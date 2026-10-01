# 第 4 章：iGibson 具身导航

> 对应教材：**4.4.4 具身导航实验**（印刷页 151–154）。

## 一、实验目标

在 iGibson 的交互式室内场景中运行移动机器人，完成“读取观测—生成动作—执行—判断是否到达”的循环，记录轨迹、碰撞和导航结果。比较随机动作与朝向目标的反馈控制，分析家具和可移动物体对导航的影响。

教材给出 `eai-eval + behavior_eval + iGibson` 的安装路线。本页沿用该路线，并补充同一 iGibson 分支提供的交互式导航任务。`eai-eval` 命令行用于具身决策评测，导航仿真通过 `iGibsonEnv` 运行。

## 二、实验环境配置

### 2.1 系统与资源

本页命令在已启用 Conda 的终端中逐行执行；Windows 可使用 Anaconda Prompt。

| 项目 | 要求与检查 |
| --- | --- |
| 系统 | 教材采用 Windows 10、Visual Studio 2017 的 C++ 工具和 Windows 10 SDK；Linux 需 C++ 编译器及 EGL 开发库 |
| GPU | 教材要求 NVIDIA 显存大于 6 GB、驱动 ≥ 384；执行 `nvidia-smi` 记录实际型号与驱动 |
| CUDA/cuDNN | 教材要求 CUDA ≥ 9.0、cuDNN ≥ 7；用 `nvcc --version` 检查编译工具，cuDNN 版本查对应安装目录的头文件 |
| Python/CMake | Python 3.8；CMake 从 Conda 安装。下文限制为 3.x，以适配此分支的旧 CMake 配置 |
| 资产 | iGibson 场景、机器人、YCB 对象和密钥；上游标注场景压缩包约 20 GB，还需预留解压空间 |
| 图形环境 | GUI 需要可用的桌面 OpenGL 上下文；无窗口模式仍需要受支持的 GPU 渲染环境 |

`nvidia-smi` 显示的 CUDA 数字是驱动支持能力，不能代替 `nvcc` 检查。教材最低版本不是现代机器的完整兼容组合；编译器、驱动或渲染检查失败时，先完成相应适配再运行任务。

### 2.2 安装教材指定的软件

以下固定版本来自 2026-10-01 的[上游源码核对](../assets/ch4-navigation/verification.md)，用于明确接口依据；完整依赖仍需在实验机器上安装并验证。在独立实验目录内执行：

```bash
mkdir ch4-navigation
cd ch4-navigation
conda create -n eai-eval python=3.8 -y
conda activate eai-eval
git clone https://github.com/embodied-agent-interface/embodied-agent-interface.git
cd embodied-agent-interface
git checkout 531c62f8df2cb392bdf1907923c76da41cad4fe6
python -m pip install -e .
conda install "cmake>=3.1,<4" -y
git clone --recursive https://github.com/embodied-agent-interface/iGibson.git
git -C iGibson checkout a4f6021c47d03612b429170b282e983aa916bdaf
git -C iGibson submodule update --init --recursive
python -m behavior_eval.utils.install_igibson_utils
python -m pip check
```

教材也允许 `python -m pip install eai-eval`；本页选择源码安装以固定版本。安装器会使用当前目录下已有的 `iGibson`，因此先检出指定提交，再调用教材命令。后续命令继续在 `embodied-agent-interface` 根目录执行。

### 2.3 准备资产并检查接口

先阅读[上游数据说明与申请入口](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/docs/dataset.md)，按要求取得使用资格及密钥。确认磁盘空间与网络可用后，执行教材的下载命令；出现许可提示时，根据本人是否同意作答。

```bash
git lfs version
python -m behavior_eval.utils.download_utils
python -c "import igibson, behavior_eval; from igibson.envs.igibson_env import iGibsonEnv; print('iGibson:', igibson.__version__); print('source:', igibson.__file__); print('assets:', igibson.assets_path); print('dataset:', igibson.ig_dataset_path); print('key:', igibson.key_path)"
```

下载器依次处理交互场景、通用资产、Git LFS 文件和密钥。若实验室已经配置资产，可由教师提供对应路径，通过该安装中的 `igibson/global_config.yaml` 配置后执行导入检查，避免重复下载。此分支要求资产和场景 `VERSION` 均处于 `[2.0.6, 2.2.4)`；目录存在但版本文件缺失不能视为下载完成。

导入检查应显示 iGibson `2.2.3`，且来源为上述检出的目录。保存环境记录：

```bash
python -m pip freeze > navigation-environment.txt
git rev-parse HEAD > navigation-eai-commit.txt
git -C iGibson rev-parse HEAD > navigation-igibson-commit.txt
```

## 三、实验过程

### 3.1 运行官方环境示例

先运行一个短回合，检查场景、摄像头和动作接口：

```bash
python -c "from igibson.examples.environments.env_int_example import main; main(short_exec=True)"
```

此入口来自[官方交互场景示例](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/examples/environments/env_int_example.py)。它在 `Rs_int` 中加载 Turtlebot，随机执行最多 100 步，然后关闭环境。应能看到室内场景与机器人运动；这一步只检查仿真是否工作，不能证明成功到达目标。

在已经配置 GPU 无窗口渲染的机器上，可改为 `main(headless=True, short_exec=True)`。若示例无法创建环境，保存完整报错并按第五节处理，暂不进入下一步。

### 3.2 运行交互式导航回合

本实验使用上游配置 `igibson/configs/turtlebot_interactive_nav.yaml`：

| 参数或接口 | 本实验含义 |
| --- | --- |
| `scene_id: Rs_int` | 有家具和交互对象的室内场景 |
| `task: interactive_nav_random` | 随机采样起点与目标，额外加载五个可移动 YCB 对象 |
| `task_obs` | 目标在机器人坐标系中的距离、方位角，以及当前线速度、角速度 |
| `rgb`、`depth`、`scan` | 视觉与激光观测；深度和激光输出经过归一化，不能直接按米解读 |
| 动作 | 两维归一化命令 `[前进, 转向]`，由差速控制器转换成轮速 |
| 终止 | 到达目标、超出碰撞限制、越界或达到 500 步；到达阈值为平面距离小于 0.36 m |

将下列**本页练习代码**保存为当前目录下的 `navigation_trial.py`。它调用上述固定版本的真实接口，保存一个完整回合；无需训练模型或调用外部 API。首次使用 `random`，再使用 `goal` 比较反馈控制。

```python
import json
import random
import sys
from pathlib import Path

import igibson
import numpy as np
import yaml
from PIL import Image
from igibson.envs.igibson_env import iGibsonEnv

seed = int(sys.argv[1])
policy = sys.argv[2]
if policy not in {"random", "goal"}:
    raise ValueError("policy must be random or goal")
random.seed(seed)
np.random.seed(seed)
out = Path("navigation-results") / f"seed-{seed}-{policy}"
out.mkdir(parents=True, exist_ok=False)
config_path = Path(igibson.configs_path) / "turtlebot_interactive_nav.yaml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
config.update(enable_shadow=False, enable_pbr=False)
(out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
env = iGibsonEnv(config_file=config, mode="gui_interactive", automatic_reset=False)

def save_rgb(name, state):
    pixels = (np.clip(state["rgb"], 0, 1) * 255).astype(np.uint8)
    Image.fromarray(pixels).save(out / name)

try:
    env.action_space.seed(seed)
    state = env.reset()  # This iGibson version returns only the observation.
    print("observations:", {k: np.shape(v) for k, v in state.items()})
    print("action space:", env.action_space)
    save_rgb("start.png", state)
    start = env.robots[0].get_position()[:2].copy()
    target = env.task.target_pos[:2].copy()
    shortest = float(env.task.geodesic_dist)
    if not np.isfinite(shortest) or shortest <= 0:
        raise RuntimeError("Invalid initial shortest-path distance")
    positions, actions, rewards = [start.tolist()], [], []
    done = False
    for step in range(config["max_step"]):
        if policy == "random":
            action = env.action_space.sample()
        else:
            bearing = float(state["task_obs"][1])
            action = np.array([0.2 if abs(bearing) < 0.25 else 0.0,
                               np.clip(bearing, -0.15, 0.15)], dtype=np.float32)
        state, reward, done, info = env.step(action)
        positions.append(env.robots[0].get_position()[:2].tolist())
        actions.append(action.tolist())
        rewards.append(float(reward))
        if done:
            break
    save_rgb("end.png", state)
    xy = np.asarray(positions)
    length = float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum())
    success = bool(info["success"])
    result = dict(seed=seed, policy=policy, scene=config["scene_id"],
                  task=config["task"], start=start.tolist(), target=target.tolist(),
                  steps=len(actions), done=bool(done), success=success,
                  collision_steps=int(info["collision_step"]),
                  final_distance_m=float(np.linalg.norm(xy[-1] - target)),
                  shortest_path_m=shortest, path_length_m=length,
                  spl=float(success) * shortest / max(shortest, length))
    np.savez_compressed(out / "trajectory.npz", xy=xy,
                        actions=np.asarray(actions), rewards=np.asarray(rewards))
    (out / "result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2))
finally:
    env.close()
```

执行：

```bash
python navigation_trial.py 0 random
python navigation_trial.py 0 goal
```

代码沿用旧 Gym 接口：`reset()` 返回观测字典，`step()` 返回四项 `(state, reward, done, info)`。不要直接套用 Gymnasium 的五返回值示例。无窗口运行时，将代码中的 `mode="gui_interactive"` 改为 `mode="headless"`，仍会保存首末 RGB 图像。

`goal` 通过目标方位角调整方向，仅当方位角误差小于 0.25 rad 时前进，**没有障碍规划功能**。它可能被家具阻挡；机器人卡住或回合失败是应记录和分析的结果。此控制器使用模拟器提供的目标相对位置，不能据此宣称完成了纯视觉导航或策略训练。

### 3.3 比较多次运行

分别以种子 `1`、`2` 重复两种策略，共获得六个结果目录。相同种子用于减少随机差异，仍须核对 `start` 和 `target` 是否一致；场景、对象布局或依赖不同的回合不能当作严格配对实验。已有目录会触发 `FileExistsError`，重新实验时更换种子或先归档旧结果。

查看首末图像和轨迹，分析是否接近目标、是否持续碰撞、是否被家具阻挡。可在保留随机基线的基础上，增加利用深度或激光避障的策略，并使用相同场景和终止条件再次比较。

## 四、实验结果

每个回合应生成 `config.json`、`start.png`、`end.png`、`trajectory.npz` 和 `result.json`。`trajectory.npz` 的 `xy` 包含初始位置和每步执行后的位置，行数应比 `actions` 多一。

| 记录项 | 判读方式 |
| --- | --- |
| 环境验证 | 官方示例可运行，观测存在且随动作更新；保存依赖和两个源码提交记录 |
| `done` | 回合是否终止；终止不等于成功 |
| `success` | 采用上游任务判据；到达目标时为 `true`，不能用程序无报错代替 |
| `final_distance_m` | 最终平面欧氏距离；到达判据为小于 0.36 m |
| `collision_steps` | 有有效碰撞的仿真步数，不是碰撞对象数；该任务主动忽略额外 YCB 对象的碰撞 |
| `path_length_m`、`spl` | 由保存的完整轨迹计算路径长度 P，以初始最短路径 L 计算 `S * L / max(L, P)`，其中 S 为成功标记 |

按策略汇总三次运行的成功率、平均 SPL、平均步数及平均碰撞步数。随机策略全部失败也应如实保留，不能反复更换种子只选成功回合。若安装或渲染阶段未通过，提交环境信息、失败命令和完整日志，结果状态填写“未进入导航仿真”，不填写成功率。

实验报告至少包含一组首末图像、结果表和失败分析。说明反馈控制相比随机动作改善了什么，以及为何仅朝向目标仍不能解决障碍绕行。

## 五、排错建议与注意事项

| 现象 | 检查与处理 |
| --- | --- |
| CMake、编译器或 CUDA 编译失败 | 确认 Python 3.8 环境已激活，CMake 来自 Conda；检查 `nvcc`、Windows C++/SDK 或 Linux EGL 开发库。若使用了 CMake 4，恢复本页的 3.x 范围后重新构建 |
| `No module named behavior_eval/igibson` 或来源不符 | 用 `python -m pip show eai-eval igibson` 核对当前环境，确认使用指定源码安装并执行 `python -m pip check` |
| 资产缺失、`VERSION` 报错或解密失败 | 核对打印出的资产、场景和密钥路径；检查下载是否完整、版本是否匹配以及密钥授权，不要仅新建空目录绕过检查 |
| 缺少 Turtlebot 或 YCB 模型 | 检查通用 `assets`，不能只下载场景；仅有静态 `Rs` 演示场景不能运行本实验的 `Rs_int` |
| GUI 黑屏、EGL/OpenGL 或渲染器加载失败 | 先运行官方短示例并保存日志；核对 GPU 驱动和桌面/远程渲染配置。`headless` 只去掉窗口，不能弥补缺少渲染支持 |
| `reset` 失败或无法采样有效位置 | 核对场景、可通行地图和完整资产；检查起终点采样警告，不能在未加载场景时直接修改坐标继续 |
| 动作维度或返回值数量不符 | 核对 iGibson 提交、`turtlebot_interactive_nav.yaml` 和实际导入路径，恢复本页的两维动作、四项返回值接口 |
| `goal` 碰墙、原地转向或超时 | 先对照目标方位、轨迹与观测定位问题，再增加避障或路径规划；这不是重新安装环境的依据 |

课程导航目录尚未提供完整运行入口，本页练习代码需按第三节自行保存。接口依据、检查范围和未完成的 GPU 验证见[导航实验核验记录](../assets/ch4-navigation/verification.md)。
