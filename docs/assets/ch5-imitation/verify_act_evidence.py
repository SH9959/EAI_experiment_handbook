"""Read-only checks of the recorded 50-rollout ACT baseline, not a policy run.

Default: standard-library summary consistency checks. --evidence-dir additionally
checks rollout0.npz..rollout49.npz and video0.mp4..video49.mp4 against the summary,
then recomputes reward statistics with NumPy (allow_pickle=False). Videos are
hashed, not decoded. No model, training data, simulator or network is loaded.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zipfile import BadZipFile


SOURCE_COMMIT = "742c753c0d4a5d87076c8f69e5628c79a8cc5488"
DEFAULT_SUMMARY = Path(__file__).with_name("act-evaluation-20261002.json")
COUNTS = ("reward4_steps", "longest_reward4_run_steps", "trailing_reward4_steps")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregates(rows):
    successes = sum(row["max_reward"] == 4 for row in rows)
    final = sum(row["final_reward"] == 4 for row in rows)
    return {
        "rollouts": len(rows), "success_count": successes,
        "success_rate": successes / len(rows),
        "average_return": sum(row["episode_return"] for row in rows) / len(rows),
        "final_reward4_count": final,
        "ever_reward4_but_final_not4_count": successes - final,
    }


def validate_summary(data):
    """Return every row's first error, plus structural/aggregate errors."""
    errors = []
    try:
        require(data["state"] == "complete", "summary is not marked complete")
        require(data["source_commit"] == SOURCE_COMMIT, "unexpected ACT source commit")
        train, evaluation = data["training"], data["evaluation"]
        require(train["demonstrations"] == 50 and train["epochs"] == 2000,
                "expected 50 demonstrations and 2000 training epochs")
        require(type(train["best_epoch"]) is int and 0 <= train["best_epoch"] < 2000,
                "invalid best_epoch")
        require(evaluation["rollouts"] == 50 and evaluation["steps_per_rollout"] == 400,
                "expected 50 rollouts of 400 steps")
        require(evaluation["query_timesteps"] == [0, 100, 200, 300], "unexpected query steps")
        require(evaluation["success_definition"] == "Maximum recorded reward equals 4",
                "original max-reward criterion changed")
        require(evaluation["original_cuda_cli_verified"] is False,
                "recorded adapted run does not verify the original CUDA CLI")
        require(data["source_integrity"]["source_commit"] == SOURCE_COMMIT,
                "source integrity commit differs")
        hashes = [train["checkpoint_sha256"], data["source_integrity"]["manifest_sha256"],
                  data["cpu_gpu_comparison"]["reference_sha256"],
                  data["evidence_sha256"]["worker_result"],
                  data["evidence_sha256"]["supplemental_audit"]]
        require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                    for value in hashes), "invalid metadata SHA-256 value")
        rows = data["rollouts"]
        require(isinstance(rows, list) and len(rows) == 50, "need all 50 rollout rows")
        indices = [row["index_zero_based"] for row in rows]
        require(all(type(index) is int for index in indices)
                and sorted(indices) == list(range(50)), "indices must be unique 0..49")
    except (KeyError, TypeError, ValueError) as exc:
        return [{"item": "summary", "error": str(exc)}]
    for row in rows:
        try:
            maximum, final, total = row["max_reward"], row["final_reward"], row["episode_return"]
            require(finite(maximum) and maximum in range(5), "invalid max_reward")
            require(finite(final) and final in range(5) and final <= maximum, "invalid final_reward")
            require(finite(total) and maximum <= total <= 400 * maximum, "invalid episode_return")
            require(type(row["original_task_success"]) is bool
                    and row["original_task_success"] == (maximum == 4), "success differs from max reward")
            count, longest, trailing = [row[key] for key in COUNTS]
            require(all(type(value) is int for value in (count, longest, trailing))
                    and 0 <= trailing <= longest <= count <= 400, "invalid reward-4 step counts")
            require((count > 0) == (maximum == 4) and (longest > 0) == (count > 0)
                    and (trailing > 0) == (final == 4), "reward-4 counts contradict rewards")
            require(4 * count <= total <= 4 * count + min(maximum, 3) * (400 - count),
                    "reward-4 counts contradict episode_return")
            require(count < 400 or longest == trailing == 400,
                    "400 reward-4 steps must form one full trailing run")
            require(count <= longest * (401 - count),
                    "longest run cannot contain the stated reward-4 step count")
            pose = row["initial_box_pose"]
            require(isinstance(pose, list) and len(pose) == 7 and all(map(finite, pose)),
                    "invalid initial_box_pose")
            for key in ("trace_sha256", "video_sha256"):
                require(isinstance(row[key], str) and re.fullmatch(r"[0-9a-f]{64}", row[key]),
                        "invalid " + key)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"item": "rollout" + str(row["index_zero_based"]), "error": str(exc)})
    if not errors:
        for key, expected in aggregates(rows).items():
            actual = evaluation.get(key)
            if not finite(actual) or not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9):
                errors.append({"item": "evaluation." + key, "error": f"expected {expected}, got {actual}"})
    return errors


def inspect_trace(path, row, np):
    """Check numeric arrays; reject pickled/object arrays without deserializing them."""
    require(sha256(path) == row["trace_sha256"], "trace SHA-256 mismatch")
    with np.load(path, allow_pickle=False) as data:
        for key, shape in (("qpos", (400, 14)), ("actions", (400, 14)),
                           ("final_qpos", (14,)), ("initial_box_pose", (7,))):
            array = data[key]
            require(array.shape == shape and np.isfinite(array).all(), "invalid " + key)
        require(np.array_equal(data["initial_box_pose"], row["initial_box_pose"]), "initial pose differs")
        require(data["query_timesteps"].tolist() == [0, 100, 200, 300], "query steps differ")
        rewards = data["rewards"]
        require(rewards.shape == (400,) and np.isfinite(rewards).all()
                and np.isin(rewards, [0, 1, 2, 3, 4]).all(), "invalid rewards")
        require(data["task_max_reward"].shape == () and float(data["task_max_reward"]) == 4,
                "task_max_reward differs")
        longest = run = 0
        for reward in rewards:
            run = run + 1 if reward == 4 else 0
            longest = max(longest, run)
        actual = {
            "episode_return": float(rewards.sum()), "max_reward": float(rewards.max()),
            "original_task_success": bool(rewards.max() == 4), "final_reward": int(rewards[-1]),
            "reward4_steps": int((rewards == 4).sum()),
            "longest_reward4_run_steps": longest, "trailing_reward4_steps": run,
        }
        for key, value in actual.items():
            require(row[key] == value, "summary differs from trace: " + key)
        for key in ("episode_return", "max_reward"):
            require(data[key].shape == () and float(data[key]) == actual[key],
                    "trace scalar differs from rewards: " + key)
    return actual


def verify(summary, evidence_dir=None):
    report = {
        "status": "FAILED", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "stored evidence only; no training or policy execution",
        "summary_hash": None, "errors": [], "items": [],
        "limits": ["Summary mode checks metadata format and arithmetic, not source/model provenance.",
                   "Video checks compare bytes by SHA-256; frames are not decoded.",
                   "Final reward 4 alone does not establish stable holding."],
    }
    try:
        data = json.loads(summary.read_text(encoding="utf-8-sig"))
        report["summary_hash"] = sha256(summary)
        report["errors"] = validate_summary(data)
        if report["errors"]:
            return report
        report["aggregates"] = aggregates(data["rollouts"])
        if evidence_dir is None:
            report["status"] = "VERIFIED_SUMMARY"
            return report
        import numpy as np
        report["numpy_version"] = np.__version__
        require(evidence_dir.is_dir(), "evidence directory does not exist")
        for row in sorted(data["rollouts"], key=lambda value: value["index_zero_based"]):
            index = row["index_zero_based"]
            item = {"index_zero_based": index, "trace": "FAILED", "video_hash": "FAILED", "errors": []}
            try:
                item["recomputed"] = inspect_trace(evidence_dir / f"rollout{index}.npz", row, np)
                item["trace"] = "VERIFIED"
            except (OSError, KeyError, TypeError, ValueError, EOFError, BadZipFile) as exc:
                item["errors"].append({"file": f"rollout{index}.npz", "error": str(exc)})
            try:
                require(sha256(evidence_dir / f"video{index}.mp4") == row["video_sha256"],
                        "video SHA-256 mismatch")
                item["video_hash"] = "VERIFIED"
            except (OSError, ValueError) as exc:
                item["errors"].append({"file": f"video{index}.mp4", "error": str(exc)})
            report["items"].append(item)
            report["errors"].extend(item["errors"])
        report["verified_traces"] = sum(item["trace"] == "VERIFIED" for item in report["items"])
        report["verified_video_hashes"] = sum(item["video_hash"] == "VERIFIED" for item in report["items"])
        if not report["errors"]:
            report["status"] = "VERIFIED_TRACES"
    except (OSError, ImportError, KeyError, TypeError, ValueError) as exc:
        report["errors"].append({"item": "input", "error": str(exc)})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--evidence-dir", type=Path, help="directory with all 50 NPZs and videos; needs NumPy")
    parser.add_argument("--output", type=Path, help="optional NEW JSON report; existing files are never replaced")
    args = parser.parse_args(argv)
    if args.output:
        if args.output.exists():
            parser.error("output already exists; choose a new file")
        if args.evidence_dir and args.output.resolve().is_relative_to(args.evidence_dir.resolve()):
            parser.error("save reports outside the original evidence directory")
    report = verify(args.summary, args.evidence_dir)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
        except OSError as exc:
            print("Report write failed: " + str(exc), file=sys.stderr)
            return 2
    print(json.dumps({key: value for key, value in report.items() if key != "items"},
                     ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["status"].startswith("VERIFIED_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
