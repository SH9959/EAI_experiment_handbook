"""AnyGrasp 前置资料和相机几何检查。不导入 SDK，不启动机器人。"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import sysconfig
from pathlib import Path


def intrinsics(width: int, height: int, fov_degrees: float) -> tuple[float, float, float, float]:
    if (isinstance(width, bool) or isinstance(height, bool)
            or not isinstance(width, int) or not isinstance(height, int)
            or width <= 0 or height <= 0):
        raise ValueError("图像尺寸必须为正整数")
    if not math.isfinite(fov_degrees) or not 0 < fov_degrees < 180:
        raise ValueError("垂直 FOV 必须在 0 到 180 度之间")
    focal = height / (2 * math.tan(math.radians(fov_degrees) / 2))
    return focal, focal, width / 2, height / 2


def metric_depth(z_buffer: float, near: float, far: float) -> float:
    if not all(math.isfinite(v) for v in (z_buffer, near, far)):
        raise ValueError("深度参数不能含 NaN 或 Inf")
    if not (0 < near < far and 0 <= z_buffer <= 1):
        raise ValueError("要求 0 < near < far 且 0 <= Z-buffer <= 1")
    return near * far / (far - (far - near) * z_buffer)


def backproject(u: float, v: float, depth: float, camera: tuple) -> tuple[float, float, float]:
    fx, fy, cx, cy = camera
    if not all(math.isfinite(x) for x in (u, v, depth, fx, fy, cx, cy)):
        raise ValueError("反投影输入不能含 NaN 或 Inf")
    if depth <= 0 or fx <= 0 or fy <= 0:
        raise ValueError("深度和焦距必须大于零")
    return (u - cx) * depth / fx, (v - cy) * depth / fy, depth


def validate_rigid(matrix: list[list[float]]) -> None:
    if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
        raise ValueError("齐次矩阵必须为 4×4")
    if not all(math.isfinite(x) for row in matrix for x in row):
        raise ValueError("矩阵不能含 NaN 或 Inf")
    if any(abs(matrix[3][j] - [0, 0, 0, 1][j]) > 1e-5 for j in range(4)):
        raise ValueError("齐次矩阵最后一行应为 [0,0,0,1]")
    r = matrix
    for i in range(3):
        for j in range(3):
            if abs(sum(r[k][i] * r[k][j] for k in range(3)) - (i == j)) > 1e-5:
                raise ValueError("旋转部分不正交")
    det = (r[0][0] * (r[1][1]*r[2][2]-r[1][2]*r[2][1])
           - r[0][1] * (r[1][0]*r[2][2]-r[1][2]*r[2][0])
           + r[0][2] * (r[1][0]*r[2][1]-r[1][1]*r[2][0]))
    if abs(det - 1) > 1e-5:
        raise ValueError("旋转应满足 det(R)=+1，不能使用镜像矩阵")


def world_from_camera(view_column_major: list[float]) -> list[list[float]]:
    """返回 world_T_cam_cv；输入是 PyBullet 的 16 项列主序 OpenGL view。"""
    if len(view_column_major) != 16:
        raise ValueError("view 应有 16 项")
    view = [[float(view_column_major[4*j+i]) for j in range(4)] for i in range(4)]
    validate_rigid(view)
    # 刚体逆变换：R^T，-R^T t；再右乘 diag(1,-1,-1,1)。
    signs = [1, -1, -1]
    out = [[view[j][i] * signs[j] for j in range(3)] +
           [-sum(view[k][i]*view[k][3] for k in range(3))] for i in range(3)]
    out.append([0., 0., 0., 1.])
    validate_rigid(out)
    return out


def transform_point(matrix: list[list[float]], point: tuple) -> tuple:
    validate_rigid(matrix)
    if len(point) != 3 or not all(math.isfinite(x) for x in point):
        raise ValueError("点必须含三个有限坐标")
    return tuple(sum(matrix[i][j]*point[j] for j in range(3)) + matrix[i][3] for i in range(3))


def file_state(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    if path.stat().st_size == 0:
        return "EMPTY"
    with path.open("rb") as stream:
        if stream.read(128).startswith(b"version https://git-lfs.github.com/spec/v1"):
            return "LFS_POINTER_ONLY"
    return "PRESENT_NOT_EXECUTED"


def binary_state(detection: Path, extension_suffix: str) -> str:
    """仅按当前解释器的完整扩展后缀找文件，不导入或断言二进制可用。"""
    loaded_state = file_state(detection / "gsnet.so")
    if loaded_state != "MISSING":
        return ("PRESENT_ABI_NOT_VALIDATED" if loaded_state == "PRESENT_NOT_EXECUTED"
                else loaded_state)
    candidate = detection / "gsnet_versions" / ("gsnet" + extension_suffix)
    state = file_state(candidate)
    return "MATCHING_NAME_NOT_LOADED" if state == "PRESENT_NOT_EXECUTED" else state


def license_part_state(directory: Path, pattern: str) -> str:
    """检查授权包的每类文件；不读取授权内容或在报告中列出申请人名称。"""
    states = [file_state(path) for path in directory.glob(pattern)]
    if not states:
        return "MISSING"
    for blocker in ("MISSING", "EMPTY", "LFS_POINTER_ONLY"):
        if blocker in states:
            return blocker
    return "PRESENT_NOT_EXECUTED"


def check_files(sdk: Path | None, sim_dir: Path | None, system: str | None = None,
                extension_suffix: str | None = None) -> dict:
    system = system or platform.system()
    extension_suffix = extension_suffix or sysconfig.get_config_var("EXT_SUFFIX") or ".unsupported"
    report = {"mode": "FILES_ONLY", "platform": system,
              "python": platform.python_version(), "extension_suffix": extension_suffix,
              "checks": [],
              "sdk_inference": "NOT_RUN", "robot": "NOT_STARTED"}
    if system != "Linux":
        report["checks"].append({"item": "教材 Linux SDK 二进制", "state": "PLATFORM_MISMATCH"})
    if sdk:
        detection = sdk / "grasp_detection"
        for relative in ("README.md", "license_registration/README.md", "requirements.txt", "grasp_detection/demo.py"):
            report["checks"].append({"item": relative, "state": file_state(sdk / relative)})
        report["checks"].append({"item": "gsnet 二进制文件（不验证 ABI）",
                                 "state": binary_state(detection, extension_suffix)})
        demo = detection / "demo.py"
        needs_seg = demo.is_file() and "seg_mask.png" in demo.read_text(encoding="utf-8", errors="replace")
        images = ["color.png", "depth.png"] + (["seg_mask.png"] if needs_seg else [])
        for name in images:
            report["checks"].append({"item": "grasp_detection/example_data/"+name, "state": file_state(detection/"example_data"/name)})
        for relative in ("license/licenseCfg.json", "log/checkpoint_detection.tar"):
            report["checks"].append({"item": "grasp_detection/"+relative, "state": file_state(detection/relative)})
        for pattern in ("*.public_key", "*.signature", "*.lic"):
            report["checks"].append({"item": "grasp_detection/license/" + pattern,
                                     "state": license_part_state(detection / "license", pattern)})
        report["license_validation"] = "NOT_RUN；各类文件存在不等于内容匹配或授权有效"
    else:
        report["checks"].append({"item": "SDK 目录未提供", "state": "NOT_CHECKED"})
    if sim_dir:
        for name in ("grasp_sim_anygrasp.py", "anygrasp_model.py", "log/checkpoint_detection.tar"):
            report["checks"].append({"item": "课程仿真工作目录/"+name, "state": file_state(sim_dir/name)})
    else:
        report["checks"].append({"item": "课程仿真工作目录未提供", "state": "NOT_CHECKED"})
    report["blockers_found"] = any(row["state"] in {
        "MISSING", "EMPTY", "LFS_POINTER_ONLY", "PLATFORM_MISMATCH", "MATCHING_NAME_NOT_LOADED"
    } for row in report["checks"])
    report["ready_to_grasp"] = False  # 文件检查不构成抓取授权或安全验收。
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("geometry", help="计算一个解析例子；不生成抓取结果")
    p = sub.add_parser("files", help="只读检查已下载资料；不安装、不联网")
    p.add_argument("--sdk", type=Path)
    p.add_argument("--sim-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "geometry":
            k = intrinsics(960, 720, 35)
            print(json.dumps({"mode": "ANALYTIC_EXAMPLE_NOT_GRASP", "fx_fy_cx_cy": k,
                "depth_z0_z1": [metric_depth(0, .01, 10), metric_depth(1, .01, 10)],
                "center_at_one_m": backproject(480, 360, 1, k)}, ensure_ascii=False, indent=2))
            return 0
        report = check_files(args.sdk, args.sim_dir)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if report["blockers_found"] else 0
    except (ValueError, OSError) as exc:
        print(f"检查失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
