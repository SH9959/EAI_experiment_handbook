"""假 Unity 的验收/失败留证测试；本文件不证明真实仿真成功。"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import virtualhome_checked_demo as demo


def graph(*, inside=False, held=False, closed=True):
    edges = []
    if inside:
        edges.append({"from_id": 7, "to_id": 25, "relation_type": "INSIDE"})
    if held:
        edges.append({"from_id": 1, "to_id": 7, "relation_type": "HOLDS_RH"})
    return {"nodes": [{"id": 1, "class_name": "character", "states": []},
                      {"id": 7, "class_name": "salmon", "states": []},
                      {"id": 25, "class_name": "fridge",
                       "states": ["CLOSED" if closed else "OPEN"]}], "edges": edges}


class FakeUnity:
    def __init__(self, *, fail_at=None, fail_value=False, goal_after=6,
                 initial=None, final=None, graph_error_at=None):
        self.actions = []
        self.graph_calls = 0
        self.fail_at = fail_at
        self.fail_value = fail_value
        self.goal_after = goal_after
        self.initial = initial or graph()
        self.final = final or graph(inside=True)
        self.graph_error_at = graph_error_at

    def reset(self, scene):
        self.scene = scene
        return True

    def add_character(self, character):
        return True

    def environment_graph(self):
        self.graph_calls += 1
        if self.graph_calls == self.graph_error_at:
            return True, {"nodes": self.initial["nodes"]}  # 缺 edges
        return True, copy.deepcopy(self.final if len(self.actions) >= self.goal_after
                                   else self.initial)

    def render_script(self, steps, **kwargs):
        self.actions.extend(steps)
        if kwargs["find_solution"] is not False or kwargs["recording"] is not True:
            raise AssertionError("必须执行原动作并录制")
        if len(self.actions) == self.fail_at:
            return self.fail_value, {"message": "object is not close"}
        return True, {"message": "Success"}


class CheckedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.api = self.root / "api"
        (self.api / "unity_simulator").mkdir(parents=True)
        (self.api / "unity_simulator" / "comm_unity.py").write_text("", encoding="utf-8")
        self.output = self.root / "run"

    def args(self, *extra):
        return demo.parser().parse_args(["--api-dir", str(self.api),
                                        "--output-dir", str(self.output), *extra])

    def run_fake(self, fake, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            code, result = demo.run_checked(self.args(*extra), lambda args: fake)
        self.assertEqual(json.loads(json.dumps(result)),
                         json.loads((self.output / "result.json").read_text("utf-8")))
        return code, result

    def test_success_requires_all_actions_and_final_graph(self):
        fake = FakeUnity()
        code, result = self.run_fake(fake)
        self.assertEqual(code, 0)
        self.assertIs(result["task_success"], True)
        self.assertTrue(result["all_steps_succeeded"])
        self.assertEqual(len(fake.actions), 6)
        self.assertFalse(result["model_called"])
        self.assertTrue((self.output / "graph_before.json").exists())
        self.assertTrue((self.output / "graph_after.json").exists())
        self.assertTrue((self.output / "step_06.json").exists())

    def test_failed_action_stops_even_if_final_goal_looks_complete(self):
        fake = FakeUnity(fail_at=2, goal_after=2)
        code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertIs(result["task_success"], False)
        self.assertEqual(len(fake.actions), 2)
        failure = json.loads((self.output / "step_02.json").read_text("utf-8"))
        self.assertEqual(failure["message"], {"message": "object is not close"})
        self.assertTrue((self.output / "graph_02.json").exists())
        self.assertFalse((self.output / "step_03.json").exists())

    def test_numeric_success_is_not_literal_true(self):
        code, result = self.run_fake(FakeUnity(fail_at=1, fail_value=1, goal_after=1))
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertEqual(len(result["actions"]), 1)

    def test_missing_graph_stops_and_preserves_invalid_payload(self):
        fake = FakeUnity(graph_error_at=2)
        code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertEqual(len(fake.actions), 1)
        self.assertNotIn("edges", json.loads((self.output / "graph_01.json").read_text("utf-8")))
        self.assertIn("edges", result["actions"][0]["graph_error"]["message"])

    def test_final_graph_missing_is_unknown_after_all_true_actions(self):
        code, result = self.run_fake(FakeUnity(graph_error_at=8))
        self.assertNotEqual(code, 0)
        self.assertTrue(result["all_steps_succeeded"])
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertEqual(result["errors"][-1]["stage"], "final_graph")

    def test_preexisting_goal_is_rejected_without_actions(self):
        fake = FakeUnity(initial=graph(inside=True))
        code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertIs(result["task_success"], False)
        self.assertEqual(fake.actions, [])
        self.assertIn("初始三文鱼", result["errors"][0]["message"])

    def test_initial_holding_rejected_without_actions(self):
        fake = FakeUnity(initial=graph(held=True))
        code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertEqual(fake.actions, [])
        self.assertIs(result["task_success"], False)

    def test_held_salmon_is_not_success_even_with_inside_relation(self):
        code, result = self.run_fake(FakeUnity(final=graph(inside=True, held=True)))
        self.assertNotEqual(code, 0)
        self.assertIs(result["task_success"], False)
        self.assertTrue(result["final_state"]["salmon_held"])

    def test_open_fridge_is_not_success(self):
        code, result = self.run_fake(FakeUnity(final=graph(inside=True, closed=False)))
        self.assertNotEqual(code, 0)
        self.assertIs(result["task_success"], False)

    def test_external_plan_is_labeled_and_raw_input_preserved(self):
        plan = self.root / "model-plan.json"
        plan.write_text('{"steps": ["<char0> [WALK] <salmon> (7)"]}', encoding="utf-8")
        code, result = self.run_fake(FakeUnity(), "--plan", str(plan), "--plan-source", "model")
        self.assertNotEqual(code, 0)
        self.assertEqual(result["plan_source"], "provided_file")
        self.assertEqual(result["plan_origin_declared"], "model")
        self.assertFalse(result["model_called"])
        self.assertFalse(result["plan_origin_verified"])
        self.assertEqual(plan.read_text("utf-8"), (self.output / "plan_input.json").read_text("utf-8"))

    def test_plan_from_different_scene_is_rejected_before_actions(self):
        plan = self.root / "other-scene.json"
        plan.write_text('{"steps": ["<char0> [WALK] <salmon> (999)"]}', encoding="utf-8")
        fake = FakeUnity()
        code, result = self.run_fake(fake, "--plan", str(plan))
        self.assertNotEqual(code, 0)
        self.assertEqual(fake.actions, [])
        self.assertIs(result["task_success"], False)
        self.assertIn("ID", result["errors"][0]["message"])
        self.assertTrue((self.output / "plan_input.json").exists())

    def test_connection_failure_during_action_preserves_exact_error_and_graph(self):
        fake = FakeUnity()
        with patch.object(fake, "render_script", side_effect=ConnectionError("lost response 123")):
            code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        row = json.loads((self.output / "step_01.json").read_text("utf-8"))
        self.assertEqual(row["error"], {"type": "ConnectionError", "message": "lost response 123"})
        self.assertTrue((self.output / "graph_01.json").exists())
        self.assertTrue((self.output / "graph_after.json").exists())
        self.assertEqual(len(result["actions"]), 1)

    def test_contradictory_fridge_state_is_unknown(self):
        final = graph(inside=True)
        final["nodes"][2]["states"] = ["CLOSED", "OPEN"]
        code, result = self.run_fake(FakeUnity(final=final))
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertIn("矛盾", result["errors"][0]["message"])

    def test_missing_character_cannot_be_interpreted_as_empty_hands(self):
        initial = graph()
        initial["nodes"] = [node for node in initial["nodes"] if node["class_name"] != "character"]
        fake = FakeUnity(initial=initial)
        code, result = self.run_fake(fake)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertEqual(fake.actions, [])
        self.assertIn("character", result["errors"][0]["message"])

    def test_changed_character_id_is_unknown(self):
        final = graph(inside=True)
        final["nodes"][0]["id"] = 99
        code, result = self.run_fake(FakeUnity(final=final))
        self.assertNotEqual(code, 0)
        self.assertEqual(result["task_success"], "UNKNOWN")
        self.assertIn("角色 ID", result["errors"][0]["message"])

    def test_zero_recording_frames_never_claims_complete_evidence(self):
        code, result = self.run_fake(FakeUnity())
        self.assertEqual(code, 0)  # 物理任务判据独立于是否录得证据。
        self.assertIs(result["task_success"], True)
        self.assertEqual(result["recording_frames"], 0)
        self.assertEqual(result["recording_state"], "MISSING_STEP_FRAMES")
        self.assertIs(result["evidence_complete"], False)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "result.json"
        sentinel.write_text("existing evidence", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            demo.run_checked(self.args(), lambda args: FakeUnity())
        self.assertEqual(sentinel.read_text("utf-8"), "existing evidence")

    def test_default_check_never_imports_or_connects_to_unity(self):
        with patch.object(demo, "connect", side_effect=AssertionError("unexpected connection")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = demo.main(["--api-dir", str(self.api), "--output-dir", str(self.output)])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["task_success"], "NOT_EVALUATED")
        self.assertFalse(result["unity_contacted"])
        self.assertFalse(self.output.exists())

    def test_prepare_saves_ids_and_graph_but_never_executes_actions(self):
        fake = FakeUnity()
        code, result = self.run_fake(fake, "--run", "--prepare")
        self.assertEqual(code, 0)
        self.assertEqual(result["execution_state"], "PREPARED")
        self.assertEqual(result["task_success"], "NOT_EVALUATED")
        self.assertEqual(fake.actions, [])
        self.assertEqual(fake.graph_calls, 1)
        self.assertTrue((self.output / "graph_before.json").exists())
        run = json.loads((self.output / "run.json").read_text("utf-8"))
        self.assertEqual((run["food_id"], run["fridge_id"]), (7, 25))
        self.assertFalse((self.output / "graph_after.json").exists())

    def test_prepare_requires_explicit_run(self):
        with patch.object(demo, "connect", side_effect=AssertionError("unexpected connection")), \
                contextlib.redirect_stderr(io.StringIO()):
            code = demo.main(["--api-dir", str(self.api), "--output-dir", str(self.output),
                              "--prepare"])
        self.assertEqual(code, 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
