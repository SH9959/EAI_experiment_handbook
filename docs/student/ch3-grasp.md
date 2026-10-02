# 第 3 章：AnyGrasp 抓取

对应教材 **3.4.4 抓取实验**：AnyGrasp 候选抓取检测、PyBullet Panda 仿真抓取和 Dobot CR5 实机抓取（印刷页 79—96）。

## 一、实验目标

使用 RGB-D 图像生成候选抓取位姿，完成相机坐标系到世界/机器人基座坐标系的变换，并在仿真或实机中验证物体能否被夹住、抬起和放置。

实验流程为：RGB-D → 相机系点云 → 相机系抓取 → 世界/基座系抓取 → 末端 IK → 靠近、闭合、抬升。位姿分数高不保证碰撞安全或真实抓取成功。

## 二、实验环境配置

### 2.1 平台与前置材料

先按下表准备材料；缺少 License、权重或课程工程时，在对应阶段停止并记录缺项。AnyGrasp License 需按[官方说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/license_registration/README.md)为运行机器申请，机器特征码与授权文件不公开。

| 条件 | 配置要求 | 缺项处理 |
|---|---|---|
| 系统与二进制 | 教材是 Linux SDK；本页固定提交提供的是 Linux x86_64 的 CPython 二进制 | Windows PowerShell 可做配套离线检查；ARM 或其他解释器不能直接使用这些 `.so`，先确定课程 Linux 机器 |
| Python / CUDA / PyTorch | 教材举例 Python 3.9、CUDA 11.8、PyTorch 2.4 | 教材仅给出版本示例；完整依赖组合和编译工具版本需向助教确认 |
| 依赖 | MinkowskiEngine、pointnet2、graspnetAPI 等 | 先核对 CUDA 编译器与 torch 编译版本，不在现有语音环境中混装 |
| 授权与权重 | 有效 License、与所选 SDK 匹配的 checkpoint | 先申请或领取；只有文件存在不代表授权有效 |
| 仿真工程 | `grasp_sim_anygrasp.py`、`anygrasp_model.py` | 课程仓库的指定提交未提供这两个脚本，需向助教领取 |
| 实机工程与设备 | `anygrasp_open`、CR5、AG95、D435i 及标定材料 | 没有完整工程或现场安全条件，不运行实机 |

### 2.2 SDK 版本与接口

本页固定 SDK 提交 `b8eaafc9eca7babd5208e7a5ade3c561060be4c5`，使用 `get_feature_id` / `check_license` 授权和 `create_detector` 检测接口。按[该版本安装说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/README.md#installation)选择 MinkowskiEngine 的 CUDA 分支，不混用教材旧版的授权工具或模型包装代码；接口差异见[检查记录](../assets/ch3-grasp/verification.md)。未经课程负责人确认，不修改系统头文件。

### 2.3 代码获取与依赖安装（Linux Bash）

从单独的实验父目录开始，SDK 不放在手册仓库内部。已有副本先检查本地修改，不要覆盖。

```bash
conda create -n eai-anygrasp python=3.9 -y
conda activate eai-anygrasp
git clone https://github.com/graspnet/anygrasp_sdk.git
cd anygrasp_sdk
git checkout b8eaafc9eca7babd5208e7a5ade3c561060be4c5
git rev-parse HEAD
python --version
nvcc -V
```

先安装课程确认过的 CUDA/PyTorch/MinkowskiEngine 组合，再检查：

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import MinkowskiEngine; print(MinkowskiEngine.__version__)"
```

分别记录 `nvidia-smi`、`nvcc -V` 和 `torch.version.cuda`，它们表示驱动支持、编译工具链和 PyTorch 编译时使用的 CUDA 版本。找不到 `nvcc` 或导入失败时，向助教领取匹配环境配置，再继续安装。

确认上述两条能导入后，在 `anygrasp_sdk` 根目录继续：

```bash
python -m pip install -r requirements.txt
(cd pointnet2 && python setup.py install)
```

graspnetAPI 按 SDK README 安装，最后执行 `python -m pip check`。这一步只是环境检查，不是推理验收。

## 三、实验过程

### 3.1 SDK detection

#### 3.1.1 离线前置检查

以下命令从**手册仓库根目录**运行，只使用 Python 标准库，不需要模型、GPU 或授权；可以使用已经创建的 `eai-dialogue` 环境，不需要再装一个环境。

```bash
python docs/assets/ch3-grasp/grasp_checks.py geometry
```

预期显示 `ANALYTIC_EXAMPLE_NOT_GRASP`，并给出中心点 `[0, 0, 1]`。对照 3.2.2 的公式检查坐标换算；此命令不生成抓取候选。

检查已取得的 SDK 或仿真工程时，将路径替换为实际目录；Windows 可用 `C:/...`，Linux 可用 `/home/...`。二进制检查应在实际 SDK 环境中执行，否则报告只反映当前检查环境的平台与 Python ABI：

```bash
python docs/assets/ch3-grasp/grasp_checks.py files --sdk "实际的/anygrasp_sdk目录" --sim-dir "实际的/仿真工作目录"
```

只检查一个目录时，仅传对应参数。按以下结果补齐材料：

| 状态 | 含义与处理 |
|---|---|
| `MISSING` / `EMPTY` | 文件缺失或为空，补齐后复查 |
| `LFS_POINTER_ONLY` | 只有 Git LFS 指针，需取得实际文件 |
| `PRESENT_NOT_EXECUTED` | 文件存在，尚未执行验证 |
| `MATCHING_NAME_NOT_LOADED` | 找到匹配名称的二进制；按下一节复制为 `gsnet.so` |
| `PRESENT_ABI_NOT_VALIDATED` | 已有 `gsnet.so`，仍需在 Linux SDK 环境中导入验证 |
| `NOT_CHECKED` | 未提供对应目录，未检查 |
| `PLATFORM_MISMATCH` | 当前平台不是 Linux；二进制导入和推理需在课程 Linux SDK 环境中进行 |

返回码 2 表示缺项、未完成复制或平台不匹配；文件检查不执行推理，也不判定抓取结果。

#### 3.1.2 二进制选择与授权

在 Linux 终端进入 `anygrasp_sdk` 根目录，激活 2.3 配置的环境，再选择与**当前解释器及 CPU 架构**相符的文件。找不到对应二进制时先查发布支持情况，不将其他版本改名使用。下列命令用 `&&` 连接，前一步失败后停止：

```bash
conda activate eai-anygrasp &&
SUFFIX=$(python -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))') &&
test -f "grasp_detection/gsnet_versions/gsnet${SUFFIX}" &&
cp "grasp_detection/gsnet_versions/gsnet${SUFFIX}" grasp_detection/gsnet.so
```

确认上面成功后，再进入 detection 目录读取本机特征码：

```bash
cd grasp_detection
python -c "from gsnet import get_feature_id; print(get_feature_id())"
```

`test -f` 失败时停止，不执行后续复制和导入。按官方授权页提交申请；领取后保留整个 `license/` 目录，不只复制其中一个 `.lic`。将目录放到当前 `grasp_detection/` 内，再执行：

```bash
python -c "from gsnet import check_license; check_license('license')"
```

官方样例所需布局如下。该版本的 `demo.py` 同时读取彩色图、深度图和 `seg_mask.png`。

```text
anygrasp_sdk/grasp_detection/
├── demo.py
├── demo.sh
├── gsnet.so
├── license/                 # 按授权邮件原样保留目录内容
├── log/checkpoint_detection.tar
└── example_data/
    ├── color.png
    ├── depth.png
    └── seg_mask.png
```

三张样例图随 SDK 提供，`log/checkpoint_detection.tar` 需向助教或 SDK 提供方领取匹配版本；未取得权重前停止。模型和授权不要提交到手册仓库。先使用官方样例；自采数据必须更换相机内参和深度尺度。

#### 3.1.3 官方 detection 样例

保持在 `grasp_detection/` 目录，运行：

```bash
python demo.py --checkpoint_path log/checkpoint_detection.tar --vis
```

运行后检查：

| 输出 | 检查方法 |
|---|---|
| 终端评分与 Open3D 窗口 | 核对模型加载、候选数量、评分和画面；脚本不自动保存记录，将脱敏日志和截图保存到自己的 `runs/grasp/` |
| `Failed to create detector!` | 检测器创建失败；即使退出码为 0，也未完成推理 |
| 候选为空 | 记录空输出，检查输入和模型状态，不能仅凭窗口打开判定通过 |

官方演示的 steering 配置包含关闭碰撞过滤的情况，只用于感知演示，不能直接作为实机动作。

### 3.2 PyBullet 仿真抓取

#### 3.2.1 工程准备

**当前仓库缺少 `grasp_sim_anygrasp.py` 和 `anygrasp_model.py`，此阶段暂时无法运行。** 向助教领取这两份脚本、提交号、匹配的 SDK/权重、物体资产、末端/抓取坐标系定义及依赖清单。文件检查工具 `grasp_checks.py` 不能替代仿真工程；已核对的来源见[检查记录](../assets/ch3-grasp/verification.md)。

#### 3.2.2 相机几何与坐标变换

教材定义：世界系 Z 向上；OpenGL 相机系 x 右、y 上、视线为 -Z；PIN/OpenCV 相机系 x 右、y 下、z 向前。深度要先从 Z-buffer 恢复为相机光轴方向的 Z 值，不是把灰度 PNG 的像素直接当米。

```text
Z = near * far / (far - (far - near) * z_buffer)
fx = fy = (height / 2) / tan(vertical_fov / 2)
cx = width / 2, cy = height / 2
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
```

公式中的 `vertical_fov` 使用弧度，命令行 `--cam-fov` 使用度。以下采用列向量约定：`A_T_B` 把 B 系坐标转换到 A 系。用 NumPy 从 PyBullet 的 16 项列表恢复 view 时：

```python
V = np.asarray(view).reshape(4, 4, order="F")
world_T_cam_gl = np.linalg.inv(V)
world_T_cam_cv = world_T_cam_gl @ np.diag([1, -1, -1, 1])
world_T_grasp = world_T_cam_cv @ cam_T_grasp
```

这里 `np` 指 NumPy。`order="F"` 按列主序恢复矩阵，此后不要再转置；使用其他存储顺序时需重新核对变换。

[官方 demo 的显示函数](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/grasp_detection/demo.py)为展示结果，会对点云和夹爪共同施加 `diag(1, 1, -1, 1)`。这个矩阵的旋转块行列式为 -1，是镜像；不要把它当作上面的相机刚体变换传给 IK。

还需核对 **grasp 系到机器人工具/EE 系** 的固定变换。若 IK 接受工具原点目标，通常需要该工具变换；不能靠随意加 ±90° 来掩盖坐标错误。RGB-D 必须来自同一视图和相同分辨率，记录深度单位、near/far 与内参，保留原始数值深度，区分可视化 PNG 与实际输入。

#### 3.2.3 仿真运行

先进入助教交付的工作目录，确认两份脚本、License 和权重存在，且包装代码与 SDK 代际匹配，再运行。以下命令沿用教材参数，尚待完整工程到位后实测：

```bash
conda activate eai-anygrasp
python grasp_sim_anygrasp.py --gui --checkpoint_path log/checkpoint_detection.tar --cam-distance 0.35 --cam-fov 35 --cam-yaw 0 --cam-pitch -85 --cam-width 960 --cam-height 720
```

`--cam-distance` 单位米；`--cam-fov` 是垂直角度；yaw/pitch 单位度；width/height 是像素。教材预计输出 `captures/rgb.png`、`captures/depth.png` 和关键矩阵，需以交付脚本实际实现再次确认。

### 3.3 CR5 实机抓取

#### 3.3.1 工程与设备准备

需要 Ubuntu 20.04、ROS1 Noetic、Dobot CR5、DH AG95、D435i，以及与设备固件匹配的 `anygrasp_open`、ROS1 驱动和 launch 文件。**当前未提供完整实机工程与设备条件。** 向助教领取后再继续，不混装 ROS2 驱动；教材命令修正见[检查记录](../assets/ch3-grasp/verification.md)。

#### 3.3.2 Eye-to-Hand 手眼标定

手眼标定时，**相机相对机器人基座固定，标定板相对末端固定**。移动末端，让标定板以不同位置和角度出现在画面中；过程中不要移动相机或重新安装标定板。

教材棋盘为 8×11 格、7×10 个内角点，标称边长 20 mm；量取实际打印板后填写参数。核对 CameraInfo、图像话题、光学坐标系与 TF。采集约 15 个多方向姿态后，用未参与计算的姿态检查标定；误差通过现场要求后保存矩阵。配置参考 [easy_handeye 的 eye-on-base 说明](https://github.com/IFL-CAMP/easy_handeye#use-cases)。

#### 3.3.3 分步抓取

设备负责人确认驱动、限速、碰撞环境、急停与工作区后，打开三个 Bash 终端。每个终端先执行以下两行，将 `/实际工作空间` 换成助教交付并编译通过的 catkin 工作空间：

```bash
source /opt/ros/noetic/setup.bash
source /实际工作空间/devel/setup.bash
```

随后分别在三个终端运行：

```bash
# 终端 1：启动设备与坐标变换
roslaunch anygrasp_open move.launch
# 终端 2：启动抓取预测
rosrun anygrasp_open anygrasp_ros.py
# 终端 3：打开分步控制界面
rosrun anygrasp_open mover.py
```

在控制界面逐步执行：到物体上方 → 下探 → 夹取 → 抬升 → 到放置区上方 → 放置 → 松爪并退离。每步核对实际位置后再进行下一步；位置或方向异常时停机。

## 四、实验结果

按下表分别验收 SDK detection、仿真抓取和实机抓取，保存对应证据。

| 阶段 | 输入与处理 | 验收证据 |
|---|---|---|
| SDK detection | 官方样例 RGB-D → 点云 → 候选抓取 | 授权与模型加载正常，显示有效候选；记录 SDK/权重版本和截图 |
| PyBullet 抓方块 | 仿真 RGB-D → AnyGrasp → 坐标变换 → IK | 记录方块离开支撑面的全过程，保存 RGB、原始深度和关键矩阵 |
| CR5 实机 | D435i RGB-D → 抓取预测 → 手眼变换 → 执行 | 经现场人员确认后分步抓取、抬升和放置；保留标定与执行记录 |

录像应覆盖靠近、闭合、抬升；同时检查是否夹住目标、是否穿模、是否掉落。机械臂到达位置或脚本退出 0 均不能单独证明抓取完成。

每次记录：日期、操作系统、解释器和依赖版本、代码提交、模型/授权状态（不公开授权内容）、命令、实际输入输出、失败位置、修改与复测。未运行的阶段写“未运行”。

结果分析应说明候选评分与抓取成功率的区别、彩色深度图能否复现点云，以及相机位置变化后需要更新哪些矩阵。

## 五、排错建议与注意事项

| 现象 | 优先检查 |
|---|---|
| 找不到 `license_checker` | 是否拿了 2026-07 更新后的 SDK；按该版本授权说明操作 |
| `.so` 导入失败 | Linux/Windows、CPU 架构、Python ABI、CUDA/PyTorch 与编译依赖 |
| 模型文件很小或加载失败 | 是否仅有 Git LFS 指针，是否拿错 checkpoint 代际 |
| 样例找不到图片 | 当前目录是否为 `grasp_detection/`；新 demo 是否还需 `seg_mask.png` |
| 点云颠倒、抓取在物体后方 | 深度尺度、view 列主序、OpenGL/PIN 翻转是否重复 |
| 模型有位姿但 IK 不对 | 目标点/工具系偏移、位置单位、旋转约定与关节限位 |
| `roslaunch` 找不到包 | 是否补齐 ROS1 工程并 source；有没有混入 ROS2 驱动 |

首次联调必须由现场负责人陪同，采用分步控制；位姿异常先停机，不把手伸入正在运动的工作区。

已验证范围与资料缺项见[检查记录](../assets/ch3-grasp/verification.md)。
