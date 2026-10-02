"""Offline boundary checks; no checkpoint, network, training or rollouts needed.

Run: python -m unittest discover -s docs/assets/ch5-imitation -p test_run_act_cpu_reference.py
Numerical cases need NumPy; they are explicitly skipped if it is unavailable.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("act_cpu_reference", Path(__file__).with_name("run_act_cpu_reference.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
try:
    import numpy as np
except ImportError:
    np = None


class FileBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def make_file(self, name, content=b"known"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_wrong_resource_hash_is_rejected_even_with_same_size(self):
        path = self.make_file("checkpoint", b"wrong")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            runner.checked_file(path, {"bytes": 5, "sha256": hashlib.sha256(b"known").hexdigest()}, "checkpoint")

    def test_missing_resource_names_obstacle(self):
        with self.assertRaisesRegex(ValueError, "Missing reference"):
            runner.checked_file(self.root / "missing", {}, "reference")

    def test_unsafe_archive_names_rejected(self):
        for name in ("../escape", "/root", "folder/../../escape", "C:/drive", "folder\\escape", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.safe_relative(name)

    def test_cpu_transformation_only_changes_act_factory(self):
        original = (b"def build_ACT_model_and_optimizer(args):\n    model.cuda()\n    return model\n\n"
                    b"def other():\n    model.cuda()\n")
        actual = runner.cpu_factory(original)
        self.assertIn(b"def other():\n    model.cuda()", actual)
        self.assertEqual(actual.count(b"model.cpu()"), 1)

    def test_already_patched_or_ambiguous_factory_rejected(self):
        for content in (b"def build_ACT_model_and_optimizer(args):\n    model.cpu()\n",
                        b"def build_ACT_model_and_optimizer(args):\n    model.cuda()\n    model.cuda()\n"):
            with self.assertRaises(ValueError):
                runner.cpu_factory(content)

    def source_fixture(self):
        source = self.root / "source"
        rows = []
        for i in range(48):
            path = self.make_file(f"source/file{i}.py", str(i).encode())
            digest = runner.sha256(path)
            rows.append({"path": path.name, "original_sha256": digest,
                         "minimal_cpu_sha256": digest, "cpu50_sha256": digest})
        return source, {"source_files": rows}

    def test_pinned_source_checks_full_file_set(self):
        source, manifest = self.source_fixture()
        self.assertEqual(runner.source_hashes(source, manifest)["checked_files"], 48)
        (source / "unexpected.py").write_text("pass")
        with self.assertRaisesRegex(ValueError, "file set differs"):
            runner.source_hashes(source, manifest)

    def test_source_mutation_rejected(self):
        source, manifest = self.source_fixture()
        (source / "file2.py").write_text("modified")
        with self.assertRaisesRegex(ValueError, "Source hashes"):
            runner.source_hashes(source, manifest)

    def test_source_missing_file_rejected(self):
        source, manifest = self.source_fixture()
        (source / "file2.py").unlink()
        with self.assertRaisesRegex(ValueError, "file set differs"):
            runner.source_hashes(source, manifest)

    def test_prepared_copy_excludes_old_bytecode(self):
        source, manifest = self.source_fixture()
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "file2.cpython-310.pyc").write_bytes(b"untrusted cache")
        destination = self.root / "fresh-source"
        runner.copy_prepared_source(source, destination, manifest)
        self.assertFalse((destination / "__pycache__").exists())
        self.assertEqual(runner.source_hashes(destination, manifest)["checked_files"], 48)

    def output_args(self):
        return argparse.Namespace(output=self.root / "new", source=None,
            torch_home=self.root / "cache", checkpoint=self.root / "evidence/model",
            stats=self.root / "evidence/stats", reference=self.root / "reference/input",
            reference_report=self.root / "reference/report", training_report=self.root / "training/report")

    def test_existing_output_is_preserved(self):
        args = self.output_args()
        args.output.mkdir()
        marker = args.output / "result.json"
        marker.write_text("old failure")
        with self.assertRaisesRegex(ValueError, "NEW output"):
            runner.validate_output(args)
        self.assertEqual(marker.read_text(), "old failure")

    def test_output_cannot_be_under_original_evidence_or_cache(self):
        args = self.output_args()
        for protected in (args.checkpoint.parent, args.torch_home, args.reference.parent):
            args.output = protected / "new"
            with self.subTest(path=args.output), self.assertRaisesRegex(ValueError, "outside"):
                runner.validate_output(args)

    def test_timeout_terminates_owned_process_and_records_failure(self):
        args = self.output_args()
        args.threads, args.timeout_seconds = 1, 1
        process = mock.Mock(pid=123)
        process.wait.side_effect = [subprocess.TimeoutExpired("test", 1), -9]
        process.poll.return_value = -9
        with mock.patch.object(runner.subprocess, "Popen", return_value=process), contextlib.redirect_stdout(io.StringIO()):
            code = runner.supervised(args, [])
        self.assertEqual(code, 124)
        process.kill.assert_called_once()
        self.assertEqual(runner.read_json(args.output / "result.json")["state"], "TIMEOUT")
        self.assertTrue(runner.read_json(args.output / "supervisor.json")["worker_exited"])

    def test_worker_crash_does_not_pass(self):
        args = self.output_args()
        args.threads, args.timeout_seconds = 1, 1
        process = mock.Mock(pid=123)
        process.wait.return_value, process.poll.return_value = 1, 1
        with mock.patch.object(runner.subprocess, "Popen", return_value=process), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.supervised(args, []), 1)
        self.assertEqual(runner.read_json(args.output / "result.json")["state"], "FAILED")

    def test_shared_environment_is_not_claimed_independent(self):
        prefix = self.root / "venv"
        prefix.mkdir()
        (prefix / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
        with mock.patch.object(sys, "prefix", str(prefix)), mock.patch.object(sys, "base_prefix", str(self.root / "base")):
            report = runner.environment_report()
        self.assertTrue(report["include_system_site_packages"])
        self.assertFalse(report["independent_environment"])


class ContractChecks(unittest.TestCase):
    def test_platform_gl_configuration(self):
        windows = runner.platform_environment("win32", Path("out"), Path("cache"), 2)
        linux = runner.platform_environment("linux", Path("out"), Path("cache"), 2)
        self.assertEqual(windows["MUJOCO_GL"], "glfw")
        self.assertNotIn("PYOPENGL_PLATFORM", windows)
        self.assertEqual(linux["PYOPENGL_PLATFORM"], "osmesa")
        self.assertEqual(linux["CUDA_VISIBLE_DEVICES"], "")

    def test_bundled_manifest_identifies_full_baseline(self):
        manifest = runner.read_json(runner.MANIFEST)
        self.assertEqual(manifest["source_commit"], runner.COMMIT)
        self.assertEqual(len({row["path"] for row in manifest["source_files"]}), 48)
        self.assertEqual(manifest["training_parameters"]["num_epochs"], 2000)
        self.assertEqual(manifest["training_parameters"]["num_episodes"], 50)
        self.assertEqual(manifest["resources"]["checkpoint"]["sha256"],
                         "620d3909885eae69c238c990eb4e89ba51ee81dfd7fcb50712ba6cef4191ac7e")

    def test_cli_exposes_no_training_or_rollout_option(self):
        options = runner.argument_parser()._option_string_actions
        for forbidden in ("--train", "--evaluate", "--stage", "--num-epochs", "--num-rollouts", "--worker"):
            self.assertNotIn(forbidden, options)
        self.assertIn("--preflight-only", options)

    def test_network_connect_is_blocked(self):
        with mock.patch.object(runner.socket, "create_connection"), mock.patch.object(runner.socket.socket, "connect"), \
             mock.patch.object(runner.socket.socket, "connect_ex"), mock.patch.object(runner.socket.socket, "sendto"):
            runner.disable_network()
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                runner.socket.create_connection(("example.invalid", 443))


@unittest.skipIf(np is None, "NumPy unavailable: numerical boundary cases not executed")
class NumericalChecks(unittest.TestCase):
    def setUp(self):
        self.expected = np.zeros((1, 100, 14), dtype=np.float32)

    def test_small_cpu_difference_passes_both_spaces(self):
        actual = self.expected + 1e-5
        self.assertEqual(runner.compare_arrays(np, actual, self.expected, actual, self.expected)["state"], "PASSED")

    def test_normalized_mismatch_fails(self):
        actual = self.expected.copy()
        actual[0, 20, 4] = 0.001
        self.assertEqual(runner.compare_arrays(np, actual, self.expected, self.expected, self.expected)["state"], "FAILED")

    def test_physical_mismatch_fails(self):
        self.assertEqual(runner.compare_arrays(np, self.expected, self.expected,
                                               self.expected + 0.001, self.expected)["state"], "FAILED")

    def test_nonfinite_and_wrong_shape_predictions_rejected(self):
        for actual in (np.zeros((100, 14)), np.full((1, 100, 14), np.nan), np.full((1, 100, 14), np.inf)):
            with self.subTest(shape=actual.shape), self.assertRaises(ValueError):
                runner.compare_arrays(np, actual, self.expected, self.expected, self.expected)

    def test_nonpositive_stats_rejected_before_inference(self):
        stats = {name: np.ones(14) for name in ("qpos_mean", "qpos_std", "action_mean", "action_std")}
        stats["qpos_std"][0] = 0
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "Nonpositive"):
            runner.check_arrays(np, stats, image, np.zeros(14), self.expected, self.expected)


if __name__ == "__main__":
    unittest.main()
