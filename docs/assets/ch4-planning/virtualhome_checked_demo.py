"""VirtualHome 三文鱼任务：默认只检查文件；--run 连接已启动的本机 Unity。"""
from __future__ import annotations

import argparse
import collections.abc  # 兼容仍引用 collections.abc 的旧版 VirtualHome API。
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from planning_checks import check_virtualhome_response, named_node, virtualhome_plan


class UnknownObservation(ValueError):
    """环境状态缺失或无效，无法完成验收。"""


def save(directory: Path, name: str, value) -> None:
    (directory / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def task_state(graph: dict, food_id: int, fridge_id: int) -> dict:
    """要求完整、无矛盾的场景反馈；不能把缺失数据当作“不在手里”。"""
    try:
        named_node(graph, "salmon", food_id)
        fridge = named_node(graph, "fridge", fridge_id)
        character = named_node(graph, "character")
        ids = {node["id"] for node in graph["nodes"]}
        edges = graph.get("edges")
        if not isinstance(edges, list):
            raise ValueError("场景图缺少 edges 列表")
        for edge in edges:
            if (not isinstance(edge, dict) or
                    type(edge.get("from_id")) is not int or
                    type(edge.get("to_id")) is not int or
                    edge["from_id"] not in ids or edge["to_id"] not in ids or
                    not isinstance(edge.get("relation_type"), str) or
                    not edge["relation_type"]):
                raise ValueError("场景图包含无效关系或不存在的节点 ID")
        states = fridge.get("states")
        if (not isinstance(states, list) or
                any(not isinstance(state, str) for state in states) or
                sum(state in states for state in ("OPEN", "CLOSED")) != 1):
            raise ValueError("冰箱开闭状态缺失或互相矛盾")
        inside = any(edge["from_id"] == food_id and edge["to_id"] == fridge_id and
                     edge["relation_type"] == "INSIDE" for edge in edges)
        held = any(edge["to_id"] == food_id and edge["relation_type"].startswith("HOLDS")
                   for edge in edges)
        return {"character_id": character["id"],
                "salmon_inside_fridge": inside, "fridge_states": states,
                "fridge_closed": "CLOSED" in states and "OPEN" not in states,
                "salmon_held": held}
    except (ValueError, TypeError, KeyError) as exc:
        raise UnknownObservation(str(exc)) from exc


def read_graph(comm, directory: Path, name: str, report: dict,
               food_id: int | None = None, fridge_id: int | None = None):
    try:
        response = comm.environment_graph()
    except Exception as exc:
        raise UnknownObservation(str(exc)) from exc
    save(directory, name + "_response.json", response)
    if not isinstance(response, (tuple, list)) or len(response) != 2:
        raise UnknownObservation("environment_graph 返回值不是 (success, graph)")
    ok, graph = response
    if ok is not True:
        raise UnknownObservation(f"environment_graph 未返回字面值 True：{response!r}")
    save(directory, name + ".json", graph)
    try:
        food_id = named_node(graph, "salmon", food_id)["id"]
        fridge_id = named_node(graph, "fridge", fridge_id)["id"]
    except (ValueError, TypeError, KeyError) as exc:
        raise UnknownObservation(str(exc)) from exc
    state = task_state(graph, food_id, fridge_id)
    if "character_id" in report and report["character_id"] != state["character_id"]:
        raise UnknownObservation("本次角色 ID 与初始场景不同，无法核对同一角色的持物状态")
    report["character_id"] = state["character_id"]
    report["food_id"], report["fridge_id"] = food_id, fridge_id
    return graph, state


def connect(args):
    # 仅连接回环地址；不启动/停止 Unity，也不走代理。
    no_proxy = os.environ.get("NO_PROXY", "")
    os.environ["NO_PROXY"] = ",".join(filter(None, (no_proxy, "127.0.0.1", "localhost")))
    sys.path.insert(0, str(args.api_dir.resolve()))
    from unity_simulator import comm_unity
    return comm_unity.UnityCommunication(url="127.0.0.1", port=str(args.port),
                                        timeout_wait=60)


def run_checked(args, factory=None) -> tuple[int, dict]:
    """执行并保留失败证据。factory 仅供假控制器测试，不替代 Unity 实测。"""
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "mode": "UNITY_EXECUTION", "endpoint": f"http://127.0.0.1:{args.port}",
              "execution_state": "STARTED",
              "scene": args.scene, "model_called": False, "task_success": "UNKNOWN",
              "plan_source": "provided_file" if args.plan else "handbook_rules",
              "plan_origin_declared": args.plan_source if args.plan else "handbook_rules",
              "plan_origin_verified": False, "actions": [], "errors": [],
              "planned_steps": None, "all_steps_succeeded": False}
    comm = None
    scene_ready = False
    uncertain = False
    final_state = None

    def error(exc, stage):
        report["errors"].append({"stage": stage, "type": type(exc).__name__,
                                 "message": str(exc)})

    try:
        save(directory, "result.json", report)
        api_file = args.api_dir / "unity_simulator" / "comm_unity.py"
        if api_file.is_file():
            report["api_sha256"] = hashlib.sha256(api_file.read_bytes()).hexdigest()
        comm = (factory or connect)(args)
        reset_response = comm.reset(args.scene)
        report["reset_response"] = reset_response
        if reset_response is not True:
            raise RuntimeError(f"reset 未返回字面值 True：{reset_response!r}")
        character_response = comm.add_character("Chars/Female2")
        report["add_character_response"] = character_response
        if character_response is not True:
            raise RuntimeError(f"add_character 未返回字面值 True：{character_response!r}")
        scene_ready = True
        graph, initial = read_graph(comm, directory, "graph_before", report,
                                    args.food_id, args.fridge_id)
        report["initial_state"] = initial
        if initial["salmon_inside_fridge"]:
            raise ValueError("初始三文鱼已经在选定冰箱内，不能作为本次放入任务的成功记录")
        if any(edge["relation_type"].startswith("HOLDS") for edge in graph["edges"]):
            raise ValueError("初始角色手中已有物品；本任务要求初始双手为空")
        if args.prepare:
            report["execution_state"] = "PREPARED"
            report["task_success"] = "NOT_EVALUATED"
            return 0, report
        if args.plan:
            raw = args.plan.read_text(encoding="utf-8-sig")
            (directory / "plan_input.json").write_text(raw, encoding="utf-8")
            response = json.loads(raw)
            steps = check_virtualhome_response(graph, response, report["food_id"],
                                               report["fridge_id"])
            report["plan_file_sha256"] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
        else:
            steps = virtualhome_plan(graph, report["food_id"], report["fridge_id"])
        save(directory, "plan.json", {"steps": steps, "source": report["plan_source"],
                                      "origin_declared": report["plan_origin_declared"]})
        report["planned_steps"] = len(steps)
        for index, step in enumerate(steps, 1):
            row = {"step": index, "action": step, "render_success": None,
                   "graph_success": False}
            report["actions"].append(row)
            action_error = None
            try:
                response = comm.render_script(
                    [step], find_solution=False, recording=True,
                    camera_mode=["FIRST_PERSON"], output_folder=str(directory / "recording"),
                    file_name_prefix=f"step-{index:02d}", frame_rate=10,
                    image_width=640, image_height=480)
                row["response"] = response
                if not isinstance(response, (tuple, list)) or len(response) != 2:
                    uncertain = True
                    raise ValueError("render_script 返回值不是 (success, message)")
                row["render_success"], row["message"] = response
                if row["render_success"] is not True:
                    uncertain = uncertain or type(row["render_success"]) is not bool
                    raise RuntimeError(f"render_script 未返回字面值 True：{response!r}")
            except (Exception, KeyboardInterrupt) as exc:
                action_error = exc
                if row["render_success"] is None:
                    uncertain = True
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
            try:
                graph, state = read_graph(comm, directory, f"graph_{index:02d}", report,
                                          report["food_id"], report["fridge_id"])
                row["graph_success"] = True
                row["state"] = state
            except Exception as exc:
                uncertain = True
                row["graph_error"] = {"type": type(exc).__name__, "message": str(exc)}
                error(exc, f"graph_{index:02d}")
            save(directory, f"step_{index:02d}.json", row)
            save(directory, "result.json", report)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if action_error is not None:
                raise action_error
            if not row["graph_success"]:
                raise UnknownObservation(f"第 {index} 步后无法读取有效场景图，停止后续动作")
        report["all_steps_succeeded"] = bool(
            len(report["actions"]) == len(steps) and
            all(row["render_success"] is True for row in report["actions"]))
    except (Exception, KeyboardInterrupt) as exc:
        uncertain = uncertain or isinstance(exc, UnknownObservation)
        error(exc, "execution")
    finally:
        prepared = report["execution_state"] == "PREPARED"
        if comm is not None and scene_ready and not prepared:
            try:
                _, final_state = read_graph(comm, directory, "graph_after", report,
                                           report.get("food_id", args.food_id),
                                           report.get("fridge_id", args.fridge_id))
                report["final_state"] = final_state
            except Exception as exc:
                uncertain = True
                error(exc, "final_graph")
        if final_state is not None and not uncertain and not prepared:
            report["task_success"] = bool(
                not report["errors"] and report["all_steps_succeeded"] and
                final_state["salmon_inside_fridge"] and final_state["fridge_closed"] and
                not final_state["salmon_held"])
        if not prepared:
            report["execution_state"] = ("COMPLETED" if report["task_success"] is True else
                                         "UNKNOWN" if report["task_success"] == "UNKNOWN" else "FAILED")
        report["recording_frames"] = len(list((directory / "recording").rglob("*.png")))
        for row in report["actions"]:
            row["recording_frames"] = len(list(
                (directory / "recording" / f"step-{row['step']:02d}").rglob("*.png")))
            save(directory, f"step_{row['step']:02d}.json", row)
        report["recording_state"] = (
            "NOT_REQUESTED" if prepared or not report["actions"] else
            "ALL_EXECUTED_STEPS_HAVE_FRAMES" if all(row["recording_frames"] > 0
                                                    for row in report["actions"]) else
            "MISSING_STEP_FRAMES")
        # 物理目标达成与可复核的完整录像/图记录分别报告。
        report["evidence_complete"] = bool(
            report["planned_steps"] and len(report["actions"]) == report["planned_steps"] and
            not uncertain and final_state is not None and
            all(row["graph_success"] and row["recording_frames"] > 0
                for row in report["actions"]))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(directory, "result.json", report)
        save(directory, "run.json", {key: report[key] for key in (
            "execution_state", "task_success", "scene", "food_id", "fridge_id", "character_id", "endpoint",
            "model_called", "plan_source", "plan_origin_declared", "api_sha256") if key in report})
    return (0 if report["task_success"] is True else 1), report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--api-dir", required=True, type=Path,
                        help="含 unity_simulator/comm_unity.py 的目录")
    result.add_argument("--output-dir", required=True, type=Path, help="本次新建的记录目录")
    result.add_argument("--port", type=int, default=8080, help="本机 Unity HTTP 端口")
    result.add_argument("--scene", type=int, default=0)
    result.add_argument("--food-id", type=int)
    result.add_argument("--fridge-id", type=int)
    operation = result.add_mutually_exclusive_group()
    operation.add_argument("--plan", type=Path, help='已有计划文件，严格为 {"steps": [...]}')
    operation.add_argument("--prepare", action="store_true",
                           help="配合 --run 只重置场景、添加角色并保存初始图，不执行动作")
    result.add_argument("--plan-source", choices=("manual", "model", "external"),
                        default="external", help="所提供计划的自报来源；脚本不调用模型")
    result.add_argument("--run", action="store_true", help="重置场景并执行；默认只检查文件")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError("--port 应在 1 到 65535 之间")
        if args.scene < 0:
            raise ValueError("--scene 不能为负数")
        if args.prepare and not args.run:
            raise ValueError("--prepare 需要 --run，因为它会重置 Unity 场景")
        if args.output_dir.exists():
            raise ValueError("--output-dir 已存在；请换一个新目录，保留已有记录")
        api_file = args.api_dir / "unity_simulator" / "comm_unity.py"
        if not api_file.is_file():
            raise ValueError("缺少 unity_simulator/comm_unity.py；核对 --api-dir")
        if args.plan and not args.plan.is_file():
            raise ValueError("--plan 文件不存在")
        if not args.run:
            print(json.dumps({"mode": "CHECK_ONLY", "task_success": "NOT_EVALUATED",
                              "model_called": False, "unity_contacted": False,
                              "api_file": str(api_file.resolve()),
                              "next_step": "先启动本机 Unity，再添加 --run；此检查未导入 API 或执行动作"},
                             ensure_ascii=False, indent=2))
            return 0
        code, report = run_checked(args)
        print("task_success=" + str(report["task_success"]), flush=True)
        if report["execution_state"] == "PREPARED":
            print("PREPARED：只保存初始场景图，尚未执行动作或验收任务。", flush=True)
        print("记录目录：" + str(args.output_dir.resolve()), flush=True)
        if report["errors"]:
            print(json.dumps(report["errors"], ensure_ascii=False, indent=2), file=sys.stderr)
        return code
    except (ValueError, OSError) as exc:
        print(f"检查失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
