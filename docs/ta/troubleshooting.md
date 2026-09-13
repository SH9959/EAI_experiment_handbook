# 助教：常见问题排查

## 先判断问题属于哪一层

| 现象 | 优先检查 |
|---|---|
| `ModuleNotFoundError` / 编译失败 | 环境层：Conda、Python、CUDA、依赖 |
| 图像黑屏 / 深度为空 / 音频读不到 | 输入层：相机、麦克风、ROS topic、路径 |
| API 返回错误 / 模型不输出 | 模型层：Key、网络、checkpoint、显存 |
| 模型输出正常但任务失败 | 规划/执行层：动作合法性、坐标系、仿真反馈、机器人约束 |

## SenseVoice

教材特别提醒：

- `funasr` 版本需要 `>= 1.1.2`；
- `torchaudio` 版本过旧可能报错；
- 默认 `demo1.py` 使用 `device="cuda:0"`，没有可用 CUDA 时要根据实验机器调整。

## AnyGrasp

### MinkowskiEngine 编译失败

先检查：

```bash
nvcc -V
python -c "import torch; print(torch.__version__, torch.version.cuda)"
```

CUDA 编译器、PyTorch CUDA 版本和 SDK Python 版本要匹配。教材示例为 Python 3.9、CUDA 11.8、PyTorch 2.4。

### 抓取候选看起来正确，但机器人姿态异常

这通常不是检测问题，而是**坐标系变换或工具坐标系约定**问题。先在 RViz / Open3D 中验证 `camera → robot base → gripper` 的变换，不要直接让实机执行。

## ALFRED

教材提到若评测出现 `stuck in resetting env`，应查 ALFRED 官方 Issue；这类问题通常发生在仿真环境初始化，而不是模型前向本身。

## AI2THOR

### 模型输出了不存在的动作

课程 demo 会用 `action.json` 中的技能集合做合法性检查。先检查模型输出格式是否满足：

```text
Action-Object
```

再判断动作名称是否在技能列表中。

### 模型提前输出 `done`

保留当前图像、历史动作和环境反馈，重点检查 Prompt 是否让模型误判任务已完成。

### `Agent hand has something in it already`

这是教材示例中的典型执行失败：机器人手里已有物体，又生成了新的 `PickupObject`。解决方向应是让规划器利用执行历史，而不是修改仿真器绕过约束。

## VirtualHome

课程示例中 `YOUR_FILE_NAME` 和视频输出目录都是本机路径占位符，必须修改。教材还指出 Windows 安装时可能遇到旧版 `setup.py` 依赖问题，可按教材给出的 `find_packages(where=".")` 方式处理，并参考官方 Issue。

## 方块重排 / 汉诺塔

教材明确列出的实机问题包括：

- 逆解进入关节限位；
- 机械臂碰撞桌面或其他物体；
- 方块从夹爪中滑落。

处理顺序：先停止执行 → 检查姿态/夹爪/摆放 → 再重新规划。不要通过提高速度“冲过去”。

## iGibson

安装阶段优先检查 GPU 驱动、CUDA、CMake 和资产完整性。仿真器无法打开时先不要调导航算法。

## ACT / cobot-magic

### 数据能采集但训练很差

先用可视化脚本检查数据本身，包括相机视角、关节轨迹和任务是否完整。教材强调方块位置只做小范围随机，否则会显著增加学习难度。

### 实机相机不全

用 `rqt` 查看 `camera_r`、`camera_l`、`camera_f` 三路话题；如果缺一路，先处理 USB/ROS 驱动，不要继续采集数据。
