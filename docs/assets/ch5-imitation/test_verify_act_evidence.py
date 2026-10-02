"""Check that evidence errors cannot become reported ACT experiment success."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import verify_act_evidence as verifier

try:
    import numpy as np
except ImportError:
    np = None


class SummaryChecks(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(verifier.DEFAULT_SUMMARY.read_text(encoding="utf-8"))

    def test_baseline_criterion_and_final_observation_are_distinct(self):
        self.assertEqual(verifier.validate_summary(self.data), [])
        result = verifier.aggregates(self.data["rollouts"])
        self.assertEqual(result["success_count"], 37)
        self.assertEqual(result["final_reward4_count"], 34)
        self.assertEqual(result["ever_reward4_but_final_not4_count"], 3)
        self.assertEqual(result["average_return"], 490.26)

    def test_duplicate_or_missing_rollout_rejected(self):
        self.data["rollouts"][-1] = deepcopy(self.data["rollouts"][0])
        self.assertIn("unique", verifier.validate_summary(self.data)[0]["error"])
        self.data["rollouts"].pop()
        self.assertTrue(verifier.validate_summary(self.data))

    def test_corrupt_metadata_and_aggregate_rejected(self):
        for field, value in (("success_count", 50), ("average_return", 0),
                             ("final_reward4_count", 37)):
            changed = deepcopy(self.data)
            changed["evaluation"][field] = value
            self.assertTrue(verifier.validate_summary(changed), field)
        self.data["training"]["checkpoint_sha256"] = "bad-hash"
        self.assertTrue(verifier.validate_summary(self.data))

    def test_multiple_row_failures_preserved(self):
        self.data["rollouts"][0]["original_task_success"] = True
        self.data["rollouts"][1]["episode_return"] = float("nan")
        errors = verifier.validate_summary(self.data)
        self.assertEqual([row["item"] for row in errors], ["rollout0", "rollout1"])

    def test_reward_counts_cannot_contradict_return(self):
        row = self.data["rollouts"][1]
        row["reward4_steps"] = row["longest_reward4_run_steps"] = 399
        errors = verifier.validate_summary(self.data)
        self.assertEqual(errors[0]["item"], "rollout1")
        self.assertIn("episode_return", errors[0]["error"])

    def test_summary_runs_without_site_packages_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            command = [sys.executable, "-S", str(Path(verifier.__file__)), "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            self.assertEqual(json.loads(saved)["status"], "VERIFIED_SUMMARY")
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), saved)

    @unittest.skipIf(np is None, "NumPy needed for optional raw trace checks")
    def test_missing_evidence_reports_every_file(self):
        with tempfile.TemporaryDirectory() as directory:
            report = verifier.verify(verifier.DEFAULT_SUMMARY, Path(directory))
            self.assertEqual(report["status"], "FAILED")
            self.assertEqual(len(report["items"]), 50)
            self.assertEqual(len(report["errors"]), 100)
            self.assertEqual(report["verified_traces"], 0)


@unittest.skipIf(np is None, "NumPy needed for optional raw trace checks")
class TraceChecks(unittest.TestCase):
    def test_drop_after_success_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout0.npz"
            arrays = dict(qpos=np.zeros((400, 14)), actions=np.zeros((400, 14)),
                          final_qpos=np.zeros(14), initial_box_pose=np.zeros(7),
                          query_timesteps=np.array([0, 100, 200, 300]),
                          rewards=np.array([0] * 200 + [4] * 100 + [0] * 100),
                          task_max_reward=np.array(4), episode_return=np.array(400), max_reward=np.array(4))
            row = dict(initial_box_pose=[0] * 7, episode_return=400, max_reward=4,
                       original_task_success=True, final_reward=0, reward4_steps=100,
                       longest_reward4_run_steps=100, trailing_reward4_steps=0)
            np.savez_compressed(path, **arrays)
            row["trace_sha256"] = verifier.sha256(path)
            result = verifier.inspect_trace(path, row, np)
            self.assertTrue(result["original_task_success"])
            self.assertEqual(result["final_reward"], 0)
            with path.open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verifier.inspect_trace(path, row, np)
            arrays["episode_return"] = np.array(0)
            np.savez_compressed(path, **arrays)
            row["trace_sha256"] = verifier.sha256(path)
            with self.assertRaisesRegex(ValueError, "trace scalar differs"):
                verifier.inspect_trace(path, row, np)
            arrays["rewards"] = arrays["rewards"].astype(object)
            np.savez_compressed(path, **arrays)
            row["trace_sha256"] = verifier.sha256(path)
            with self.assertRaisesRegex(ValueError, "allow_pickle=False"):
                verifier.inspect_trace(path, row, np)


if __name__ == "__main__":
    unittest.main(verbosity=2)
