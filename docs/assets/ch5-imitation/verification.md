# ACT 模仿学习：修订与验证记录

检查日期：2026-10-01。本轮完成教材文字、固定源码与文档静态检查；未安装实验环境、录制数据、训练模型、运行评估或启动机器人。正文中的产物名称和成功判据来自源码，并非本轮实际生成的实验结果。

## 来源

- 教材《具身智能导论-v2.0.pdf》第 5.7.1 节，印刷页 189—201（PDF 第 207—219 页）。本轮读取新文件的文本提取，核对仿真、实机两条流程及 50 条示教、2000/3000 epoch 等基线设置；未对教材图表作本轮目视验收。
- ACT：`tonyzhaozh/act@742c753c0d4a5d87076c8f69e5628c79a8cc5488`。核对 [README](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/README.md)、[constants.py](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/constants.py)、[录制入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/record_sim_episodes.py)、[可视化入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/visualize_episodes.py)、[训练评估入口](https://github.com/tonyzhaozh/act/blob/742c753c0d4a5d87076c8f69e5628c79a8cc5488/imitate_episodes.py)、数据加载、backbone、DETR 参数和 `conda_env.yaml`。
- cobot-magic：`sheji105/cobot_magic@70c11788f1a750c3e27453a2472fdd6bea59c675`，为教材指定仓库。核对 [采集入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/collect_data/collect_data.py)、[可视化入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/collect_data/visualize_episodes.py)、[训练入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/aloha-devel/act/train.py)、[推理入口](https://github.com/sheji105/cobot_magic/blob/70c11788f1a750c3e27453a2472fdd6bea59c675/aloha-devel/act/inference.py)、两份 requirements、数据加载、模型导入链、ROS 包名、相机 launch 与机械臂启动脚本。
- [PyTorch 官方历史安装表](https://pytorch.org/get-started/previous-versions/#v201)给出 torch 2.0.1 / torchvision 0.15.2 的 CUDA 11.8 配对。正文用它补足教材未固定的 torch/torchvision 配对，不代表已完成 ACT/ROS 全栈兼容性验证。

只读获取两仓库的提交信息、文件树和少量文本源码，保存在手册仓库外的本地审阅目录；未下载数据集或模型权重。固定源码提交后，仍需按本机驱动、ROS 与 Python 检查依赖。

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

## 本轮实际检查

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

1. 在匹配的 Linux/GPU/渲染环境完成导入和两条仿真示教，确认 HDF5、视频和曲线可读。
2. 采集 50 条、运行短流程，再训练完整基线并评估 50 次；保存真实成功数、平均回报和失败视频。
3. 实机需实验台提供可用 ROS/Python 环境。上游 requirements 未锁定全部传递依赖，`cv_bridge` 与 Conda 的兼容性、`robomimic`/`diffusers` 的导入链尚未在该主机验证。
4. 完成 CAN/相机序列号配置、三相机与四臂话题核对后，再采集、训练和在设备负责人现场监督下推理。

没有实机、依赖导入失败或图像/关节话题不完整时，应按正文记录卡点；不能将静态参数检查、短流程检查或教材参考图写成任务成功。
