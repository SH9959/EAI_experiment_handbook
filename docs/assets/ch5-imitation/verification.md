# ACT 模仿学习：修订与验证记录

更新日期：2026-10-01。**仿真示教采集与回放成功 2/2，学生亲自复测新增成功 1/1；随后完成原 ACT 模型的两次 GPU 参数更新及检查点保存、回读检查。** 尚未运行原训练命令入口、50 条示教的完整基线训练、策略闭环评估或实机实验。

## 仿真示教验证

采集阶段由 Codex 在 Ubuntu 22.04 虚拟机中执行：4 vCPU、4 GB 内存、约 4 GB 交换空间；Python **3.10.12**、torch **2.0.1+cpu**、MuJoCo **2.3.7**、dm_control **1.0.14**、NumPy **1.26.4**。使用 OSMesa 软件渲染；该阶段未下载预训练权重，后续 GPU 检查另见下文。

ACT 固定提交为 `742c753c0d4a5d87076c8f69e5628c79a8cc5488`。原始 `record_sim_episodes.py` 分两次执行，每次采集一条，输出到不同目录；未改动上游源码，48 个文件与固定提交逐一核对一致。

| 示教 | 末端空间策略 | 关节回放 | 采集耗时 |
|---|---|---|---|
| A | Successful，回报 619 | Successful，回报 646；`Success: 1 / 1` | 129.94 秒 |
| B | Successful，回报 621 | Successful，回报 641；`Success: 1 / 1` | 126.42 秒 |

- 两份 HDF5 各为 **368,740,832 字节**；`sim=True`，动作、关节位置及速度均为 `(400,14)` 且数值有限，`top` 图像为 `(400,480,640,3)`、`uint8`。
- 原可视化脚本生成两段视频及关节曲线。视频均可完整解码 **400 帧、640×480、50 fps**；首末帧可见双臂和方块，末帧方块位于左侧夹爪。
- 两次采集峰值常驻内存约为 1.95 GB 和 2.02 GB。采集、可视化及数据检查均正常退出。
- 初次单帧渲染检查在退出时出现 dm_control 资源释放警告；后续两次完整采集和可视化未出现该警告。

示教回放执行的是脚本产生的关节轨迹，不能据此报告 ACT 学习策略的成功率。

### 学生本机复测（2026-10-01）

学生通过 Ubuntu 桌面实验菜单选择“ACT 示教采集与回放”，在上述环境中启动原始采集、可视化和文件检查脚本。新增输出单独保存，没有覆盖前两条示教。

截图中的 `Successful, episode_return=618` 对应末端空间示教；取回的完整日志随后记录关节回放 `Successful, episode_return=643`，最后为 `Success: 1 / 1`。HDF5、视频和关节曲线均已生成。本次由学生亲自启动，动作由原始示教脚本自动执行，属于采集与回放复测；未运行 ACT 模型训练或策略评估。原始日志和文件保存在仓库外。

独立检查本轮文件通过：HDF5 为 368,740,832 字节，400 步关节数据数值有限，图像尺寸与类型正确；视频完整解码 400 帧、640×480、50 fps，已查看末帧方块位于左侧夹爪。48 个上游源文件仍与固定提交一致，检查器退出码为 0。

### CPU 采集复测

此入口只复测示教采集与视频，适用于 Ubuntu 22.04 / Python 3.10。训练继续使用[正文的 GPU 环境](../../student/ch5-imitation.md#21-act)。软件渲染配置依据 [dm_control 官方说明](https://github.com/google-deepmind/dm_control#rendering)。

在新目录获取固定源码并创建独立环境；已有 `act-cpu` 目录时，先进入该目录核对提交，不重复克隆。

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv libosmesa6 libgl1-mesa-glx
mkdir -p "$HOME/eai-lab"
cd "$HOME/eai-lab"
git clone https://github.com/tonyzhaozh/act.git act-cpu
cd act-cpu
git checkout 742c753c0d4a5d87076c8f69e5628c79a8cc5488
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pip==24.3.1
python -m pip install torch==2.0.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install numpy==1.26.4 mujoco==2.3.7 dm-control==1.0.14 \
  h5py==3.11.0 matplotlib==3.8.4 pyquaternion==0.9.9 ipython==8.26.0 \
  opencv-python-headless==4.10.0.84 scipy==1.11.4 PyOpenGL==3.1.7 \
  glfw==2.7.0 protobuf==4.25.3
python -m pip check
python -m pip freeze > environment-cpu.txt
```

在 ACT 根目录执行以下命令。每条示教单独启动进程并创建新目录，保留 400 步及原始图像尺寸；不需要修改 `constants.py`。不加 `--onscreen_render`，图像由 OSMesa 离屏渲染。

```bash
export MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa MPLBACKEND=Agg
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
set -euo pipefail
mkdir -p data
for episode in 1 2; do
  output=$(mktemp -d "$PWD/data/cpu-check-${episode}-XXXXXX")
  python -u record_sim_episodes.py --task_name sim_transfer_cube_scripted \
    --dataset_dir "$output" --num_episodes 1 2>&1 | tee "$output/record.log"
  python visualize_episodes.py --dataset_dir "$output" --episode_idx 0
  python - "$output" <<'PY'
import sys
from pathlib import Path
import cv2
import h5py
import numpy as np

directory = Path(sys.argv[1])
with h5py.File(directory / 'episode_0.hdf5', 'r') as data:
    assert bool(data.attrs['sim'])
    for key in ('action', 'observations/qpos', 'observations/qvel'):
        values = data[key][:]
        assert values.shape == (400, 14) and np.isfinite(values).all(), key
    images = data['observations/images/top']
    assert images.shape == (400, 480, 640, 3) and images.dtype == np.uint8
video = cv2.VideoCapture(str(directory / 'episode_0_video.mp4'))
assert video.isOpened()
assert abs(video.get(cv2.CAP_PROP_FPS) - 50) < 0.1
frames = 0
while True:
    ok, frame = video.read()
    if not ok:
        break
    assert frame.shape == (480, 640, 3)
    frames += 1
video.release()
assert frames == 400, frames
print('HDF5 and video: OK', directory)
PY
done
```

每个输出目录应包含 HDF5、`record.log`、视频和关节曲线。核对日志末尾的 `Success: 1 / 1`，再观看视频确认方块传递。失败回合也会保存文件，须如实保留失败记录。

## GPU 计算检查（2026-10-01）

经用户授权，下载 [PyTorch 官方 ResNet18 权重](https://download.pytorch.org/models/resnet18-f37072fd.pth)（46,830,571 字节，SHA-256 前缀 `f37072fd`），用于原 ACT 的视觉骨干网络。检查在 Windows 独立 venv 中完成，复用已有 CUDA PyTorch；环境为 Python **3.12.12**、torch **2.7.1+cu118**、torchvision **0.22.1+cu118**、NumPy **1.26.4**、h5py **3.11.0**、IPython **8.26.0**，GPU 为 RTX 4060 Laptop。

直接调用上述固定提交的 `ACTPolicy` 和 `utils.load_data`。输入是采集阶段的 A、B 两条 400 步示教，按原加载器分为训练 1 条、验证 1 条，batch size 为 1。使用 `top` 相机原始图像、100 步动作块、hidden dimension 512、feedforward dimension 3200、编码器 4 层、解码器 7 层、8 个注意力头、KL 权重 10；模型及骨干学习率均为 `1e-5`，随机种子为 0。

| 检查 | 实际结果 |
|---|---|
| 源码与预训练权重 | 运行前后 48 个上游文件一致；模型初始卷积权重与下载的 ResNet18 权重一致 |
| 前向、反向与更新 | 两次损失分别为 71.1530、67.0076；各有 261 个梯度张量，数值有限，总梯度范数非零；动作输出层参数最大变化约 `2.00e-5` |
| 检查点 | 保存 `policy_after_two_updates.ckpt`（336,095,885 字节）及配套 `dataset_stats.pkl`；新建模型严格加载检查点后，同一输入的输出最大差值为 0 |
| 输出与资源 | 动作输出尺寸为 `(1,100,14)`；PyTorch 峰值显存分配约 1.67 GB；进程退出码为 0 |

这次检查确认了真实数据加载、GPU 梯度更新和检查点读写。仅两次更新不能说明策略已学会方块传递，损失变化也不作为收敛结论。检查没有启动 `imitate_episodes.py` 或仿真闭环，没有生成 50 次策略评估结果。该 Windows Python 3.12 环境未配置 MuJoCo 2.3.7；原命令入口的完整依赖仍需另行验证。报告、日志、数据和模型文件保存在仓库外。

## 静态审阅记录

以下保留 2026-10-01 实际运行前的文档与源码检查。该阶段未安装实验依赖或采集数据；上方的仿真与 GPU 检查为随后新增的运行证据。

## 来源

- 教材《具身智能导论-v2.0.pdf》第 5.7.1 节，印刷页 189—201（PDF 第 207—219 页）。本轮读取新文件的文本提取，核对仿真、实机两条流程及 50 条示教、2000/3000 epoch 等基线设置；未对教材图表作本轮目视验收。
- ACT：`tonyzhaozh/act@742c753c0d4a5d87076c8f69e5628c79a8cc5488`。核对 [README](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/README.md)、[constants.py](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/constants.py)、[录制入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/record_sim_episodes.py)、[可视化入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/visualize_episodes.py)、[训练评估入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/imitate_episodes.py)、数据加载、backbone、DETR 参数和 `conda_env.yaml`。
- cobot-magic：`sheji105/cobot_magic@70c11788f1a750c3e27453a2472fdd6bea59c675`，为教材指定仓库。核对 [采集入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/collect_data/collect_data.py)、[可视化入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/collect_data/visualize_episodes.py)、[训练入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/aloha-devel/act/train.py)、[推理入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/aloha-devel/act/inference.py)、两份 requirements、数据加载、模型导入链、ROS 包名、相机 launch 与机械臂启动脚本。
- [PyTorch 官方历史安装表](https://pytorch.org/get-started/previous-versions/#v201)给出 torch 2.0.1 / torchvision 0.15.2 的 CUDA 11.8 配对。正文用它补足教材未固定的 torch/torchvision 配对，不代表已完成 ACT/ROS 全栈兼容性验证。

静态审阅阶段只读获取两仓库的提交信息、文件树和少量文本源码，保存在手册仓库外的本地审阅目录；该阶段未下载数据集或模型权重。固定源码提交后，仍需按本机驱动、ROS 与 Python 检查依赖。

## 关键修订

| 问题 | 正文处理与源码依据 |
|---|---|
| 仿真录制目录与训练目录脱节 | 明确修改 `constants.py` 的 `DATA_DIR`；训练读任务配置，不接收 `--dataset_dir` |
| 仿真数据存在被误认为示教成功 | 源码失败回合也保存；要求保存回放成功统计并抽查视频 |
| 相机视角混淆 | 录制显示为 `angle`，基线保存/训练为 `top`；实机明确三话题到三 HDF5 键的顺序 |
| 训练与评估参数或产物不明确 | 用 Bash 数组复用配置；明确 `policy_best.ckpt`、配套 stats、50 次 rollout 和结果文件 |
| 实机路径与现行源码不符 | 修正为 `aloha-devel`、`collect_data/visualize_episodes.py`、ROS 包 `astra_camera` |
| 实机数据目录和数量不匹配 | 采集/可视化按 `dataset_dir/task_name`；训练字符串拼接要求根目录尾斜线，源码硬编码 60 改为教材 50 |
| 深度布尔开关存在歧义 | `type=bool` 下命令行 `False` 仍为真；RGB 基线要求只改采集默认值为 False，与训练/推理默认一致 |
| 实机视频时间比例不一致 | 采集默认 30 Hz，可视化 `DT=0.02`；注明改为 `1/30` |
| 不同终端与启动脚本相互叠加 | 明确绝对根目录、环境、逐终端启动；不混用自行启动 ROS master 的脚本 |
| 推理输入提示被误当作启动前暂停 | 说明 input 前已有初始位运动；500 步仅限制单轮，外层继续循环 |
| 依赖与实际验证边界不清 | 保留教材仿真版本、分离两个 DETR 环境；给出导入/帮助检查及 ROS/Python 环境未配齐时的具体停止点 |

正文中修改 `constants.py`、实机采集开关、可视化 DT 和训练条数的指示，均针对学生克隆的实验仓库。本轮只编辑手册页面与本记录，没有修改外部实验工程。

## 文档静态检查

执行环境为 Windows PowerShell，使用 Codex 附带 Python **3.12.14**。语法检查不等于教材 Python 3.8 及 GPU/ROS 运行验证。

| 检查 | 结果与范围 |
|---|---|
| 正文结构 | 恰好 5 个指定 H2；6 个 H3 按 2.1—2.2、3.1—3.4 编号；16 个代码块 |
| Python 示例 | 2 段以 `ast.parse(..., feature_version=(3,8))` 检查通过；包括 HDF5 检查脚本，仅解析，未运行数据检查 |
| 脚本参数 | 从固定源码 AST 提取 argparse 声明，对正文 13 处脚本调用/帮助入口检查通过；未导入这些脚本或其模型依赖 |
| Bash 语法 | 对 15 个 Bash 代码块逐段执行 Git Bash 的 `bash -n`，均通过；没有执行块内命令 |
| 来源完整性 | 缓存的 65 个上游文本文件逐一计算 Git blob SHA-1，与固定提交的文件树匹配 |
| Markdown | 两文件本地相对链接、行尾空白和替换字符检查通过；正文转 HTML 后确有 5 个 H2、16 个代码块和实机警示框，未做浏览器目视验收 |
| 数据空间估算 | 仿真 `50×400×480×640×3 = 18,432,000,000` 字节；实机 RGB `50×500×3×480×640×3 = 69,120,000,000` 字节，仅计算像素，不是实测占用 |
| Git 空白检查 | `git diff --check -- docs/student/ch5-imitation.md` 通过；LF/CRLF 提示不属于检查失败 |

本轮不沿用旧测试记录作为新证据。全站构建及其他实验的检查由本次整体复核另行记录。

交叉审阅后统一 H3 编号，区分仓库附带的 `robomimic` 与 requirements 依赖 `diffusers`，补充由设备负责人启用 CAN、用 `ip -details link show` 核对接口 `UP` 标志的步骤。上述语法、结构与本地链接检查已对修订后的正文重新执行；没有实际运行 CAN 检查或启动设备。

## 尚需真实验证

1. 在同时支持 CUDA 与 MuJoCo 2.3.7 的 Python 环境运行原 `imitate_episodes.py` 入口。现已通过原模型和数据加载器的两次 GPU 更新检查，但现用 Python 3.12 没有 MuJoCo 2.3.7 的对应预编译包，尚未验证原入口及仿真依赖。
2. 采集 50 条、运行短训练流程，再训练完整基线并评估 50 次；保存真实成功数、平均回报和失败视频。
3. 实机需实验台提供可用 ROS/Python 环境。上游 requirements 未锁定全部传递依赖，`cv_bridge` 与 Conda 的兼容性、`robomimic`/`diffusers` 的导入链尚未在该主机验证。
4. 完成 CAN/相机序列号配置、三相机与四臂话题核对后，再采集、训练和在设备负责人现场监督下推理。

没有实机、依赖导入失败或图像/关节话题不完整时，应按正文记录卡点；不能将静态参数检查、短流程检查或教材参考图写成任务成功。
