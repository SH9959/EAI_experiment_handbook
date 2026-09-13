# 第 5 章：ACT 模仿学习

> 对应教材：**5.7.1 模仿学习实验**，包含 ACT 仿真与 cobot-magic 实机两部分。

## 先理解 ACT 在做什么

ACT（Action Chunking with Transformers）的输入是**相机图像 + 机器人关节状态**，输出不是单个动作，而是一段连续动作 chunk。这样可以减轻行为克隆中单步误差不断累积的问题。

实验主线非常清楚：

```text
采集示教数据 → 可视化检查 → 训练 ACT → 仿真评估
                                  ↓
                           实机采集 → 训练 → 实机推理
```

# 一、ACT 仿真实验

## 1. 环境

教材使用 ACT 官方仓库：

```bash
git clone https://github.com/tonyzhaozh/act.git
cd act

conda create -n aloha python=3.8.10 -y
conda activate aloha

pip install torchvision torch pyquaternion pyyaml rospkg pexpect \
  mujoco==2.3.7 dm_control==1.0.14 opencv-python matplotlib \
  einops packaging h5py ipython

cd detr
pip install -e .
cd ..
```

## 2. 采集仿真数据

教材以 `sim_transfer_cube_scripted` 为任务，采集 50 条示教：

```bash
python3 record_sim_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --dataset_dir ./data \
  --num_episodes 50 \
  --onscreen_render
```

**成功判据：** 仿真窗口能看到 scripted policy 执行方块传递，并在 `dataset_dir` 中生成 episode 数据。

## 3. 先检查数据

```bash
python3 visualize_episodes.py \
  --dataset_dir ./data \
  --episode_idx 1
```

教材说明可视化后会生成机械臂状态曲线和相机视频，例如：

```text
episode_1_qpos.png
episode_1_video.mp4
```

如果数据本身有明显异常，不要直接开始训练。

## 4. 训练 ACT

```bash
python3 imitate_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --ckpt_dir ./ckpt \
  --policy_class ACT --kl_weight 10 \
  --chunk_size 100 --hidden_dim 512 \
  --batch_size 8 --dim_feedforward 3200 \
  --num_epochs 2000 \
  --seed 0 --lr 1e-5
```

训练过程中重点观察：

- `train_val_kl_seed_0.png`
- `train_val_l1_seed_0.png`
- `train_val_loss_seed_0.png`
- `dataset_stats.pkl`

## 5. 仿真评估

在相同配置后增加 `--eval`：

```bash
python3 imitate_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --ckpt_dir ./ckpt \
  --policy_class ACT --kl_weight 10 \
  --chunk_size 100 --hidden_dim 512 \
  --batch_size 8 --dim_feedforward 3200 \
  --num_epochs 2000 \
  --seed 0 --lr 1e-5 \
  --eval
```

**实验重点：** 不只看 loss，还要看 rollout 是否真正完成 transfer cube。

# 二、cobot-magic 实机实验

教材使用：

- cobot-magic 双臂平台；
- 两个主臂 + 两个从臂；
- 3 个 Orbbec Dabai 深度相机；
- Ubuntu 20.04；
- ROS1 Noetic。

## 1. 环境准备

```bash
git clone https://github.com/sheji105/cobot_magic.git
cd cobot_magic/aloha_devel

conda create -n aloha python=3.8 -y
conda activate aloha
pip install -r requirements.txt
```

ACT/DETR 模块按项目目录安装：

```bash
cd act/detr
pip install -e .
```

编译机械臂与相机 ROS 包：

```bash
cd cobot_magic/remote_control
./tools/build.sh

cd cobot_magic/camera_ws
catkin_make
```

## 2. 先测试机械臂与相机

CAN 映射和机械臂启动：

```bash
cd remote_control
./tools/can.sh

cd master1
source devel/setup.bash
roslaunch arm_control arx5v.launch
```

相机：

```bash
cd camera_ws
source devel/setup.bash
roslaunch ros_astra_camera multi_camera.launch
rqt
```

**成功判据：** 机械臂状态正常；`rqt` 中能看到 `camera_r`、`camera_l`、`camera_f` 三路相机数据。

## 3. 采集实机示教

```bash
# 终端 1
roscore

# 终端 2：主臂、从臂、相机
./tools/start.sh

# 终端 3：采集
cd collect_data
python collect_data.py \
  --max_timesteps 500 \
  --dataset_dir ./data \
  --episode_idx 0
```

教材同样以 50 条 `transfer_cube` 数据为示例。摆放位置可做小范围随机，但不要无约束乱放，否则会显著增加学习难度。

可视化一条数据：

```bash
cd collect_data
python visuallize_data.py \
  --dataset_dir ./data \
  --episode_idx 0
```

## 4. 训练

教材示例：

```bash
conda activate aloha
python act/train.py \
  --dataset /你的数据目录/ \
  --ckpt_dir ~/train_act/ \
  --batch_size 48 \
  --num_epochs 3000
```

## 5. 实机推理

推理时只启动从臂和相机，由模型输出替代主臂控制：

```bash
conda activate aloha

cd remote
./tools/start01.sh

python act/inference.py --ckpt_dir ~/train_act/
```

!!! danger "实机推理"
    第一次推理必须有人在机械臂旁监控，确保急停可用。先在固定、熟悉的方块位置测试，再小范围改变位置观察泛化，不要直接把未验证 checkpoint 用在复杂场景。

!!! note "课程代码状态"
    当前 `SH9959/EAI_project` 仓库没有收录第 5 章 ACT/cobot-magic 工程，因此本页使用教材明确给出的两个官方仓库路径。
