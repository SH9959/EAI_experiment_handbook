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


def virtualhome_prompt(graph: dict, food_id: int | None = None, fridge_id: int | None = None) -> str:
    food = named_node(graph, "salmon", food_id)
    fridge = named_node(graph, "fridge", fridge_id)
    virtualhome_plan(graph, food["id"], fridge["id"])
    if not isinstance(graph.get("edges"), list):
        raise ValueError("场景图缺少 edges")
    scene = {"nodes": [{k: n[k] for k in ("id", "class_name", "states", "properties") if k in n}
                       for n in graph["nodes"]], "edges": graph["edges"]}
    return (
        f"将 salmon({food['id']}) 放入 fridge({fridge['id']}) 并关门。角色为 <char0>，初始双手为空。\n"
        '只返回一个 JSON 对象，格式为 {"steps": ["一条动作", "下一条动作"]}，不要代码围栏或解释。\n'
        "动作格式为 <char0> [ACTION] <class_name> (id)。只允许 WALK、GRAB、OPEN、CLOSE，"
        "以及双参数 PUTIN：<char0> [PUTIN] <salmon> (id) <fridge> (id)。\n"
        "仅操作指定的 salmon 和 fridge，最多 20 步；按场景开闭状态和动作前置条件规划。\n"
        "以下为当前环境图：\n" + json.dumps(scene, ensure_ascii=False)
    )


def check_virtualhome_response(graph: dict, response: dict,
                               food_id: int | None = None, fridge_id: int | None = None) -> list[str]:
    """校验模型动作的格式和对象；可达性及执行结果由 Unity 判断。"""
    food = named_node(graph, "salmon", food_id)
    fridge = named_node(graph, "fridge", fridge_id)
    if not isinstance(response, dict) or set(response) != {"steps"}:
        raise ValueError('模型回答必须是仅含 steps 的 JSON 对象')
    steps = response["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise ValueError("steps 必须含 1 到 20 条动作")
    expected = {"salmon": food["id"], "fridge": fridge["id"]}
    pattern = r"<char0> \[(WALK|GRAB|OPEN|CLOSE|PUTIN)\] <(salmon|fridge)> \(([0-9]+)\)(?: <(salmon|fridge)> \(([0-9]+)\))?"
    for i, step in enumerate(steps, 1):
        match = re.fullmatch(pattern, step) if isinstance(step, str) else None
        if match is None:
            raise ValueError(f"第 {i} 条动作格式或动作名不合法")
        action, first, first_id, second, second_id = match.groups()
        if int(first_id) != expected[first] or (second and int(second_id) != expected[second]):
            raise ValueError(f"第 {i} 条动作的 ID 与选定场景对象不符")
        if action == "PUTIN":
            valid = first == "salmon" and second == "fridge"
        else:
            valid = second is None and (action == "WALK" or
                    (action == "GRAB" and first == "salmon") or
                    (action in ("OPEN", "CLOSE") and first == "fridge"))
        if not valid:
            raise ValueError(f"第 {i} 条动作的参数数量或对象类型不符")
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("action", help="只检查单个动作格式，不执行")
    p.add_argument("--text", required=True)
    p.add_argument("--skills", type=Path)
    for command, help_text in (("vh-plan", "生成规则候选脚本"),
                               ("vh-prompt", "从环境图生成模型问题文本"),
                               ("vh-check", "检查模型回答的动作格式和物体 ID")):
        p = sub.add_parser(command, help=help_text + "，不运行 Unity 或调用模型")
        p.add_argument("--graph", required=True, type=Path)
        p.add_argument("--food-id", type=int)
        p.add_argument("--fridge-id", type=int)
        if command == "vh-check":
            p.add_argument("--response", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "action":
            skills = supported_actions(args.skills) if args.skills else COURSE_SKILLS
            name, target = parse_action(args.text, skills)
            result = {"mode": "FORMAT_ONLY", "action": name, "target": target,
                      "executed": False, "task_success": "NOT_EVALUATED"}
        else:
            graph = json.loads(args.graph.read_text(encoding="utf-8-sig"))
            if args.command == "vh-prompt":
                print(virtualhome_prompt(graph, args.food_id, args.fridge_id))
                return 0
            if args.command == "vh-check":
                response = json.loads(args.response.read_text(encoding="utf-8-sig"))
                steps = check_virtualhome_response(graph, response, args.food_id, args.fridge_id)
            else:
                steps = virtualhome_plan(graph, args.food_id, args.fridge_id)
            result = {"mode": "PLAN_ONLY", "steps": steps,
                      "executed": False, "task_success": "NOT_EVALUATED"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"检查失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
