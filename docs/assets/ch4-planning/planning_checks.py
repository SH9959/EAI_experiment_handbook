"""任务规划的输入/状态检查。纯 Python；不连接仿真器或模型。"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

COURSE_SKILLS = ("GotoObject", "PickupObject", "PutObject", "OpenObject", "CloseObject",
                "SliceObject", "ToggleObjectOn", "ToggleObjectOff", "Done")


def parse_action(text: str, skills=COURSE_SKILLS) -> tuple[str, str | None]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("动作为空")
    text = text.strip()
    if any(c in text for c in "\n\r;`"):
        raise ValueError("每次只接受一条 Action-Target，不接受代码块或多步文本")
    action, separator, target = text.partition("-")
    canonical = {x.casefold(): x for x in COURSE_SKILLS}
    names = {x.casefold(): canonical[x.casefold()] for x in skills
             if isinstance(x, str) and x.casefold() in canonical}
    name = names.get(action.strip().casefold())
    if name is None:
        raise ValueError("动作不在课程技能表内")
    if name.casefold() == "done":
        if separator:
            raise ValueError("Done 不应带物体参数")
        return name, None
    target = target.strip()
    if not separator or not target or any(c.isspace() for c in target):
        raise ValueError("需要 Action-ObjectType 或 Action-objectId")
    # objectId 可含负号，因此只在第一个 '-' 分隔。
    return name, target


def find_object(objects: list[dict], target: str) -> dict:
    if not isinstance(target, str) or not target:
        raise ValueError("目标不能为空")
    if not isinstance(objects, list) or any(not isinstance(o, dict) for o in objects):
        raise ValueError("场景 objects 应为对象字典列表")
    found = [o for o in objects if o.get("objectId") == target]
    if not found and "|" not in target:
        found = [o for o in objects if str(o.get("objectType", "")).casefold() == target.casefold()]
    if not found:
        raise ValueError(f"当前场景没有精确匹配的目标：{target}")
    if len(found) != 1:
        raise ValueError(f"目标 {target} 有多个实例；请填写完整 objectId")
    return found[0]


def action_feedback(metadata: dict) -> tuple[bool, str]:
    if not isinstance(metadata, dict):
        raise ValueError("环境反馈应为 metadata 对象")
    success = metadata.get("lastActionSuccess")
    if type(success) is not bool:
        raise ValueError("metadata.lastActionSuccess 缺失或不是布尔值")
    return success, "执行成功" if success else str(metadata.get("errorMessage") or "环境未给出错误信息")


def supported_actions(action_file: Path) -> tuple[str, ...]:
    rows = json.loads(action_file.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("action.json 应为非空列表")
    names = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError("每个技能必须有字符串 name")
        name = row["name"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name):
            raise ValueError("技能名称格式不合法")
        canonical = {x.casefold(): x for x in COURSE_SKILLS}
        if name.casefold() not in canonical:
            raise ValueError("技能表包含本入口不支持的动作")
        name = canonical[name.casefold()]
        if name.casefold() in {n.casefold() for n in names}:
            raise ValueError("技能名称重复")
        names.append(name)
    return tuple(names)


def named_node(graph: dict, class_name: str, node_id: int | None = None) -> dict:
    if not isinstance(graph, dict):
        raise ValueError("场景图应为包含 nodes 和 edges 的对象")
    if node_id is not None and type(node_id) is not int:
        raise ValueError("指定的节点 ID 必须是整数")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("场景图缺少 nodes")
    ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    if len(ids) != len(nodes) or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("场景节点必须具有互不重复的整数 id")
    found = [n for n in nodes if n.get("class_name") == class_name and (node_id is None or n["id"] == node_id)]
    if len(found) != 1:
        raise ValueError(f"{class_name} 需要唯一匹配；缺失或重名时核对场景/指定节点 ID")
    return found[0]


def virtualhome_plan(graph: dict, food_id: int | None = None, fridge_id: int | None = None) -> list[str]:
    """生成教材三文鱼任务的候选脚本；不声称候选脚本可执行或任务完成。"""
    food = named_node(graph, "salmon", food_id)
    fridge = named_node(graph, "fridge", fridge_id)
    a, b = food["id"], fridge["id"]
    states = fridge.get("states")
    if not isinstance(states, list) or sum(s in states for s in ("OPEN", "CLOSED")) != 1:
        raise ValueError("冰箱开闭状态未知或互相矛盾，先检查环境图")
    steps = [f"<char0> [WALK] <salmon> ({a})", f"<char0> [GRAB] <salmon> ({a})", f"<char0> [WALK] <fridge> ({b})"]
    if "OPEN" not in states:
        steps.append(f"<char0> [OPEN] <fridge> ({b})")
    steps += [f"<char0> [PUTIN] <salmon> ({a}) <fridge> ({b})", f"<char0> [CLOSE] <fridge> ({b})"]
    return steps


def inside_relation(graph: dict, food_id: int, fridge_id: int) -> bool:
    edges = graph.get("edges")
    if not isinstance(edges, list):
        raise ValueError("缺少 edges，无法判断给定场景图的包含关系")
    named_node(graph, "salmon", food_id)
    named_node(graph, "fridge", fridge_id)
    return any(e.get("from_id") == food_id and e.get("to_id") == fridge_id and
               e.get("relation_type") == "INSIDE" for e in edges if isinstance(e, dict))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("action", help="只检查单个动作格式，不执行")
    p.add_argument("--text", required=True)
    p.add_argument("--skills", type=Path)
    p = sub.add_parser("vh-plan", help="从实际导出的环境图生成候选脚本，不运行 Unity")
    p.add_argument("--graph", required=True, type=Path)
    p.add_argument("--food-id", type=int)
    p.add_argument("--fridge-id", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "action":
            skills = supported_actions(args.skills) if args.skills else COURSE_SKILLS
            name, target = parse_action(args.text, skills)
            result = {"mode": "FORMAT_ONLY", "action": name, "target": target,
                      "executed": False, "task_success": "NOT_EVALUATED"}
        else:
            graph = json.loads(args.graph.read_text(encoding="utf-8-sig"))
            result = {"mode": "PLAN_ONLY", "steps": virtualhome_plan(graph, args.food_id, args.fridge_id),
                      "executed": False, "task_success": "NOT_EVALUATED"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"检查失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
