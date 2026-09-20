# 第 3 章：AnyGrasp 抓取

对应教材 **3.4.4 抓取实验**：先配置 AnyGrasp detection，再做 PyBullet 中的 Panda 抓方块，最后在 Dobot CR5 上抓取。教材印刷页 79—96，对应本次 v2.0 PDF 第 97—114 页。

> **本版验证范围（2026-09-20）**：已核对教材、手册和公开源码，并执行配套几何/文件检查的离线测试。没有运行 AnyGrasp 推理、PyBullet 抓取或真实机械臂。详细证据、版本与待补材料见[检查记录](../assets/ch3-grasp/verification.md)。

## 一、要做什么，怎样算成功

输入是 RGB-D 图像，输出是抓取位姿；机器人执行后，还要检查物体是否真的被夹住并抬起。**点云窗口能打开、模型有输出、机器人抓取成功，是三个不同的结果。**

| 阶段 | 输入与处理 | 验收证据 |
|---|---|---|
| SDK detection | 官方样例 RGB-D → 点云 → 候选抓取 | 授权与模型加载正常，显示有效候选；记录 SDK/权重版本和截图 |
| PyBullet 抓方块 | 仿真 RGB-D → AnyGrasp → 坐标变换 → IK | 记录方块离开支撑面的全过程，保存 RGB、原始深度和关键矩阵 |
| CR5 实机 | D435i RGB-D → 抓取预测 → 手眼变换 → 执行 | 经现场人员确认后分步抓取、抬升和放置；保留标定与执行记录 |

原始流程为：RGB-D → 相机系点云 → 相机系抓取 → 世界/基座系抓取 → 末端 IK → 靠近、闭合、抬升。位姿分数高不保证碰撞安全或真实抓取成功。

## 二、先检查条件，不急着安装

**AnyGrasp SDK 的 License 不是上一实验的云端 API Key。**这里是本机 SDK 授权，不能用 DashScope Key 或聊天软件订阅代替。[官方授权说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/license_registration/README.md)要求按工作机器申请。不要把机器特征码和授权文件提交到公开仓库。

| 条件 | 教材配置／本次核对结果 | 没有时停在哪 |
|---|---|---|
| 系统与二进制 | 教材是 Linux SDK；本页固定提交提供的是 Linux x86_64 的 CPython 二进制 | Windows PowerShell 可做配套离线检查；ARM 或其他解释器不能直接使用这些 `.so`，先确定课程 Linux 机器 |
| Python / CUDA / PyTorch | 教材举例 Python 3.9、CUDA 11.8、PyTorch 2.4 | 这是教材配置，不是本次验证过的完整锁文件；向助教取得可用环境/镜像和编译工具版本 |
| 依赖 | MinkowskiEngine、pointnet2、graspnetAPI 等 | 先核对 CUDA 编译器与 torch 编译版本，不在现有语音环境中混装 |
| 授权与权重 | 有效 License、与所选 SDK 匹配的 checkpoint | 先申请或领取；只有文件存在不代表授权有效 |
| 仿真工程 | `grasp_sim_anygrasp.py`、`anygrasp_model.py` | 本次检查的课程仓库树未提供这两个脚本，需助教补交 |
| 实机工程与设备 | `anygrasp_open`、CR5、AG95、D435i 及标定材料 | 没有完整工程或现场安全条件，不运行实机 |

### 2.1 现在就能做的离线检查

以下命令从**手册仓库根目录**运行，只使用 Python 标准库，不需要模型、GPU 或授权；可以使用已经创建的 `eai-dialogue` 环境，不需要再装一个环境。

```bash
python docs/assets/ch3-grasp/test_grasp_checks.py
python docs/assets/ch3-grasp/grasp_checks.py geometry
```

第一条检查解析公式、坐标约定和文件检查行为；第二条输出标有 `ANALYTIC_EXAMPLE_NOT_GRASP` 的解析例子。它们不是 AnyGrasp 抓取结果。

已经拿到 SDK 或仿真工程后，再检查实际路径。下面引号里的内容需换成你自己的目录；Windows 可用 `C:/...`，Linux 可用 `/home/...`：

```bash
python docs/assets/ch3-grasp/grasp_checks.py files --sdk "实际的/anygrasp_sdk目录" --sim-dir "实际的/仿真工作目录"
```

只拿到其中一个目录时，可只传对应参数。`MISSING` 为缺文件，`EMPTY` 为空文件，`LFS_POINTER_ONLY` 表示只有 Git LFS 指针；`PRESENT_NOT_EXECUTED` 只代表文件存在。工具按当前解释器的完整扩展后缀查找二进制；`MATCHING_NAME_NOT_LOADED` 表示找到同名候选但还未复制成 `gsnet.so`，`PRESENT_ABI_NOT_VALIDATED` 表示已有 `gsnet.so`，还需在 Linux 中实际导入验证。返回码 2 表示发现缺项、未完成复制或平台不匹配，不是“运行抓取失败”。没有提供的目录显示 `NOT_CHECKED`；无论返回码是多少，文件检查都不会判定可以抓取。

## 三、SDK 环境和官方样例

### 3.1 先决定采用哪一版

教材和原手册引用旧接口：`license_checker -f`、旧版 SDK 环境。**本次读取的上游 README 记载，2026-07-04 后改为 SDK 内的 `get_feature_id` / `check_license`，检测入口变为 `create_detector`，旧工具不再用于新申请。**已部署的旧机器可以保留旧 SDK；新机器应按当前官方指南配置。不能把新二进制、旧 Python 包装代码和旧授权流程任意组合。

本页下面的 SDK 命令属于**当前上游接口适配**，不是教材旧环境已复现的证明。本次核对固定提交 `b8eaafc9eca7babd5208e7a5ade3c561060be4c5`；运行前记录 `git rev-parse HEAD`、Python、torch、CUDA、编译器和权重来源，课堂复测通过后再冻结完整组合。[该版本安装说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/README.md#installation)使用修改过的 MinkowskiEngine，并区分 CUDA 分支；它与教材克隆 NVIDIA 原仓库的步骤不同。没有课程确认的组合时先申请环境，不直接照抄修改系统头文件的命令。

### 3.2 获取代码和安装顺序（Linux Bash）

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

`nvidia-smi` 的 CUDA 显示值、`nvcc -V` 的工具链版本、`torch.version.cuda` 的编译版本不是同一项，记录时分别填写。没有 `nvcc` 不能靠安装普通推理 wheel 自动补齐编译工具。课程尚无已验证锁文件时，停在这里申请环境，不承诺只装几条 pip 命令即可完成。

确认上述两条能导入后，在 `anygrasp_sdk` 根目录继续：

```bash
python -m pip install -r requirements.txt
(cd pointnet2 && python setup.py install)
```

graspnetAPI 按 SDK README 安装，最后执行 `python -m pip check`。这一步只是环境检查，不是推理验收。

### 3.3 匹配二进制并申请授权

在 `anygrasp_sdk` 根目录先查看 `grasp_detection/gsnet_versions/`，选择与**当前解释器及 CPU 架构**相符的文件。Linux 下可用下列命令选取当前解释器后缀；若找不到该文件，先查发布支持情况，不把其他版本的文件随意改名。三条命令用 `&&` 连接，前一步失败后不会继续：

```bash
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

官方样例所需布局如下。当前 `demo.py` 还读取 `seg_mask.png`，不能仅照旧页准备两张图。

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

### 3.4 运行 detection 样例

工作目录仍为 `grasp_detection/`，不是 SDK 根目录。该目录的相对路径是样例读取输入的依据。

```bash
python demo.py --checkpoint_path log/checkpoint_detection.tar --vis
```

该版本使用 `--vis`；不要照旧版脚本随意添加 `--debug`。输出为终端评分和 Open3D 窗口，脚本不会自动保存抓取记录。将脱敏终端输出和截图保存在自己的 `runs/grasp/` 记录目录，核对模型加载消息、候选数量/评分及画面。出现 `Failed to create detector!` 时，即使进程退出码为 0 也没有完成推理；没有候选时记录空输出，不把空窗口记为通过。官方演示包含多种 steering 配置，其中还展示关闭碰撞过滤的情况；这些是感知演示，不能直接作为实机安全动作。

教材复制 `example_data` 的命令缺少目录递归选项。本页改为在 SDK 自带目录运行，避免重复复制导致路径嵌套；确需复制目录时应使用 `cp -r`。

## 四、PyBullet：让 Panda 抓起方块

### 4.1 先补齐课程工程

本次核对的 `SH9959/EAI_project` 提交为 `e6bb5d5de828b5d87834ea169b53c09b376d8b09`，没有检索到教材两份仿真脚本及完整 `anygrasp_open` 工程。教材还写了 `SH9959/EAI.git` 地址；本次未取得该地址下可复现的完整交付，不能当成已下载。

向助教领取：两份仿真脚本及提交号、其匹配的 SDK/权重版本、物体资产、末端/抓取坐标系定义和依赖清单。**不使用自己编写的“固定位置抓方块”代码冒充 AnyGrasp pipeline。**配套 `grasp_checks.py` 也不替代这两份脚本。

### 4.2 相机几何先核对

教材定义：世界系 Z 向上；OpenGL 相机系 x 右、y 上、视线为 -Z；PIN/OpenCV 相机系 x 右、y 下、z 向前。深度要先从 Z-buffer 恢复为相机光轴方向的 Z 值，不是把灰度 PNG 的像素直接当米。

```text
Z = near * far / (far - (far - near) * z_buffer)
fx = fy = (height / 2) / tan(vertical_fov / 2)
cx = width / 2, cy = height / 2
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
```

公式中的 `vertical_fov` 要先转为弧度；命令行的 `--cam-fov` 单位仍是度。教材印刷页 82 的“左乘”措辞与该页写出的乘法顺序不一致，view 的转置还依赖数组恢复方式。本页明确采用：列向量、`A_T_B` 把 B 系坐标转换到 A 系。若用 NumPy 从 PyBullet 的 16 项列表恢复 view：

```python
V = np.asarray(view).reshape(4, 4, order="F")
world_T_cam_gl = np.linalg.inv(V)
world_T_cam_cv = world_T_cam_gl @ np.diag([1, -1, -1, 1])
world_T_grasp = world_T_cam_cv @ cam_T_grasp
```

这里 `np` 指 NumPy。使用 `order="F"` 后不要再额外转置一次。不同代码若使用默认行主序 reshape，需要重新核对推导，不能只根据公式外观判断相等。配套解析测试覆盖非零平移和非平凡旋转，不仅测试单位矩阵。

另一个容易混淆的地方是[官方 demo 的显示函数](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/grasp_detection/demo.py)：它为了展示对点云和夹爪共同施加 `diag(1, 1, -1, 1)`。这个矩阵的旋转块行列式为 -1，是镜像；不要把它当作上面的相机刚体变换传给 IK。

还需核对 **grasp 系到机器人工具/EE 系** 的固定变换。若 IK 接受工具原点目标，通常需要该工具变换；不能靠随意加 ±90° 来掩盖坐标错误。RGB-D 必须来自同一视图和相同分辨率，记录深度单位、near/far 与内参，保留原始数值深度，区分可视化 PNG 与实际输入。

### 4.3 完整工程到位后的教材命令

先进入助教交付的工作目录，确认两份脚本、License 和权重存在，且包装代码与 SDK 代际匹配，再运行。以下命令保留教材参数；本次未实际执行：

```bash
conda activate eai-anygrasp
python grasp_sim_anygrasp.py --gui --checkpoint_path log/checkpoint_detection.tar --cam-distance 0.35 --cam-fov 35 --cam-yaw 0 --cam-pitch -85 --cam-width 960 --cam-height 720
```

`--cam-distance` 单位米；`--cam-fov` 是垂直角度；yaw/pitch 单位度；width/height 是像素。教材预计输出 `captures/rgb.png`、`captures/depth.png` 和关键矩阵，需以交付脚本实际实现再次确认。

录像应覆盖靠近、闭合、抬升；同时检查是否夹住目标、是否穿模、是否掉落。机械臂到达位置或脚本退出 0 均不能单独证明抓取完成。

## 五、CR5 实机：工程到位后由现场人员带领

教材配置为 Ubuntu 20.04、ROS1 Noetic、Dobot CR5、DH AG95、D435i 和 eye-to-hand 标定。没有设备时可以登记资料缺项，不能用仿真成功替代实机。

**教材需要先纠正的交付问题**：印刷页 90 的 ROS1/catkin 流程却引用 `DOBOT_6Axis_ROS2_V4`；夹爪克隆命令在已有 `src` 下又加了一层 `src/`；tuw_marker_detection 命令缺 `git clone`；标定与抓取 launch 使用的机械臂包名不一致。应由助教提供与实际固件匹配的整套 ROS1 驱动及 launch，不只替换一个仓库名。本页没有修改其他人的驱动仓库。

手眼标定时，**相机相对机器人基座固定，标定板相对末端固定；相机与标定板之间的相对位姿必须随末端运动发生变化**。原手册“相机和标定板固定关系不能变化”不准确。教材正文印刷页 92 已写清正确固定关系，本页按该正文修改。

棋盘规格需确认表示的是格子数还是内角点数：教材图中是 8×11 格，标定参数写 7×10 内角点；图示方格尺寸为 20 mm，仍应量取手中打印板，检查是否缩放。核对使用的 CameraInfo/图像话题、光学坐标系与 TF。采集约 15 个姿态是教材示例，不是自动合格阈值；需要多方向姿态和独立位姿的标定验证。[easy_handeye 的 eye-on-base 说明](https://github.com/IFL-CAMP/easy_handeye#use-cases)也采用相机对基座固定、标记对末端固定的关系。

设备负责人确认驱动、限速、碰撞环境、急停与工作区后，才能运行教材的三个终端。每个终端需要 source 正确工作空间：

```bash
# 以下分别在三个终端运行，仅适用于已补齐并检查过的 ROS1 工程。
roslaunch anygrasp_open move.launch
rosrun anygrasp_open anygrasp_ros.py
rosrun anygrasp_open mover.py
```

依次验收物体上方、下探、夹取、抬升、放置区上方、放置、松爪后退离/抬起。首次联调不独自运行，也不让代理自动连续控制真实机械臂。位姿异常先停机排查，不能把手伸入正在运动的工作区。

## 六、记录与排错

| 现象 | 优先检查 |
|---|---|
| 找不到 `license_checker` | 是否拿了 2026-07 更新后的 SDK；按该版本授权说明操作 |
| `.so` 导入失败 | Linux/Windows、CPU 架构、Python ABI、CUDA/PyTorch 与编译依赖 |
| 模型文件很小或加载失败 | 是否仅有 Git LFS 指针，是否拿错 checkpoint 代际 |
| 样例找不到图片 | 当前目录是否为 `grasp_detection/`；新 demo 是否还需 `seg_mask.png` |
| 点云颠倒、抓取在物体后方 | 深度尺度、view 列主序、OpenGL/PIN 翻转是否重复 |
| 模型有位姿但 IK 不对 | 目标点/工具系偏移、位置单位、旋转约定与关节限位 |
| `roslaunch` 找不到包 | 是否补齐 ROS1 工程并 source；有没有混入 ROS2 驱动 |

每次记录：日期、操作系统、解释器和依赖版本、代码提交、模型/授权状态（不公开授权内容）、命令、实际输入输出、失败位置、修改与复测。未运行的阶段写“未运行”。

思考：候选抓取评分与抓取成功率为什么不等价？单独保存一张彩色深度图能否复现点云？只调相机后，哪些矩阵必须更新？
