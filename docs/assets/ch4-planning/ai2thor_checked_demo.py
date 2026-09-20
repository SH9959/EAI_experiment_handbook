"""课程 AI2THOR 示例的手册侧修订入口。默认仅预检；--run 才启动仿真。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from planning_checks import action_feedback, find_object, parse_action, supported_actions

SOURCE_BLOBS = {
    "myController.py": "aadd9fd3fdbc8274ea2dbb28a70ef0ed9989b55c",
    "action.json": "189c5672cce57400c6858517def3987c4789630a",
}
TASK = "place a cup with a knife in it on the kitchen counter space"


class ActionOutcomeError(RuntimeError):
    """动作已提交，但不能取得可信反馈；不应再标记为未执行。"""
    def __init__(self, message, executed):
        super().__init__(message)
        self.executed = executed


def safe_message(value, key="") -> str:
    message = str(value)
    if key:
        message = message.replace(key, "[REDACTED]")
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", message)


def check_source(directory: Path) -> None:
    for name, expected in SOURCE_BLOBS.items():
        raw = (directory / name).read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if actual != expected:
            raise ValueError(f"{name} 与本页核对版本不同。保留该文件，先核对版本，不覆盖课程仓库。")


def checked_controller(course_class):
    """修复课程派生控制器的目标查找、空候选和反馈；不改写来源文件。"""
    class CheckedController(course_class):
        def _findObject(self, target):
            return [find_object(self.last_event.metadata["objects"], target)], ""

        def _getTeleportPose(self, obj):
            event = self.step(action="GetInteractablePoses", objectId=obj["objectId"],
                              horizons=[-30. + 90. * i / 29 for i in range(30)], standings=[True])
            ok, message = action_feedback(event.metadata)
            poses = event.metadata.get("actionReturn")
            if not ok or not isinstance(poses, list) or not poses:
                raise ValueError(f"没有可用的接近姿态：{message}")
            origin = obj.get("position")
            def finite_number(value):
                return type(value) in (int, float) and math.isfinite(value)
            if not isinstance(origin, dict) or not all(finite_number(origin.get(k)) for k in ("x", "y", "z")):
                raise ValueError("目标坐标缺失或不是有限数值")
            def distance(p):
                return sum((p[k] - origin[k])**2 for k in ("x", "y", "z"))
            poses = [p for p in poses if isinstance(p, dict) and
                     all(finite_number(p.get(k)) for k in ("x", "y", "z", "rotation", "horizon"))]
            if not poses:
                raise ValueError("环境返回的接近姿态缺少必要字段或有限数值")
            pose = min(poses, key=distance)
            return {k: pose[k] for k in ("x", "y", "z")}, pose["rotation"], pose["horizon"]

        def execute_checked(self, text, skills):
            action, target = parse_action(text, skills)
            if action == "Done":
                raise ValueError("Done 必须由主循环处理，不能调用机器人动作方法")
            obj = find_object(self.last_event.metadata["objects"], target)
            if action == "PutObject" and obj.get("receptacle") is not True:
                raise ValueError("PutObject 的目标必须是容器/承载面，不是手中物体")
            if action == "PickupObject" and obj.get("pickupable") is not True:
                raise ValueError("目标不可拾取")
            if action in {"OpenObject", "CloseObject"} and obj.get("openable") is not True:
                raise ValueError("目标不可开闭")
            command, _ = self._genAI2ThorAPI(action, obj["objectId"])
            try:
                event = self.step(**command)
            except Exception as exc:
                raise ActionOutcomeError(f"动作请求已尝试，但执行状态未知：{exc}", None) from exc
            try:
                ok, message = action_feedback(event.metadata)
            except (ValueError, AttributeError, TypeError) as exc:
                raise ActionOutcomeError(f"环境已返回动作结果，但成功状态无法核验：{exc}", True) from exc
            return event, ok, message
    return CheckedController


def response_text(response) -> str:
    def field(value, name):
        return value.get(name) if isinstance(value, dict) else getattr(value, name, None)
    status = field(response, "status_code")
    if status != 200:
        # 不打印含请求内容的异常对象，避免把密钥带入截图。
        raise ValueError(f"模型请求失败，HTTP {status}；核对地域、权限和额度后再试")
    choices = field(field(response, "output"), "choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("模型响应缺少 output.choices，未取得可执行动作")
    content = field(field(choices[0], "message"), "content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(part["text"] for part in content
                         if isinstance(part, dict) and isinstance(part.get("text"), str))
    else:
        raise ValueError("响应中没有可解析的文字")
    if not text.strip():
        raise ValueError("模型返回空动作")
    return text.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course-dir", required=True, type=Path,
                        help="EAI_project 内 for_ai2thor 的目录")
    parser.add_argument("--mode", choices=["manual", "llm"], default="manual")
    parser.add_argument("--run", action="store_true", help="允许启动 Unity（首次可能下载仿真程序）")
    parser.add_argument("--send", action="store_true", help="仅 LLM 模式：允许发送图片/文字并消耗 API 额度")
    parser.add_argument("--model", default="qwen-vl-plus")
    parser.add_argument("--scene", default="FloorPlan10")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("runs/planning"))
    args = parser.parse_args(argv)
    if not 1 <= args.max_steps <= 100:
        parser.error("--max-steps 必须在 1 到 100 之间")
    if args.send and args.mode != "llm":
        parser.error("--send 仅用于 --mode llm")
    controller = None
    result_dir = None
    records = []
    exit_code = 0
    stop_reason = "NOT_STARTED"
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    try:
        args.course_dir = args.course_dir.resolve()
        check_source(args.course_dir)
        skills = supported_actions(args.course_dir / "action.json")
        if not args.run:
            print("CHECK ONLY：课程文件版本及技能表可读；没有启动 Unity、调用模型或验证任务成功。")
            return 0
        if args.mode == "llm" and (not args.send or not key):
            raise ValueError("LLM 模式还需 --send 和有效 DASHSCOPE_API_KEY；未启动仿真")
        if args.mode == "llm" and not args.model.strip():
            raise ValueError("模型名不能为空；未启动仿真")
        from PIL import Image
        spec = importlib.util.spec_from_file_location("_eai_course_controller", args.course_dir / "myController.py")
        if spec is None or spec.loader is None:
            raise ValueError("无法加载已核对的课程控制器")
        course = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(course)
        if args.mode == "llm":
            import dashscope
            base = os.environ.get("DASHSCOPE_HTTP_BASE_URL")
            if base:
                from urllib.parse import urlparse
                parsed = urlparse(base)
                official_hosts = {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com"}
                if parsed.scheme != "https" or parsed.hostname not in official_hosts or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443) or parsed.path.rstrip("/") != "/api/v1":
                    raise ValueError("端点应为无凭据的 HTTPS DashScope 原生 /api/v1 地址")
                dashscope.base_http_api_url = base.rstrip("/")
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        result_dir = args.output.resolve() / run_id
        result_dir.mkdir(parents=True, exist_ok=False)
        cls = checked_controller(course.MyController)
        controller = cls(scene=args.scene, width=640, height=480)
        controller.reset(args.scene)
        history = []
        stop_reason = "STEP_LIMIT"
        def snapshot(index):
            image_path = result_dir / f"frame_{index:03d}.png"
            Image.fromarray(controller.last_event.frame).save(image_path)
            (result_dir/f"metadata_{index:03d}.json").write_text(
                json.dumps(controller.last_event.metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
            return image_path
        image_path = snapshot(0)
        print(f"场景：{args.scene}。图像和状态保存于 {result_dir}")
        print("这是课程的粗粒度/部分 forceAction 演示，不是标准导航指标评测。")
        print("Done 仅结束循环，不自动表示任务成功。Ctrl+C 可停止。")
        for index in range(1, args.max_steps + 1):
            objects = controller.last_event.metadata["objects"]
            print("当前物体：", [o["objectId"] for o in objects])
            if args.mode == "manual":
                text = input("输入一个技能动作（例如 GotoObject-Cup）或 Done：")
            else:
                input("回车发送本轮图像和任务；Ctrl+C 停止：")
                prompt = course.get_prompt(TASK, course.get_all_objects_in_scene(controller.last_event),
                    json.loads((args.course_dir/"action.json").read_text(encoding="utf-8-sig")), skills,
                    history_of_actions=history, current_image=str(image_path),
                    feed_back_message=history[-1][1] if history else "")
                prompt += "\nPutObject 的目标是容器或台面。完成时只输出 Done。重复类别请使用完整 objectId。\n" + str([o["objectId"] for o in objects])
                response = dashscope.MultiModalConversation.call(api_key=key, model=args.model,
                    messages=[{"role": "user", "content": [{"image": image_path.as_uri()}, {"text": prompt}]}],
                    stream=False, max_tokens=128)
                text = response_text(response)
                print("模型动作：", safe_message(text, key))
            try:
                name, _ = parse_action(text, skills)
                if name == "Done":
                    stop_reason = "USER_DONE" if args.mode == "manual" else "MODEL_DONE"
                    records.append({"step": index, "action": safe_message(text, key), "executed": False, "reason": stop_reason})
                    break
                event, ok, feedback = controller.execute_checked(text, skills)
            except ActionOutcomeError as exc:
                records.append({"step": index, "action": safe_message(text, key),
                                "executed": exc.executed, "lastActionSuccess": None,
                                "feedback": safe_message(exc, key)})
                stop_reason, exit_code = "ACTION_OUTCOME_UNKNOWN", 2
                print(safe_message(exc, key), file=sys.stderr)
                break
            except ValueError as exc:
                feedback = safe_message(exc, key)
                records.append({"step": index, "action": safe_message(text, key), "executed": False, "feedback": feedback})
            else:
                feedback = safe_message(feedback, key)
                records.append({"step": index, "action": safe_message(text, key), "executed": True, "lastActionSuccess": ok, "feedback": feedback})
                # 截图/写盘失败不能把已执行的动作改记为未执行，也不能重复登记同一步。
                image_path = snapshot(index)
            history.append((text, feedback))
            print(feedback)
    except (KeyboardInterrupt, EOFError):
        stop_reason, exit_code = "USER_INTERRUPTED", 130
    except Exception as exc:
        message = safe_message(exc, key)
        print(f"停止：{message}", file=sys.stderr)
        stop_reason, exit_code = "ERROR", 2
    finally:
        if result_dir:
            payload = {"mode": args.mode, "scene": args.scene, "instruction": TASK,
                       "stop_reason": stop_reason, "task_success": "NOT_EVALUATED",
                       "note": "需对照最终状态/图像验收；手动规划不等于模型规划。", "steps": records}
            raw = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
            if key:
                raw = raw.replace(key, "[REDACTED]")
            try:
                (result_dir / "run.json").write_text(raw, encoding="utf-8")
            except OSError as exc:
                print(f"运行记录保存失败：{type(exc).__name__}", file=sys.stderr)
                exit_code = 2
        if controller is not None:
            try:
                controller.stop()
            except Exception:
                print("仿真退出失败；请确认 Unity 进程已停止。", file=sys.stderr)
                exit_code = 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
