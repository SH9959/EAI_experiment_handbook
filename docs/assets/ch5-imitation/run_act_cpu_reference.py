"""Compare ONE ACT CPU prediction with the accepted GPU reference, offline.

No training, data collection, simulator rendering or rollout entry point exists.
Use Python 3.10+; --preflight-only needs only the standard library. Every run
requires a new output directory and preserves stdout/stderr, including failures.
"""
import argparse
import ast
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import pickle
import site
import socket
import subprocess
import sys
import time
import traceback
import zipfile

COMMIT = "742c753c0d4a5d87076c8f69e5628c79a8cc5488"
TASK = "sim_transfer_cube_scripted"
POLICY = {"lr": 1e-5, "num_queries": 100, "kl_weight": 10, "hidden_dim": 512,
          "dim_feedforward": 3200, "lr_backbone": 1e-5, "backbone": "resnet18",
          "enc_layers": 4, "dec_layers": 7, "nheads": 8, "camera_names": ["top"]}
MANIFEST = Path(__file__).with_name("cpu-reference-resources.json")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def checked_file(path, expected, label):
    require(path.is_file(), f"Missing {label}: {path}")
    require(path.stat().st_size == expected["bytes"], f"Wrong size for {label}: {path}")
    actual = sha256(path)
    require(actual == expected["sha256"], f"SHA256 mismatch for {label}: {path}")
    return {"bytes": expected["bytes"], "sha256": actual}


def safe_relative(name):
    relative = PurePosixPath(name)
    require(name and "\\" not in name and not relative.is_absolute()
            and ".." not in relative.parts and ":" not in name,
            "Unsafe source path: " + name)
    return relative


def cpu_factory(content):
    """Change precisely the ACT factory device; leave CNNMLP/training untouched."""
    text = content.decode("utf-8")
    nodes = [node for node in ast.parse(text).body
             if isinstance(node, ast.FunctionDef)
             and node.name == "build_ACT_model_and_optimizer"]
    require(len(nodes) == 1, "Expected one ACT factory")
    node = nodes[0]
    lines = text.splitlines(keepends=True)
    fragment = "".join(lines[node.lineno - 1:node.end_lineno])
    require(fragment.count("model.cuda()") == 1, "ACT factory CUDA fragment differs")
    return ("".join(lines[:node.lineno - 1])
            + fragment.replace("model.cuda()", "model.cpu()")
            + "".join(lines[node.end_lineno:])).encode("utf-8")


def source_hashes(source, manifest):
    """Reject modified, missing and added files; never trust a supplied manifest."""
    source = source.resolve()
    expected = {row["path"]: row for row in manifest["source_files"]}
    actual = {}
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        require(not path.is_symlink(), "Symlinks are not accepted in source: " + str(relative))
        if path.is_file():
            require(path.resolve().is_relative_to(source), "Source escapes its directory")
            actual[relative.as_posix()] = sha256(path)
    require(set(actual) == set(expected), "Source file set differs (expected exactly 48 files)")
    for profile in ("minimal_cpu", "historical_cpu50"):
        key = "minimal_cpu_sha256" if profile == "minimal_cpu" else "cpu50_sha256"
        if all(actual[name] == expected[name][key] for name in expected):
            return {"profile": profile, "checked_files": 48,
                    "source_commit": COMMIT, "files": actual}
    raise ValueError("Source hashes match neither pinned minimal CPU nor historical CPU50 copy")


def prepare_source(archive_path, destination, manifest):
    checked_file(archive_path, manifest["resources"]["source_archive"], "source archive")
    require(not destination.exists(), "Prepared source directory already exists")
    expected = {row["path"]: row for row in manifest["source_files"]}
    originals = {}
    prefix = "act-" + COMMIT + "/"
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            require(entry.filename.startswith(prefix), "Unexpected source archive prefix")
            name = entry.filename[len(prefix):]
            safe_relative(name)
            require(name in expected and name not in originals, "Unexpected/duplicate source entry")
            require((entry.external_attr >> 16) & 0o170000 != 0o120000,
                    "Archive symlinks are not accepted")
            content = archive.read(entry)
            require(hashlib.sha256(content).hexdigest() == expected[name]["original_sha256"],
                    "Original source differs: " + name)
            originals[name] = content
    require(set(originals) == set(expected), "Incomplete source archive")
    originals["detr/main.py"] = cpu_factory(originals["detr/main.py"])
    for name, content in originals.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return source_hashes(destination, manifest)


def copy_prepared_source(original, destination, manifest):
    identity = source_hashes(original, manifest)
    require(not destination.exists(), "Prepared source directory already exists")
    # Import a fresh verified copy: -B alone does not disable reading old .pyc files.
    for row in manifest["source_files"]:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((original / row["path"]).read_bytes())
    require(source_hashes(destination, manifest) == identity, "Source changed while copying")
    return identity


def accept_resources(args, manifest):
    resources = manifest["resources"]
    paths = {"checkpoint": args.checkpoint, "stats": args.stats,
             "training_report": args.training_report, "reference": args.reference,
             "reference_report": args.reference_report,
             "backbone": args.torch_home / "hub/checkpoints/resnet18-f37072fd.pth"}
    identities = {key: checked_file(path, resources[key], key) for key, path in paths.items()}
    training = read_json(args.training_report)
    accepted = training.get("training_acceptance", {})
    require(training.get("state") == "complete" and training.get("source_commit") == COMMIT,
            "Full training report is not accepted")
    require(training.get("parameters") == manifest["training_parameters"], "Training parameters differ")
    require(all(training.get(key) is True for key in (
        "original_48_unchanged", "training_source_unchanged_during_run", "data_unchanged")),
        "Training integrity checks were not accepted")
    require(accepted.get("state") == "passed" and accepted.get("epochs_completed") == 2000
            and accepted.get("best_epoch") == 1955
            and accepted.get("best_is_pre_update_initial_model") is False
            and accepted.get("best_matches_saved_best_epoch") is True,
            "Trained best checkpoint was not accepted")
    best = [row for row in accepted.get("checkpoints", []) if row.get("file") == "policy_best.ckpt"]
    require(len(best) == 1 and best[0]["sha256"] == identities["checkpoint"]["sha256"]
            and best[0]["bytes"] == identities["checkpoint"]["bytes"], "Best checkpoint identity differs")
    require(accepted.get("stats_sha256") == identities["stats"]["sha256"], "Training stats identity differs")
    reference = read_json(args.reference_report)
    require(reference.get("state") == "passed" and reference.get("source_commit") == COMMIT
            and reference.get("source_original_files") == 48, "GPU reference source was not accepted")
    for key, resource in (("checkpoint_sha256", "checkpoint"), ("stats_sha256", "stats"),
                          ("training_result_sha256", "training_report"), ("weights_sha256", "backbone"),
                          ("reference_sha256", "reference")):
        require(reference.get(key) == identities[resource]["sha256"], "GPU reference identity differs: " + key)
    require(training.get("weights_sha256") == identities["backbone"]["sha256"], "Training backbone differs")
    require(reference.get("policy_config") == POLICY, "GPU reference policy differs")
    require(reference.get("precision") == {"cuda_matmul_allow_tf32": False, "cudnn_allow_tf32": False},
            "GPU reference must disable TF32")
    return identities


def environment_report():
    prefix = Path(sys.prefix).resolve()
    config = prefix / "pyvenv.cfg"
    text = config.read_text(encoding="utf-8") if config.is_file() else ""
    inherited = any(line.strip().lower().replace(" ", "") == "include-system-site-packages=true"
                    for line in text.splitlines())
    package_paths = [Path(path).resolve() for path in sys.path if path
                     and ("site-packages" in Path(path).parts or "dist-packages" in Path(path).parts)]
    external = [str(path) for path in package_paths if not path.is_relative_to(prefix)]
    pth_files = []
    for directory in sorted(set(package_paths)):
        for path in sorted(directory.glob("*.pth")):
            # Do not reproduce executable lines or private absolute path contents in reports.
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            pth_files.append({"path": str(path), "sha256": sha256(path),
                              "executable_lines": sum(line.startswith(("import ", "import\t")) for line in lines)})
    is_venv = sys.prefix != sys.base_prefix
    return {"python": sys.version, "executable": sys.executable, "prefix": sys.prefix,
            "base_prefix": sys.base_prefix, "is_virtualenv": is_venv,
            "include_system_site_packages": inherited, "external_package_paths": external,
            "user_site_enabled": bool(site.ENABLE_USER_SITE), "pth_files": pth_files,
            "independent_environment": bool(is_venv and not inherited and not external
                                            and not site.ENABLE_USER_SITE),
            "independence_scope": "Observed interpreter/package paths; not a clean-install or dependency-lock validation"}


def disable_network():
    def blocked(*args, **kwargs):
        raise RuntimeError("Network access/downloads disabled for this single-input check")
    socket.create_connection = blocked
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.socket.sendto = blocked
    return blocked


def platform_environment(platform, output, torch_home, threads):
    require(platform in ("win32", "linux"), "Supported platforms: Windows or Linux")
    environment = {"TORCH_HOME": str(torch_home), "CUDA_VISIBLE_DEVICES": "",
                   "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(output / "mpl-cache"),
                   "OMP_NUM_THREADS": str(threads), "OPENBLAS_NUM_THREADS": "1",
                   "MKL_NUM_THREADS": str(threads), "PYTHONDONTWRITEBYTECODE": "1",
                   "MUJOCO_GL": "glfw" if platform == "win32" else "osmesa"}
    if platform == "linux":
        environment["PYOPENGL_PLATFORM"] = "osmesa"
    return environment


@contextlib.contextmanager
def factory_arguments(output):
    previous = sys.argv[:]
    sys.argv = [previous[0], "--ckpt_dir", str(output), "--policy_class", "ACT",
                "--task_name", TASK, "--seed", "0", "--num_epochs", "2000"]
    try:
        yield
    finally:
        sys.argv = previous


def check_arrays(np, stats, image, qpos, expected, physical_expected):
    for name in ("qpos_mean", "qpos_std", "action_mean", "action_std"):
        require(stats[name].shape == (14,) and np.isfinite(stats[name]).all(), "Invalid stats: " + name)
    require((stats["qpos_std"] > 0).all() and (stats["action_std"] > 0).all(), "Nonpositive normalization scale")
    require(image.shape == (480, 640, 3) and image.dtype == np.uint8 and np.ptp(image) > 0,
            "Invalid genuine reference RGB image")
    require(qpos.shape == (14,) and np.isfinite(qpos).all(), "Invalid reference qpos")
    for values in (expected, physical_expected):
        require(values.shape == (1, 100, 14) and np.isfinite(values).all(), "Invalid reference prediction")
    np.testing.assert_allclose(physical_expected, expected * stats["action_std"] + stats["action_mean"],
                               rtol=1e-6, atol=1e-6)


def compare_arrays(np, actual, expected, physical_actual, physical_expected):
    require(actual.shape == (1, 100, 14) and np.isfinite(actual).all(), "Invalid CPU action chunk")
    require(physical_actual.shape == (1, 100, 14) and np.isfinite(physical_actual).all(),
            "Invalid denormalized CPU action chunk")
    comparison = {"state": "FAILED", "shape": list(actual.shape), "all_finite": True,
                  "normalized_action_max_abs_difference": float(np.max(np.abs(actual - expected))),
                  "physical_action_max_abs_difference": float(np.max(np.abs(physical_actual - physical_expected))),
                  "rtol": 1e-4, "atol": 1e-4}
    comparison["state"] = "PASSED" if (np.allclose(actual, expected, rtol=1e-4, atol=1e-4)
        and np.allclose(physical_actual, physical_expected, rtol=1e-4, atol=1e-4)) else "FAILED"
    return comparison


def infer_once(args, source, report):
    blocked = disable_network()
    sys.path[:0] = [str(source), str(source / "detr")]
    import numpy as np
    import torch
    import torchvision
    torch.hub.download_url_to_file = blocked
    torch.hub.urlopen = blocked
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    np.random.seed(0)
    import policy as policy_module
    require(Path(policy_module.__file__).resolve() == source / "policy.py", "Wrong ACT policy import")
    report["versions"] = {name: importlib.metadata.version(name)
                          for name in ("torch", "torchvision", "numpy", "ipython")}
    report["module_paths"] = {"torch": torch.__file__, "torchvision": torchvision.__file__, "numpy": np.__file__}
    if any(not Path(path).resolve().is_relative_to(Path(sys.prefix).resolve())
           for path in report["module_paths"].values()):
        report["environment"]["independent_environment"] = False
    # Only this fixed, hash-verified course stats pickle is deserialized.
    with args.stats.open("rb") as stream:
        stats = pickle.load(stream)
    with np.load(args.reference, allow_pickle=False) as reference:
        image, qpos = reference["image"].copy(), reference["qpos"].copy()
        expected, physical_expected = reference["normalized_actions"].copy(), reference["actions"].copy()
    check_arrays(np, stats, image, qpos, expected, physical_expected)
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    require(state and all(value.device.type == "cpu" for value in state.values()), "Non-CPU checkpoint tensor")
    require(all(torch.isfinite(value).all() for value in state.values() if value.is_floating_point()),
            "Nonfinite checkpoint tensor")
    with factory_arguments(args.output):
        policy = policy_module.ACTPolicy(POLICY.copy())
    loaded = policy.load_state_dict(state, strict=True)
    require(not loaded.missing_keys and not loaded.unexpected_keys, "Checkpoint did not load strictly")
    del state
    require(all(value.device.type == "cpu" for value in list(policy.parameters()) + list(policy.buffers())),
            "Policy contains non-CPU tensors")
    policy.eval()
    # Exactly the original get_image order: CHW, stack cameras, /255, float32, batch.
    image_tensor = torch.from_numpy(np.stack([np.transpose(image, (2, 0, 1))]) / 255.0).float().unsqueeze(0)
    qpos_tensor = torch.from_numpy((qpos - stats["qpos_mean"]) / stats["qpos_std"]).float().unsqueeze(0)
    report["strict_state_dict_loaded"] = True
    report["inference_started"] = True
    save(args.output / "result.json", report)
    with torch.inference_mode():
        actual = policy(qpos_tensor, image_tensor).cpu().numpy()
    report["forward_passes"] = 1
    physical_actual = actual * stats["action_std"] + stats["action_mean"]
    comparison = compare_arrays(np, actual, expected, physical_actual, physical_expected)
    report["reference_comparison"] = comparison
    np.savez_compressed(args.output / "cpu-reference-output.npz", normalized_actions=actual, actions=physical_actual)
    save(args.output / "comparison.json", comparison)
    require(comparison["state"] == "PASSED", "CPU/GPU reference tolerance failed; see comparison.json")


def worker(args):
    started = time.monotonic()
    report = {"state": "RUNNING", "scope": "One saved input; no environment or task-success claim",
              "source_commit": COMMIT, "training_run": False, "rollouts_run": 0,
              "rendering_run": False, "forward_passes": 0, "network_downloads_allowed": False,
              "environment": environment_report(), "errors": []}
    source = None
    manifest = read_json(MANIFEST)
    try:
        require(manifest["source_commit"] == COMMIT and len(manifest["source_files"]) == 48,
                "Bundled resource manifest differs")
        report["manifest_sha256"] = sha256(MANIFEST)
        report["inputs"] = accept_resources(args, manifest)
        if args.source_archive:
            source = args.output / ("act-" + COMMIT)
            report["source_before"] = prepare_source(args.source_archive, source, manifest)
        else:
            source = args.output / ("act-" + COMMIT)
            report["source_before"] = copy_prepared_source(args.source, source, manifest)
        report["prepared_source"] = str(source)
        save(args.output / "source-identity.json", report["source_before"])
        if args.preflight_only:
            report["state"] = "PREFLIGHT_ONLY"
        else:
            infer_once(args, source, report)
            require(accept_resources(args, manifest) == report["inputs"], "Input resources changed during inference")
            report["resources_unchanged_after"] = True
            report["state"] = "SINGLE_INPUT_VERIFIED"
    except Exception as error:
        report["state"] = "FAILED"
        report["errors"].append(type(error).__name__ + ": " + str(error))
        report["traceback"] = traceback.format_exc()
    finally:
        if source is not None and source.exists():
            try:
                after = source_hashes(source, manifest)
                report["source_unchanged_after"] = after == report.get("source_before")
                require(report["source_unchanged_after"], "Source changed during check")
            except Exception as error:
                report["state"] = "FAILED"
                report["errors"].append("Final source check: " + str(error))
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save(args.output / "result.json", report)
    print(json.dumps({key: report[key] for key in ("state", "forward_passes", "rollouts_run", "errors")}), flush=True)
    return 0 if report["state"] in ("PREFLIGHT_ONLY", "SINGLE_INPUT_VERIFIED") else 1


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-archive", type=Path, help="Pinned original ACT ZIP; prepare a new CPU copy")
    group.add_argument("--source", type=Path, help="Existing pinned minimal CPU or historical CPU50 source directory")
    for name in ("checkpoint", "stats", "torch-home", "reference", "reference-report", "training-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true", help="Hashes/source only; no ML imports or prediction")
    parser.add_argument("--threads", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Worker wall time, 1–600 seconds (default: 180)")
    return parser


def validate_output(args):
    require(not args.output.exists(), "Use a NEW output directory; previous results are never overwritten")
    protected = [args.torch_home, args.checkpoint.parent, args.stats.parent,
                 args.reference.parent, args.reference_report.parent, args.training_report.parent]
    if args.source:
        protected.append(args.source)
    require(all(not args.output.is_relative_to(path) for path in protected),
            "Output must be outside the source, cache and input-evidence directories")


def supervised(args, argv):
    validate_output(args)
    require(1 <= args.timeout_seconds <= 600, "--timeout-seconds must be between 1 and 600")
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "PYOPENGL_PLATFORM"):
        environment.pop(key, None)
    environment.update(platform_environment(sys.platform, args.output, args.torch_home, args.threads))
    # Private worker nonce exists only in its environment, not as an exposed CLI overwrite mode.
    environment["ACT_REFERENCE_WORKER_OUTPUT"] = str(args.output)
    args.output.mkdir(parents=True)
    save(args.output / "result.json", {"state": "STARTING", "training_run": False,
                                      "rollouts_run": 0, "forward_passes": 0})
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), *argv]
    started = time.monotonic()
    with (args.output / "stdout.log").open("wb") as stdout, (args.output / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=environment,
                                   cwd=args.output, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        timed_out = False
        try:
            code = process.wait(timeout=args.timeout_seconds)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            process.kill()
            process.wait()
            code = 124 if timed_out else 130
            report = read_json(args.output / "result.json")
            report["state"] = "TIMEOUT" if timed_out else "INTERRUPTED"
            report.setdefault("errors", []).append("Worker killed at wall-time boundary" if timed_out else "Stopped by user")
            save(args.output / "result.json", report)
    save(args.output / "supervisor.json", {"exit_code": code, "timed_out": timed_out,
         "timeout_seconds": args.timeout_seconds, "elapsed_seconds": round(time.monotonic() - started, 3),
         "worker_pid": process.pid, "worker_exited": process.poll() is not None,
         "bound_scope": "One inference process; no subprocesses or rollout workers are launched"})
    result = read_json(args.output / "result.json")
    if result["state"] in ("STARTING", "RUNNING"):
        result["state"] = "FAILED"
        result.setdefault("errors", []).append("Worker exited without final acceptance; inspect stderr.log")
        save(args.output / "result.json", result)
    print(json.dumps({"state": result["state"], "exit_code": code, "output": str(args.output),
                      "errors": result.get("errors", [])}, ensure_ascii=False))
    return code if code else (0 if result["state"] in ("PREFLIGHT_ONLY", "SINGLE_INPUT_VERIFIED") else 1)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = argument_parser().parse_args(argv)
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    # Absolute arguments must be forwarded because the worker uses its output as cwd.
    normalized = []
    for key, value in vars(args).items():
        if value is True:
            normalized.append("--" + key.replace("_", "-"))
        elif value is not None and value is not False:
            normalized.extend(["--" + key.replace("_", "-"), str(value)])
    if os.environ.pop("ACT_REFERENCE_WORKER_OUTPUT", None) == str(args.output):
        sys.dont_write_bytecode = True
        return worker(args)
    try:
        return supervised(args, normalized)
    except (ValueError, OSError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
