# 第 5 章：ACT 模仿学习

对应教材 **5.7.1 模仿学习实验**：先完成方块传递的 ACT 仿真，再在 cobot-magic 平台上采集示教、训练和推理。

## 一、实验目标

用相机图像和关节状态训练 ACT，让双臂完成方块传递。仿真主线包含 50 条示教、2000 轮训练和 50 回合评估；有 cobot-magic 设备时，再完成实机采集、训练与推理。

先选择本次要做的内容：

| 内容 | 从哪里开始 | 需要什么 |
|---|---|---|
| 完整仿真 | 2.1 → 3.1 → 3.2 | Linux、NVIDIA GPU、渲染环境与数据空间 |
| 查看已有 50 回合结果 | [4.1 核对已有基线](#41) | 手册仓库和 Python；无需重新训练或评估 |
| 用已有模型预测一次动作 | [4.2 单输入 CPU 对照](#42-cpu) | 独立 CPU 环境及配套模型、参考输入；只验证一个输入 |
| 实机实验 | 2.2 → 3.3 → 3.4 | cobot-magic 实验台和设备负责人 |

缺少实机时完成仿真，报告注明实机未执行。单输入预测通过不能代替方块传递任务的评估。

## 二、实验环境配置

### 2.1 ACT 仿真环境

以下命令在 **Linux Bash** 中执行。准备 Conda、NVIDIA GPU、驱动和 OpenGL 渲染环境；此训练入口必须使用 CUDA。50 条未压缩示教的 RGB 图像约占 **18.4 GB**，另留依赖、checkpoint 和视频空间。

仅做两条示教采集时，可参考 [CPU 采集步骤](../assets/ch5-imitation/verification.md#cpu)；没有 GPU 时不要继续执行本节训练命令。

安装下列固定 ACT 提交和 CUDA 11.8 版 PyTorch。驱动不支持该运行时时，先请教师确认兼容版本。

```bash
mkdir -p "$HOME/eai-lab"
cd "$HOME/eai-lab"
git clone https://github.com/tonyzhaozh/act.git
cd act
git checkout 742c753c0d4a5d87076c8f69e5628c79a8cc5488

conda create -n act-sim python=3.8.10 -y
conda activate act-sim
python -m pip install torch==2.0.1 torchvision==0.15.2 \
  --index-url https://download.pytorch.org/whl/cu118
python -m pip install "numpy<2" pyquaternion pyyaml rospkg pexpect \
  mujoco==2.3.7 dm_control==1.0.14 opencv-python matplotlib \
  einops packaging h5py ipython tqdm
cd detr
python -m pip install -e .
cd ..
python -m pip check
python -c "import torch, torchvision, mujoco, dm_control; print(torch.__version__, torchvision.__version__, mujoco.__version__); print('CUDA:', torch.cuda.is_available())"
python -m pip freeze > environment-sim.txt
```

检查导入无错误且输出 `CUDA: True`，保留 `environment-sim.txt`。不要再安装仓库的 `conda_env.yaml`，其中 Python/MuJoCo 版本与本节不同。首次构造模型会使用 ResNet-18 预训练权重，提前准备网络或实验室缓存。

后续仿真命令均从 `$HOME/eai-lab/act` 执行。新开终端时先运行：

```bash
conda activate act-sim
cd "$HOME/eai-lab/act"
```

### 2.2 cobot-magic 实机环境

准备两个主臂、两个从臂、三个 Orbbec Dabai 相机，以及 Ubuntu 20.04 / ROS1 Noetic 工控机。使用实验台已联调的系统和 Python 环境；启动前确认 CAN 映射、相机序列号、急停和运动范围。

下载实机代码，注意目录名是 **`aloha-devel`**：

```bash
cd "$HOME/eai-lab"
git clone https://github.com/sheji105/cobot_magic.git
cd cobot_magic
git checkout 70c11788f1a750c3e27453a2472fdd6bea59c675
```

每个实机终端先设置根目录；运行 Python 的终端另激活实验台的 `cobot-act` 环境：

```bash
export COBOT_ROOT="$HOME/eai-lab/cobot_magic"
source /opt/ros/noetic/setup.bash
```

实验台尚无 Python 环境时，单独创建 `cobot-act`，避免覆盖仿真环境中的 `detr`：

```bash
conda create -n cobot-act python=3.8 -y
conda activate cobot-act
cd "$COBOT_ROOT/aloha-devel"
python -m pip install torch==2.0.1 torchvision==0.15.2 \
  --index-url https://download.pytorch.org/whl/cu118
python -m pip install -r requirements.txt -r ../collect_data/requirements.txt
cd act/detr
python -m pip install -e .
cd ../..
python -m pip check
python -c "import torch, rospy; from cv_bridge import CvBridge; print('CUDA:', torch.cuda.is_available())"
python act/train.py --help
python act/inference.py --help
python -m pip freeze > environment-real.txt
```

必须完成 PyTorch 和两个 requirements 文件的安装，并在 `aloha-devel` 运行 Python 命令。导入检查及两个 `--help` 均通过后才能继续。若缺少 `cv_bridge`、`robomimic` 或 `diffusers`，保存完整错误并向教师领取该实验台的环境配置；仓库没有完整的 ROS/Python 依赖锁定文件。

在未激活 Conda 的 ROS 终端编译：

```bash
cd "$COBOT_ROOT/remote_control"
bash tools/build.sh
cd "$COBOT_ROOT/camera_ws"
catkin_make
```

两个工作空间编译成功后，请设备负责人将 `remote_control/tools/can.sh` 的设备映射和 `camera_ws/src/ros_astra_camera/launch/multi_camera.launch` 的相机序列号改为本机配置。

## 三、实验过程

### 3.1 仿真数据采集与检查

在 ACT 根目录编辑 `constants.py`，把 `DATA_DIR` 改为：

```python
DATA_DIR = str(pathlib.Path(__file__).resolve().parent / 'data')
```

保持 `sim_transfer_cube_scripted` 的配置为 `num_episodes=50`、`episode_len=400`、`camera_names=['top']`。训练从这里读取数据位置，没有 `--dataset_dir` 参数；实际数据目录必须是 `data/sim_transfer_cube_scripted`。

先在独立目录采集 2 条检查渲染和保存：

```bash
python record_sim_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --dataset_dir "$PWD/data/sim_transfer_cube_check" \
  --num_episodes 2 --onscreen_render
python visualize_episodes.py \
  --dataset_dir "$PWD/data/sim_transfer_cube_check" --episode_idx 0
```

观察双臂是否完成方块传递，记录终端最后的 `Success: 成功条数 / 总条数`。它统计关节指令回放的结果；失败回合也会保存 HDF5。打开数据目录中的 `episode_0_video.mp4` 和 `episode_0_qpos.png`，检查画面、夹爪动作和关节曲线。录制窗口使用 `angle` 视角，保存和训练使用 `top`。

检查通过后，在新的正式数据目录录制 50 条，并保存完整日志：

```bash
set -o pipefail
python record_sim_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --dataset_dir "$PWD/data/sim_transfer_cube_scripted" \
  --num_episodes 50 2>&1 | tee record-sim.log
python visualize_episodes.py \
  --dataset_dir "$PWD/data/sim_transfer_cube_scripted" --episode_idx 1
```

正式目录应含 `episode_0.hdf5` 至 `episode_49.hdf5`。同目录重新录制会从 0 开始覆盖，重试时另建目录并同步任务配置。训练前检查数量和关键字段：

```bash
python - <<'PY'
from pathlib import Path
import h5py
from constants import SIM_TASK_CONFIGS
c = SIM_TASK_CONFIGS['sim_transfer_cube_scripted']
for i in range(c['num_episodes']):
    p = Path(c['dataset_dir']) / f'episode_{i}.hdf5'
    with h5py.File(p, 'r') as f:
        assert bool(f.attrs['sim']), p
        for key in ['observations/qpos', 'observations/qvel', 'action']:
            assert f[key].shape == (400, 14), (p, key, f[key].shape)
        assert f['observations/images/top'].shape == (400, 480, 640, 3), p
print('50 episodes: shapes OK')
PY
```

检查通过后，抽查开头、中间和末尾的回合视频。记录失败示教编号，以及重新采集或筛选了哪些数据。

### 3.2 ACT 训练与仿真评估

先用 2 个 epoch 检查数据加载、GPU、损失和 checkpoint 写出。输出目录已存在时，换一个新名称再运行：

```bash
CKPT_DIR="$PWD/ckpt/smoke"
if [ -e "$CKPT_DIR" ]; then
  echo "输出目录已存在，请更换 CKPT_DIR。"
else
  python imitate_episodes.py \
    --task_name sim_transfer_cube_scripted --ckpt_dir "$CKPT_DIR" \
    --policy_class ACT --kl_weight 10 --chunk_size 100 --hidden_dim 512 \
    --batch_size 8 --dim_feedforward 3200 --num_epochs 2 --seed 0 --lr 1e-5
fi
```

确认 train/validation loss 为有限数值且 checkpoint 已写出，再运行 2000 epoch 基线训练。以下数组同时用于后面的评估；换终端后需重新定义。

```bash
CKPT_DIR="$PWD/ckpt/transfer_seed0"
ACT_ARGS=(
  --task_name sim_transfer_cube_scripted --ckpt_dir "$CKPT_DIR"
  --policy_class ACT --kl_weight 10 --chunk_size 100 --hidden_dim 512
  --batch_size 8 --dim_feedforward 3200 --num_epochs 2000 --seed 0 --lr 1e-5
)
set -o pipefail
if [ -e "$CKPT_DIR" ]; then
  echo "输出目录已存在，请更换 CKPT_DIR。"
else
  mkdir -p "$CKPT_DIR"
  python imitate_episodes.py "${ACT_ARGS[@]}" 2>&1 | tee "$CKPT_DIR/train-sim.log"
fi
```

训练结束后，检查 `ckpt/transfer_seed0` 中有 `policy_best.ckpt`、`policy_last.ckpt`、`dataset_stats.pkl` 和 `train_val_{kl,l1,loss}_seed_0.png`。

**下一条命令会执行 50 个仿真回合。** 仅查看已有结果时跳到 4.1；评估本次新训练的模型时，在同一终端执行：

```bash
if [ -e "$CKPT_DIR/eval-sim.log" ] || [ -e "$CKPT_DIR/result_policy_best.txt" ]; then
  echo "已有评估记录，请先查看或归档。"
else
  python imitate_episodes.py "${ACT_ARGS[@]}" --eval 2>&1 | tee "$CKPT_DIR/eval-sim.log"
fi
```

评估读取 **`policy_best.ckpt`** 及同目录的统计文件，输出 `result_policy_best.txt`、`video0.mp4` 至 `video49.mp4`。已有评估文件时先归档，避免覆盖。成功率按每个回合的最高奖励是否达到 4 计算。

奖励 4 表示当时左夹爪接触方块、方块未接触桌面。回合中短暂达到这一状态也会计为成功，因此还要检查视频末尾是否掉落，并在失败分析中记录。

若最佳轮次为 epoch 0，`policy_best.ckpt` 保存的是首次更新前的模型；`policy_last.ckpt` 保存最终更新结果。记录最佳轮次、数据集和命令；`--seed` 只设置训练种子。

打开汇总和至少一个成功、一个失败回合的视频；全成功时注明。按抓取、交接、夹持和放置阶段分析失败，报告填写本次实际成功数和总数。

选做：增加 `--temporal_agg` 比较动作抖动和成功率。该选项不会新建输出目录，先另存基线结果和视频。

### 3.3 实机启动与数据采集

由设备负责人按本机映射启用 CAN、配置相机，并清空机械臂运动区域。不要直接执行仓库原始 `can.sh`。用以下命令确认预期 CAN 接口均存在且带有 `UP` 标志；缺失时先处理，`roslaunch` 不会启用 CAN。

```bash
ip -details link show
```

确认后按终端分别运行以下命令，所有终端均需完成第二节的根目录与 ROS 初始化。

| 终端 | 工作目录与命令 | 检查内容 |
|---|---|---|
| ROS 主节点 | `roscore` | 只运行一个 ROS master |
| 相机 | `cd "$COBOT_ROOT/camera_ws"`；`source devel/setup.bash`；`roslaunch astra_camera multi_camera.launch` | 包名为 `astra_camera` |
| 四个机械臂终端 | 分别进入 `$COBOT_ROOT/remote_control/master1`、`master2`、`follow1`、`follow2`；执行 `source devel/setup.bash` 和 `roslaunch arm_control arx5v.launch` | 启动可能回初始位，由设备负责人逐臂确认 |
| 检查终端 | `rostopic list`，再运行 `rqt` | 图像、关节数据持续更新 |

按表逐项启动后，不再运行 `tools/start.sh` 或 `tools/start01.sh`，避免重复启动节点。

先核对以下对应关系，左右相机不能互换：

| 实际话题 | HDF5 相机键 | 视角 |
|---|---|---|
| `/camera_f/color/image_raw` | `cam_high` | 中间 |
| `/camera_l/color/image_raw` | `cam_left_wrist` | 左腕 |
| `/camera_r/color/image_raw` | `cam_right_wrist` | 右腕 |

还需持续收到 `/master/joint_left`、`/master/joint_right`、`/puppet/joint_left`、`/puppet/joint_right`。话题名称与本机不同，必须用采集脚本的对应 `--img_*_topic`、`--master_arm_*_topic`、`--puppet_arm_*_topic` 参数同步调整，推理也使用同一映射。

使用 RGB 基线：编辑 `collect_data/collect_data.py`，将 `--use_depth_image` 的 `default=True` 改为 `default=False`。不要传 `--use_depth_image False`，此版本会将非空字符串转换成真。训练和推理已默认关闭深度图。三路 RGB、每条 500 帧、50 条未压缩数据的图像约占 **69.1 GB**。

在采集终端激活 `cobot-act`，先录一条：

```bash
conda activate cobot-act
cd "$COBOT_ROOT/collect_data"
python collect_data.py \
  --dataset_dir "$COBOT_ROOT/data" --task_name transfer_cube \
  --max_timesteps 500 --episode_idx 0
python visualize_episodes.py \
  --dataset_dir "$COBOT_ROOT/data" --task_name transfer_cube --episode_idx 0
```

手动操作主臂完成传递，数据保存为 `data/transfer_cube/episode_0.hdf5`。可视化生成的视频、关节曲线和底盘曲线位于 `data/`。默认采集频率为 30 Hz，把 `visualize_episodes.py` 中的 `DT=0.02` 改为 `DT=1 / 30`，再检查播放速度。

确认图像方向、关节维度和动作都正常后，逐次把 `--episode_idx` 改为 1 至 49，采满 50 条；每条重新放置方块并记录成败，不要用循环代替人工准备。HDF5 应含三路上述图像键、`observations/qpos` 和 `action`，本配置形状分别为 `(500,480,640,3)` 与 `(500,14)`。同编号会覆盖已有文件。

### 3.4 实机训练与推理

编辑 `aloha-devel/act/train.py`，把 `TASK_CONFIGS` 中的 **`'num_episodes': 60` 改为 `50`**。保留相机顺序 `['cam_high', 'cam_left_wrist', 'cam_right_wrist']`，`--dataset` 路径末尾保留 `/`。

先把下面命令的 `--num_epochs` 改为 `2`，输出目录改为 `ckpt/real_smoke`。检查损失和 checkpoint 后，再用原参数训练 3000 轮；每次使用新的输出目录。

```bash
conda activate cobot-act
cd "$COBOT_ROOT/aloha-devel"
python act/train.py \
  --dataset "$COBOT_ROOT/data/" --task_name transfer_cube \
  --ckpt_dir "$COBOT_ROOT/ckpt/transfer_real_seed0" \
  --policy_class ACT --chunk_size 30 --hidden_dim 512 --dim_feedforward 3200 \
  --kl_weight 10 --batch_size 48 --num_epochs 3000 --seed 0
```

训练结束后应有 `policy_best.ckpt`、`policy_last.ckpt`、`dataset_stats.pkl` 和损失曲线。保存修改后的脚本、命令和环境清单；推理使用本次实机训练的权重与统计文件。

!!! danger "实机推理前检查"
    推理程序会发送关节指令，并且在 `input("please input:")` 之前已经执行一次初始位运动。必须在启动命令前确认急停可用、人员离开运动范围、初始姿态可达，且设备负责人在场。先停止两个主臂的遥操作发布，只保留从臂、相机和 ROS master，避免多个节点同时控制从臂。

在相同环境、相同相机映射下，从 `aloha-devel` 执行：

```bash
python act/inference.py \
  --ckpt_dir "$COBOT_ROOT/ckpt/transfer_real_seed0" \
  --ckpt_name policy_best.ckpt --ckpt_stats_name dataset_stats.pkl \
  --policy_class ACT --chunk_size 30 --hidden_dim 512 --dim_feedforward 3200 \
  --kl_weight 10 --max_publish_step 500
```

训练与推理保持模型结构、相机顺序、RGB/深度和底盘选项一致。每轮最多发布 500 步，**程序随后会继续下一轮**；单次观察结束后由操作人员停止进程。默认控制话题为 `/master/joint_left` 和 `/master/joint_right`，启动前确认本机从臂订阅这两个话题。

先在训练范围内的固定位置测试，再小范围改变方块位置；逐次记录成功、掉落、交接失败、停顿或异常运动。实机程序没有仿真式的自动任务成功判定，需事先约定成功标准并人工计数。

## 四、实验结果

### 4.1 核对已有基线

已有基线使用 50 条示教、2000 轮训练和 50 回合评估：**最高奖励达到 4 的回合为 37/50（74%），平均回报 490.26；末步奖励仍为 4 的回合为 34/50**。另 3 回合曾达到奖励 4，但末步已不满足，因此 74% 不是稳定夹持率。该记录使用 Windows CUDA 训练、Ubuntu CPU 评估，未验证实机或本页原 Linux CUDA 全流程。

从**手册仓库根目录**执行，只读取仓库内的[结果文件](../assets/ch5-imitation/act-evaluation-20261002.json)，无需 PyTorch、GPU 或示教数据：

```bash
python docs/assets/ch5-imitation/verify_act_evidence.py
```

输出应含 `"status": "VERIFIED_SUMMARY"`，汇总数值与上段一致。这只核对已保存记录。要核对逐步奖励和录像，请向教师领取 50 份轨迹与视频，按[文件核验步骤](../assets/ch5-imitation/verification.md#evidence-check-20261002)检查；大文件未随仓库发布。环境差异见[适配说明](../assets/ch5-imitation/adaptation-notes.md)。

![完整基线的 50 回合结果](../assets/ch5-imitation/act-evaluation-20261002.png)

按图比较第 0、1、2 回合：第 0 回合失败，第 1 回合曾成功后掉落，第 2 回合末步仍满足奖励条件；编号从 0 开始。领取录像后，定位各回合的抓取、交接或掉落时刻。

### 4.2 单输入 CPU 对照

先向教师领取[清单](../assets/ch5-imitation/cpu-reference-resources.json)中的文件和对应平台的 wheelhouse，再按[独立 CPU 环境说明](../assets/ch5-imitation/cpu-environment.md)安装依赖。Windows 单输入路线已有验证记录；Ubuntu 独立环境尚待验证。**资源未随仓库发布，缺文件时停在资源准备。** 不需要领取 50 条 HDF5 或全部录像。

将文件整理为以下结构。把训练报告的原 `result.json` 复制为 `training-result.json`，只改副本文件名，不改内容；权重必须是完整 2000 轮训练的 `policy_best.ckpt`。

```text
act-resources/
├── act-742c753c0d4a5d87076c8f69e5628c79a8cc5488.zip
├── policy_best.ckpt
├── dataset_stats.pkl
├── training-result.json
├── reference.npz
├── reference.json
└── torch-cache/hub/checkpoints/resnet18-f37072fd.pth
```

**Windows PowerShell：**从手册仓库根目录执行，替换三个路径。`ACT_PY` 指向检查通过的独立 venv；输出目录须尚不存在，且位于资源目录外。

```powershell
$ACT_PY = 'C:/绝对路径/act-cpu-reference-01/Scripts/python.exe'
$ACT_RESOURCES = 'D:/绝对路径/act-resources'
$ACT_OUTPUT = 'D:/绝对路径/act-results/cpu-reference-01'
if (Test-Path -LiteralPath $ACT_OUTPUT) { throw '请更换为新的输出目录' }
& $ACT_PY -I docs/assets/ch5-imitation/run_act_cpu_reference.py `
  --source-archive "$ACT_RESOURCES/act-742c753c0d4a5d87076c8f69e5628c79a8cc5488.zip" `
  --checkpoint "$ACT_RESOURCES/policy_best.ckpt" --stats "$ACT_RESOURCES/dataset_stats.pkl" `
  --torch-home "$ACT_RESOURCES/torch-cache" `
  --reference "$ACT_RESOURCES/reference.npz" --reference-report "$ACT_RESOURCES/reference.json" `
  --training-report "$ACT_RESOURCES/training-result.json" `
  --output $ACT_OUTPUT --threads 4 --timeout-seconds 180
```

**Ubuntu Bash：**完成独立环境安装与检查后，从手册仓库根目录执行。`ACT_PY` 填写该 venv 的 `bin/python` 绝对路径：

```bash
ACT_PY="/绝对路径/act-cpu-clean-01/bin/python"
ACT_RESOURCES="/绝对路径/act-resources"
ACT_OUTPUT="/绝对路径/act-results/cpu-reference-01"
"$ACT_PY" -I docs/assets/ch5-imitation/run_act_cpu_reference.py \
  --source-archive "$ACT_RESOURCES/act-742c753c0d4a5d87076c8f69e5628c79a8cc5488.zip" \
  --checkpoint "$ACT_RESOURCES/policy_best.ckpt" --stats "$ACT_RESOURCES/dataset_stats.pkl" \
  --torch-home "$ACT_RESOURCES/torch-cache" \
  --reference "$ACT_RESOURCES/reference.npz" --reference-report "$ACT_RESOURCES/reference.json" \
  --training-report "$ACT_RESOURCES/training-result.json" \
  --output "$ACT_OUTPUT" --threads 4 --timeout-seconds 180
```

脚本核对资源哈希，在新目录准备 CPU 源码副本，再预测一次动作；不联网，最多运行 180 秒。只检查文件时加 `--preflight-only`，之后运行推理需换新输出目录。

运行后打开输出目录中的 `result.json`：

| 字段 | 本步骤通过时的值 |
|---|---|
| `state` | `SINGLE_INPUT_VERIFIED` |
| `environment.independent_environment` | `true` |
| `forward_passes` / `rollouts_run` | `1` / `0` |

`comparison.json` 应显示动作块形状为 `(1,100,14)`、数值有限，且与 GPU 参考在 `rtol=atol=1e-4` 下相符。预测数组保存在 `cpu-reference-output.npz`。这表示一个输入的预测通过，未执行方块传递。失败时读取 `errors`、`stdout.log` 和 `stderr.log`，保留原目录后按第五节排错。

### 4.3 提交本次实验结果

按本次选择的路线提交材料；受阻时写明失败命令和日志位置，未运行的部分填写“未执行”。

| 项目 | 报告内容 |
|---|---|
| 环境与数据 | 源码提交、依赖清单、数据目录、50 条编号、相机配置、筛选或重录记录 |
| 数据检查 | HDF5 字段/形状、一条示教视频和关节曲线、示教回放成败 |
| 仿真基线 | 训练参数、损失曲线、checkpoint 名、50 次评估成功数/成功率、平均回报 |
| 失败分析 | 至少一例失败的具体阶段与对应视频；全成功时如实说明 |
| 对比实验 | 若运行时间集成等扩展，保存独立结果，说明只改变了哪些条件 |
| 仅核对记录 / 单输入 CPU | 核对输出，或完整 CPU 输出目录；注明没有新做任务评估 |
| 实机部分 | 设备配置、数据检查、训练结果、人工评估次数/成功数；无设备时写明卡在的步骤 |

报告中的成功率只填写本次任务评估结果。源码依据和历史失败保留在[验证记录](../assets/ch5-imitation/verification.md)。

## 五、排错建议与注意事项

| 现象 | 排查顺序 |
|---|---|
| 仿真训练找不到 HDF5 | 检查 `constants.py` 的 `DATA_DIR`、任务子目录和连续编号，不能给训练脚本增加不存在的 `--dataset_dir` |
| 找到文件却提示缺少相机键 | 对照任务的 `camera_names` 与 HDF5 键；仿真 `top` 和实机三相机配置不能混用 |
| MuJoCo/GLFW/EGL 报错 | 先确认本机渲染驱动与显示会话；取消 `--onscreen_render` 仍需离屏渲染，不会自动解决 OpenGL 问题 |
| CUDA 不可用或显存不足 | 检查驱动与 PyTorch 配对；显存不足可减小 batch size 并记录，完整训练和评估继续使用匹配的模型结构 |
| 数据录制一直等待 | 检查所有必需相机/关节话题及时间戳；RGB 基线确认深度开关确实关闭 |
| 实机训练寻找第 50 至 59 条或错误目录 | 检查 `num_episodes=50`、任务名和 `--dataset` 尾部 `/` |
| checkpoint 加载维度不符 | 核对两个仓库是否混用、chunk size、hidden dim、相机数、深度/底盘选项及配套统计文件 |
| CPU 提示文件缺失或哈希不符 | 对照 4.2 目录和资源清单，重新领取对应原件；不要混用短训练权重或修改来源报告 |
| CPU 为 `PREFLIGHT_ONLY`、`FAILED` 或 `TIMEOUT` | 预检未执行推理；其余情况先读 `result.json` 的 `errors` 和 `stderr.log`，修复后换新目录重试 |
| loss 下降但传递失败 | 回看示教质量、初始位置分布和失败阶段，再决定增加训练或改善数据；不以某个 loss 阈值判定成功 |

所有重新录制、重新训练和对比评估使用独立输出目录。实机训练数据、相机安装位置或归一化统计改变后，重新核对推理配置；保留上一组可追溯的结果。
