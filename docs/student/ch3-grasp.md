# 第 3 章：AnyGrasp 抓取

对应教材 **3.4.4 抓取实验**，包括 AnyGrasp detection、PyBullet Panda 仿真抓取和 Dobot CR5 实机抓取。教材印刷页 79—96，对应 v2.0 PDF 第 97—114 页。

## 一、实验目标

使用 RGB-D 图像生成候选抓取位姿，完成相机坐标系到世界/机器人基座坐标系的变换，并在仿真或实机中验证物体能否被夹住、抬起和放置。

实验流程为：RGB-D → 相机系点云 → 相机系抓取 → 世界/基座系抓取 → 末端 IK → 靠近、闭合、抬升。位姿分数高不保证碰撞安全或真实抓取成功。

## 二、实验环境配置

### 2.1 平台与前置材料

AnyGrasp SDK 使用本机 License 授权。[官方授权说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/license_registration/README.md)要求按工作机器申请。不要把机器特征码和授权文件提交到公开仓库。

| 条件 | 配置要求 | 缺项处理 |
|---|---|---|
| 系统与二进制 | 教材是 Linux SDK；本页固定提交提供的是 Linux x86_64 的 CPython 二进制 | Windows PowerShell 可做配套离线检查；ARM 或其他解释器不能直接使用这些 `.so`，先确定课程 Linux 机器 |
| Python / CUDA / PyTorch | 教材举例 Python 3.9、CUDA 11.8、PyTorch 2.4 | 教材仅给出版本示例；完整依赖组合和编译工具版本需向助教确认 |
| 依赖 | MinkowskiEngine、pointnet2、graspnetAPI 等 | 先核对 CUDA 编译器与 torch 编译版本，不在现有语音环境中混装 |
| 授权与权重 | 有效 License、与所选 SDK 匹配的 checkpoint | 先申请或领取；只有文件存在不代表授权有效 |
| 仿真工程 | `grasp_sim_anygrasp.py`、`anygrasp_model.py` | 课程仓库的指定提交未提供这两个脚本，需向助教领取 |
| 实机工程与设备 | `anygrasp_open`、CR5、AG95、D435i 及标定材料 | 没有完整工程或现场安全条件，不运行实机 |

### 2.2 SDK 版本与接口

教材使用旧版 SDK 和 `license_checker -f` 授权命令。上游自 2026-07-04 起改用 SDK 内的 `get_feature_id` / `check_license`，检测入口改为 `create_detector`，旧工具不再用于新申请。已部署的旧机器可以保留原 SDK；更新时须同时核对二进制、Python 包装代码和授权流程。

下列命令适配新版 SDK，固定提交为 `b8eaafc9eca7babd5208e7a5ade3c561060be4c5`，不代表教材旧环境的原样复现。记录源码提交、Python、torch、CUDA、编译器和权重版本，复测通过后再冻结依赖组合。[该版本安装说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/README.md#installation)使用修改过的 MinkowskiEngine，并区分 CUDA 分支；它与教材克隆 NVIDIA 原仓库的步骤不同。没有课程确认的组合时先申请环境，不直接照抄修改系统头文件的命令。

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

`nvidia-smi` 的 CUDA 显示值、`nvcc -V` 的工具链版本、`torch.version.cuda` 的编译版本不是同一项，记录时分别填写。没有 `nvcc` 不能靠安装普通推理 wheel 自动补齐编译工具。缺少经过验证的环境配置时，先向助教补齐，再继续安装。

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
python docs/assets/ch3-grasp/test_grasp_checks.py
python docs/assets/ch3-grasp/grasp_checks.py geometry
```

第一条检查解析公式、坐标约定和文件检查行为；第二条输出标有 `ANALYTIC_EXAMPLE_NOT_GRASP` 的解析例子。它们不是 AnyGrasp 抓取结果。

检查已取得的 SDK 或仿真工程时，将路径替换为实际目录；Windows 可用 `C:/...`，Linux 可用 `/home/...`。二进制检查应在实际 SDK 环境中执行，否则报告只反映当前检查环境的平台与 Python ABI：

```bash
python docs/assets/ch3-grasp/grasp_checks.py files --sdk "实际的/anygrasp_sdk目录" --sim-dir "实际的/仿真工作目录"
```

只拿到其中一个目录时，可只传对应参数。`MISSING` 为缺文件，`EMPTY` 为空文件，`LFS_POINTER_ONLY` 表示只有 Git LFS 指针；`PRESENT_NOT_EXECUTED` 只代表文件存在。工具按当前解释器的完整扩展后缀查找二进制；`MATCHING_NAME_NOT_LOADED` 表示找到同名候选但还未复制成 `gsnet.so`，`PRESENT_ABI_NOT_VALIDATED` 表示已有 `gsnet.so`，还需在 Linux 中实际导入验证。返回码 2 表示发现缺项、未完成复制或平台不匹配，不是“运行抓取失败”。没有提供的目录显示 `NOT_CHECKED`；无论返回码是多少，文件检查都不会判定可以抓取。

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

该提交的 Git 文件树含三张样例图，但不含 `log/checkpoint_detection.tar`。checkpoint 应向助教或 SDK 提供方领取与该接口匹配的文件及版本说明；本页没有经过核实的公开权重下载地址。不要将模型/授权复制进手册 Git 仓库。使用官方样例先验收环境；自采相机数据还需更换内参和深度尺度。

#### 3.1.3 官方 detection 样例

工作目录仍为 `grasp_detection/`，不是 SDK 根目录。该目录的相对路径是样例读取输入的依据。

```bash
python demo.py --checkpoint_path log/checkpoint_detection.tar --vis
```

该版本使用 `--vis`；不要照旧版脚本随意添加 `--debug`。输出为终端评分和 Open3D 窗口，脚本不会自动保存抓取记录。将脱敏终端输出和截图保存在自己的 `runs/grasp/` 记录目录，核对模型加载消息、候选数量/评分及画面。出现 `Failed to create detector!` 时，即使进程退出码为 0 也没有完成推理；没有候选时记录空输出，不把空窗口记为通过。官方演示包含多种 steering 配置，其中还展示关闭碰撞过滤的情况；这些是感知演示，不能直接作为实机安全动作。

教材复制 `example_data` 的命令缺少目录递归选项。以上步骤直接使用 SDK 自带目录；确需复制目录时使用 `cp -r`，并检查目标路径，避免嵌套同名目录。

### 3.2 PyBullet 仿真抓取

#### 3.2.1 工程准备

`SH9959/EAI_project` 提交 `e6bb5d5de828b5d87834ea169b53c09b376d8b09` 未提供两份仿真脚本及完整 `anygrasp_open` 工程；教材另列的 `SH9959/EAI.git` 地址也尚无经过核实的完整交付。取得工程前，此阶段无法运行。

向助教领取：两份仿真脚本及提交号、其匹配的 SDK/权重版本、物体资产、末端/抓取坐标系定义和依赖清单。固定位置抓取代码和配套 `grasp_checks.py` 均不包含完整的 AnyGrasp pipeline，不能替代这两份脚本。

#### 3.2.2 相机几何与坐标变换

教材定义：世界系 Z 向上；OpenGL 相机系 x 右、y 上、视线为 -Z；PIN/OpenCV 相机系 x 右、y 下、z 向前。深度要先从 Z-buffer 恢复为相机光轴方向的 Z 值，不是把灰度 PNG 的像素直接当米。

```text
Z = near * far / (far - (far - near) * z_buffer)
fx = fy = (height / 2) / tan(vertical_fov / 2)
cx = width / 2, cy = height / 2
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
```

公式中的 `vertical_fov` 要先转为弧度；命令行的 `--cam-fov` 单位仍是度。教材印刷页 82 的“左乘”措辞与该页写出的乘法顺序不一致，view 的转置还依赖数组恢复方式。以下采用列向量约定：`A_T_B` 把 B 系坐标转换到 A 系。若用 NumPy 从 PyBullet 的 16 项列表恢复 view：

```python
V = np.asarray(view).reshape(4, 4, order="F")
world_T_cam_gl = np.linalg.inv(V)
world_T_cam_cv = world_T_cam_gl @ np.diag([1, -1, -1, 1])
world_T_grasp = world_T_cam_cv @ cam_T_grasp
```

这里 `np` 指 NumPy。使用 `order="F"` 后不要再额外转置一次。不同代码若使用默认行主序 reshape，需要重新核对推导，不能只根据公式外观判断相等。

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

教材配置为 Ubuntu 20.04、ROS1 Noetic、Dobot CR5、DH AG95、D435i 和 eye-to-hand 标定。没有设备时可以登记资料缺项，不能用仿真成功替代实机。

教材工程说明存在以下不一致：印刷页 90 的 ROS1/catkin 流程却引用 `DOBOT_6Axis_ROS2_V4`；夹爪克隆命令在已有 `src` 下又加了一层 `src/`；tuw_marker_detection 命令缺 `git clone`；标定与抓取 launch 使用的机械臂包名不一致。应由助教提供与实际固件匹配的整套 ROS1 驱动及 launch，不只替换一个仓库名。

#### 3.3.2 Eye-to-Hand 手眼标定

手眼标定时，**相机相对机器人基座固定，标定板相对末端固定；相机与标定板之间的相对位姿必须随末端运动发生变化**。这与教材印刷页 92 的正文一致；“相机和标定板相对固定”的说法不适用于此配置。

棋盘规格需确认表示的是格子数还是内角点数：教材图中是 8×11 格，标定参数写 7×10 内角点；图示方格尺寸为 20 mm，仍应量取手中打印板，检查是否缩放。核对使用的 CameraInfo/图像话题、光学坐标系与 TF。采集约 15 个姿态是教材示例，不是自动合格阈值；需要多方向姿态和独立位姿的标定验证。[easy_handeye 的 eye-on-base 说明](https://github.com/IFL-CAMP/easy_handeye#use-cases)也采用相机对基座固定、标记对末端固定的关系。

#### 3.3.3 分步抓取

设备负责人确认驱动、限速、碰撞环境、急停与工作区后，才能运行教材的三个终端。每个终端需要 source 正确工作空间：

```bash
# 以下分别在三个终端运行，仅适用于已补齐并检查过的 ROS1 工程。
roslaunch anygrasp_open move.launch
rosrun anygrasp_open anygrasp_ros.py
rosrun anygrasp_open mover.py
```

依次验收物体上方、下探、夹取、抬升、放置区上方、放置、松爪后退离/抬起。

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

首次联调不独自运行，也不让代理自动连续控制真实机械臂。位姿异常先停机排查，不能把手伸入正在运动的工作区。

源码核对、已执行的离线检查及尚未运行的阶段见[检查记录](../assets/ch3-grasp/verification.md)。
