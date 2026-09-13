# 第 3 章：AnyGrasp 抓取

> 对应教材：**3.4.4 抓取实验**。教材依次安排 AnyGrasp 环境、PyBullet 仿真抓取和 Dobot CR5 实机抓取。

## 先理解整条流程

```text
RGB + Depth
    ↓
RGB-D 反投影得到点云
    ↓
AnyGrasp 预测相机坐标系抓取位姿
    ↓
坐标系转换：Camera → World / Robot Base
    ↓
逆运动学 IK
    ↓
靠近 → 闭合夹爪 → 抬升
```

## 1. AnyGrasp 环境

教材使用 **Python 3.9 + CUDA 11.8 + PyTorch 2.4** 作为配置示例，并使用 AnyGrasp SDK detection 模式。

```bash
conda create -n anygrasp python=3.9 -y
conda activate anygrasp
nvcc -V
```

配置 MinkowskiEngine：

```bash
pip install setuptools==57.5.0
git clone https://github.com/NVIDIA/MinkowskiEngine.git
cd MinkowskiEngine
pip install .
```

获取 AnyGrasp SDK 并申请 License：

```bash
git clone https://github.com/graspnet/anygrasp_sdk.git
cd anygrasp_sdk/license_registration
./license_checker -f
```

按教材说明申请授权文件。若使用开源替代，可参考教材给出的 `graspness_unofficial` 项目。

安装 SDK 依赖：

```bash
cd anygrasp_sdk
pip install -r requirements.txt
cd pointnet2
pip install .
```

!!! note "课程代码状态"
    当前 `SH9959/EAI_project` 主仓库中没有教材所引用的 `grasp_sim_anygrasp.py`、`anygrasp_model.py` 和完整 `anygrasp_open` ROS 工程。因此本页保留教材中的运行接口；实际课程发放时请以助教提供的 AnyGrasp SDK / License / checkpoint / 实机工程为准。

## 2. 先跑 AnyGrasp 官方 Demo

把 detection 二进制、License、checkpoint 和官方 `demo.py` 放在同一个工作目录后执行：

```bash
chmod +x demo.sh
./demo.sh
```

**成功判据：** Open3D 窗口中能看到点云和一组抓取候选位姿。

## 3. PyBullet 仿真抓取

教材中的任务是让 Franka Panda 在 PyBullet 中完成 `pickup cube`。

### 核心数据流

1. PyBullet 渲染 RGB 和深度 Z-buffer；
2. 将 Z-buffer 还原为米制深度；
3. 根据相机内参把 RGB-D 反投影成点云；
4. AnyGrasp 输出 `cam_T_grasp`；
5. 从视图矩阵计算 `world_T_cam`；
6. 级联得到 `world_T_grasp = world_T_cam · cam_T_grasp`；
7. 将抓取位姿作为 IK 目标，执行靠近、闭合、抬升。

### 教材运行命令

在包含 `grasp_sim_anygrasp.py`、`anygrasp_model.py`、License 和 checkpoint 的工作目录执行：

```bash
conda activate anygrasp

python grasp_sim_anygrasp.py --gui \
  --checkpoint_path log/checkpoint_detection.tar \
  --cam-distance 0.35 --cam-fov 35 \
  --cam-yaw 0 --cam-pitch -85 \
  --cam-width 960 --cam-height 720
```

### 成功判据

- PyBullet GUI 中机械臂移动到方块上方；
- 夹爪到达预测位姿后闭合并把方块抬起；
- 终端打印相机内参、`world_T_cam`、`world_T_grasp`；
- `captures/` 下保存 RGB 和 Depth 图像。

## 4. 实机抓取

教材使用的实机配置：

| 项目 | 教材配置 |
|---|---|
| 机械臂 | Dobot CR5 |
| 夹爪 | DH AG95 二指夹爪 |
| RGB-D 相机 | Intel RealSense D435i |
| 系统 | Ubuntu 20.04 LTS |
| 中间件 | ROS1 Noetic |
| 手眼标定 | easy_handeye，Eye-to-Hand |

### 实机流程

```text
配置机械臂与相机
    ↓
7×10 标定板进行 Eye-to-Hand 手眼标定
    ↓
RealSense 输出 RGB-D
    ↓
AnyGrasp 计算相机坐标系抓取位姿
    ↓
手眼标定矩阵变换到机械臂坐标系
    ↓
MovJ / MoveIt 控制机械臂抓取与放置
```

教材建议手眼标定时采集约 **15 个不同机械臂姿态**，直到转换矩阵基本收敛；标定过程中相机和标定板固定关系不能变化。

完成标定后，教材中的抓取阶段需要三个终端：

```bash
# 终端 1：机械臂、相机、标定 TF 等
roslaunch anygrasp_open move.launch

# 终端 2：AnyGrasp 推理
rosrun anygrasp_open anygrasp_ros.py

# 终端 3：分步操作 GUI
rosrun anygrasp_open mover.py
```

### 实机安全

!!! danger "第一次运行必须分步"
    实机抓取涉及逆解、桌面碰撞、夹爪力度和坐标系误差。首次测试必须低速、逐步运行：**物体上方 → 下探 → 夹取 → 抬升 → 放置区上方 → 放置**。一旦位姿明显异常立即停止，不要让机器人继续执行整段轨迹。
