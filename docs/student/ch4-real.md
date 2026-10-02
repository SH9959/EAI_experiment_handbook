# 第 4 章：实机任务规划

对应教材 **4.4.2 方块重排、4.4.3 汉诺塔**，印刷页 140—151（v2.0 PDF 第 158—169 页）。本实验把高层规划接到第 3 章的视觉感知与抓取执行上。

## 一、实验目标

| 任务 | 规划规则 | 完成条件 |
|---|---|---|
| 方块重排 | 每次取一个方块；只有上方没有其他方块时才能取走 | 三个方块按从上到下的顺序移至已确认的放置区，逐步状态与计划一致 |
| 汉诺塔 | 每次只移动一根柱子最上方的一个盘；大盘不能放在小盘上 | 所有盘从第 1 根柱子移到第 3 根，全过程合法 |

先完成离线规则检查，再按“图像 → 场景描述 → 规划 → 定位 → 抓取与放置”逐步执行。每次搬运后重新观察，核对实际状态。

## 二、实验环境配置

### 2.1 工程与设备材料

**实机工程尚未提供。** 课程提交 `e6bb5d5de828b5d87834ea169b53c09b376d8b09` 的 [实机目录 `for_real`](https://github.com/SH9959/EAI_project/tree/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_real)只有 `.gitkeep`，教材代码片段不能直接启动机器人。仅靠手册和仓库可完成 3.1、3.3.1 的离线练习；3.2、3.3.2 需下表材料，缺项时记录名称并停在对应步骤。

| 材料 | 需要领取或确认的内容 |
|---|---|
| 实机工程 | 工程目录与提交、环境锁文件、采集/定位/执行入口、启动与停止命令、单动作示例和输出位置 |
| 设备与驱动 | RealSense、机械臂和夹爪型号；匹配固件的驱动与工作空间。沿用第 3 章时为 D435i、CR5、AG95、Ubuntu 20.04 / ROS1 Noetic，不能将其启动文件直接套用于其他设备 |
| 采集与标定 | 同步且对齐的 RGB-D 样本、CameraInfo、图像编码及深度单位、相机到基座的手眼变换、夹爪工具坐标系及 TCP 偏移 |
| 模型配置 | Qwen-VL 识别、Qwen-max 规划；调用入口见[人机对话实验](ch3-dialogue.md)，另需当前账号可用的模型名、地域与额度 |
| 方块感知与抓取 | GroundingDINO 权重、处理器及版本；AnyGrasp SDK、有效授权和匹配权重；目标框、点云、抓取位姿的输入输出接口 |
| 场地与执行参数 | 红、蓝、黄三个方块，互不重叠的放置区；桌面/障碍物模型、速度与夹爪参数、动作完成反馈、超时和失败处理 |
| 汉诺塔补充材料 | 三根固定柱子及大小可区分的盘；柱子编号照片、盘子尺寸/厚度、各柱各层的抓取和放置位姿、越过柱顶的抬升路径 |

AnyGrasp 环境和手眼标定见[抓取实验](ch3-grasp.md)。现场先确认工作空间、工具参数、限速与急停，再验证单步动作；缺少标定或动作反馈时不连续执行。

### 2.2 输入与记录约定

从手册仓库根目录运行，创建本次记录目录。只需 Python 3.9 或更高版本，后文文件均保存到这里；重复实验时更换 `run-01`，保留旧结果。

```bash
python -c "from pathlib import Path; Path('runs/real-planning/run-01').mkdir(parents=True, exist_ok=False)"
```

按下表命名记录；实机工程使用其他名称时，在 `result.md` 中写明对应位置。

| 文件 | 内容与核对项 |
|---|---|
| `rgb_000.png`、`depth_000.npy`、`camera_000.json` | 原始彩色图、保持原精度的深度数组，以及时间戳、分辨率、编码、单位、内参和坐标系；每次动作后递增编号 |
| `scene_000.json` | 由图片核实过的物体 ID、上下关系或各柱盘子列表；被遮挡或无法判断的状态必须标明 |
| `planner_input.txt`、`planner_output.txt` | 本轮场景、任务规则、允许动作及模型原始回答；另记模型版本和生成参数 |
| `block_reference.json`、`plan.json` 或 `hanoi_plan.txt` | 参考计划与模型计划分开保存；动作序列不含可执行代码 |
| `checks.csv` | 步号、动作、执行前状态、规则检查、预测后状态、实际后状态、执行反馈和证据文件 |
| `result.md` | 实际完成阶段、最终目标核对、失败步骤及缺失材料 |

实机输出还应保存目标框图、目标点云、坐标变换和候选抓取位姿。先保留原始数据，再生成可视化；不能以画过框的图片或归一化深度预览替代原始测量。

## 三、实验过程

### 3.1 方块状态与规划检查

本例按教材图 4.23 设置：**从下到上为黄、蓝、红**。先用实物或纸面记录练习，不连接机械臂。将以下内容保存为 `scene_000.json`；列表统一按从下到上排列，`[]` 表示空区。

```json
{
  "stack": ["yellow", "blue", "red"],
  "place_red": [],
  "place_blue": [],
  "place_yellow": []
}
```

一次 `pick_place` 表示搬运一个方块。先将以下参考计划保存为 `block_reference.json` 并完成规则检查；有模型环境时再生成自己的计划。

```json
[
  {"action": "pick_place", "object": "red", "source": "stack", "target": "place_red"},
  {"action": "pick_place", "object": "blue", "source": "stack", "target": "place_blue"},
  {"action": "pick_place", "object": "yellow", "source": "stack", "target": "place_yellow"}
]
```

逐步核对：动作必须是 `pick_place`，参数、物体和区域必须存在；每次只能取 `stack` 的最后一项；颜色对应的放置区必须为空。通过后更新状态，失败时保留原状态并停止。将结果写入 `checks.csv`。

| 步号 | 搬运对象 | 动作前栈顶 | 动作后 `stack` | 新占用放置区 |
|---|---|---|---|---|
| 1 | red | red | `[yellow, blue]` | `place_red: [red]` |
| 2 | blue | blue | `[yellow]` | `place_blue: [blue]` |
| 3 | yellow | yellow | `[]` | `place_yellow: [yellow]` |

另做两个反例：把首步改成 `blue`，应因上方仍有 `red` 拒绝；把第 2 步目标改成已占用的 `place_red`，应因目标区不符且非空拒绝。在 `checks.csv` 中写出首个失败步骤、原因及未改变的状态。换初始堆叠顺序后重新生成计划，不沿用本表答案。

**生成模型计划**：完成[人机对话环境配置](ch3-dialogue.md)后，把下面内容保存为本次目录下的 `planner_input.txt`。场景变化时同时修改状态和任务。

```text
初始状态：{"stack":["yellow","blue","red"],"place_red":[],"place_blue":[],"place_yellow":[]}
列表按从下到上排列。把 stack 的三个方块分别搬到同色 place 区。
每步只允许 pick_place，一次搬一个方块，只能取源栈最后一项，目标区必须为空。
仅输出 JSON 数组，每项含 action、object、source、target，不加代码围栏或解释。
```

激活 `eai-dialogue` 环境，从手册根目录运行；`qwen-max` 替换为课程账号实际可用的文本模型名：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-max --question-file runs/real-planning/run-01/planner_input.txt --output runs/real-planning/run-01/planner_output.txt --send
```

保留原始回答，将其中的 JSON 数组另存为 `plan.json`，按上表逐步检查。回答格式错误时保存错误并重新请求；不能把任意模型文本作为 Python 代码执行。此步骤会发送提示词并使用 API 额度，没有配置账号时只完成参考计划练习。

### 3.2 方块感知与实机执行

#### 3.2.1 采集与场景描述

1. 使用实机工程的采集入口保存同一时刻附近的 RGB-D 和 CameraInfo。教材采用 `/camera/color/image_raw`、`/camera/aligned_depth_to_color/image_raw`、`/camera/aligned_depth_to_color/camera_info`；先与本机实际话题核对。机械臂静止、画面稳定后采集。
2. 打开彩色图和深度预览，确认三块颜色、堆叠顺序、放置区和目标区域深度有效。核对 RGB-D 分辨率、时间戳及对齐关系；未对齐的深度不能直接使用彩色图目标框。
3. 将彩色图交给 Qwen-VL，要求列出物体 ID、从下到上的堆叠关系、空放置区和不确定项。人工对照图片修正 `scene_000.json` 后再规划。模型无法确定遮挡关系时，调整视角重新采集。
4. 用已核实的场景生成计划，按 3.1 检查。再为本步目标生成定位描述，例如 `the red block on top of the blue block`；物体 ID 保持不变，描述随实际场景更新。

教材代码会读取已有 `basic_color.npy` 和 `basic_depth.npy` 作为背景；更换相机、桌面或分辨率后需要重新采集背景。背景只用于辅助处理，不能代替本轮观测。

#### 3.2.2 目标框与点云

| 操作 | 输入、参数及应检查的结果 |
|---|---|
| 目标定位 | 输入本步彩色图和目标描述，保存所有候选框及分数。教材框阈值和文本阈值示例均为 `0.1`；仅作调试起点，记录实际值并目视筛选，不固定取最后一个框 |
| 框坐标检查 | 输出为原图像素 `x1,y1,x2,y2`；要求 `0 ≤ x1 < x2 ≤ width`、`0 ≤ y1 < y2 ≤ height`。无框、多框或目标不清楚时停止本步；框不能同时包住多个方块 |
| 提取 RGB-D | 对彩色与已对齐深度使用同一目标区域，保留原始像素位置。供候选生成的深度只保留目标有效点，框外置为无效深度；另保留完整场景点云供障碍物检查，不能用目标点云代替碰撞环境 |
| 生成点云 | 使用该图对应的内参、深度单位和坐标系；剔除无效深度，显示点云并核对桌面方向、目标形状与实物尺度 |

接入教材代码时检查三处参数：

- GroundingDINO 的 `target_sizes` 应是 `(height, width)`，彩色数组使用 `[img.shape[:2]]`。阈值参数按当前处理器签名使用 `threshold` 或旧版 `box_threshold`。[接口说明](https://huggingface.co/docs/transformers/model_doc/grounding-dino#transformers.GroundingDinoProcessor.post_process_grounded_object_detection)
- `CameraInfo.D` 是畸变参数，不能作为内参。原始图使用 `K`，校正图使用匹配的 `P` 左上 3×3；裁剪或缩放后更新内参，并记录真实光学坐标系与手眼变换。[字段定义](https://github.com/ros/common_msgs/blob/noetic-devel/sensor_msgs/msg/CameraInfo.msg)
- Open3D 的 `depth_scale`：毫米深度用 `1000.0`，米深度用 `1.0`；`depth_trunc` 应覆盖实际工作距离，保留 RGB 时设 `convert_rgb_to_intensity=False`。用已知距离核对点云尺度。[参数说明](https://www.open3d.org/docs/latest/python_api/open3d.geometry.RGBDImage.html#open3d.geometry.RGBDImage.create_from_color_and_depth)

#### 3.2.3 抓取与逐步闭环

1. 将本步目标点云送入匹配版本的 AnyGrasp，保存候选位姿、分数、夹爪宽度和坐标系。无候选时返回目标定位与深度检查，不发送空位姿。
2. 使用已验证的相机到基座变换及 TCP 偏移转换位姿，检查夹爪朝向、可达性、关节限位、桌面和周边碰撞。教材的矩阵元素阈值及翻转矩阵依赖其坐标约定，不能作为其他设备的通用筛选条件。
3. 在负责人确认的限速下，先单步验证“目标上方 → 接近 → 夹取 → 抬升 → 放置区上方 → 放置 → 松爪 → 退离”。放置区位姿由设备工程配置；规划器只引用区名，不生成未经标定的坐标。
4. 每一段动作均等待驱动反馈。完成一次搬运后重新采集图像，确认源栈确实减少一块、对应放置区出现该块且夹爪已空，再更新实际状态并开始下一步。
5. 若滑落、抓空或反馈超时，记录最后确认的位置及当前观测并停止；不得把预测状态写作实际状态。恢复前重新识别、校验和规划。

一次完整的三块搬运应保存至少四组状态：初始状态和三次动作后的状态。

### 3.3 汉诺塔规划与执行

#### 3.3.1 离线动作校验

先固定柱子编号，并用数字表示盘的大小：`1` 最小，数值越大盘越大；每根柱子的列表仍按**从下到上**排列。下面用三盘练习，教材图 4.28 展示的是四盘，实机盘数须按实际场景填写。

在本次运行目录手动创建 `hanoi_state.json`：

```json
{"1": [3, 2, 1], "2": [], "3": []}
```

先把下面的三盘参考计划保存为 `hanoi_reference.txt`，完成后面的校验。有模型环境时，再按本节提示词生成自己的计划。

```text
(1)->(3)
(1)->(2)
(3)->(2)
(1)->(3)
(2)->(1)
(2)->(3)
(1)->(3)
```

**生成模型计划**：将以下内容保存为本次目录下的 `hanoi_input.txt`：

```text
汉诺塔有三根柱子，编号为1、2、3。盘1最小，盘3最大，列表按从下到上排列。
初始状态：{"1":[3,2,1],"2":[],"3":[]}。目标是把全部盘移到柱3。
每步只能移动源柱最上面的一个盘，大盘不能放在小盘上。
仅输出动作，每行格式为(源柱)->(目标柱)，不加编号、代码围栏或解释。
```

激活 3.1 使用的 `eai-dialogue` 环境，保留同一 API 配置，从手册根目录执行：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-max --question-file runs/real-planning/run-01/hanoi_input.txt --output runs/real-planning/run-01/hanoi_output.txt --send
```

`qwen-max` 按课程账号替换。该命令会调用模型并使用 API 额度；无账号时只校验参考计划。保留原始 `hanoi_output.txt`，将动作部分另存为 `hanoi_plan.txt`；格式或规则错误按原样检查并记录，不能手工改对后算作模型成功。

将以下代码保存为同目录下的 `check_hanoi.py`。只使用 Python 标准库，检查给定计划，不连接设备。

```python
import json
import re
import sys
from pathlib import Path

def require(condition, message):
    if not condition:
        raise ValueError(message)

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
require(isinstance(state, dict) and set(state) == {"1", "2", "3"}, "柱子须为 1、2、3")
require(all(isinstance(v, list) for v in state.values()), "每根柱子须为列表")
disks = [d for stack in state.values() for d in stack]
require(bool(disks) and all(type(d) is int and d > 0 for d in disks), "盘编号须为正整数")
n = len(disks)
require(sorted(disks) == list(range(1, n + 1)), "盘编号须连续且不重复")
require(all(all(a > b for a, b in zip(s, s[1:])) for s in state.values()), "初始堆叠不合法")
lines = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
require(bool(lines), "计划为空")
for step, line in enumerate(lines, 1):
    match = re.fullmatch(r"\(([123])\)->\(([123])\)", line.strip())
    require(match is not None, f"第 {step} 行格式错误")
    source, target = match.groups()
    require(source != target and bool(state[source]), f"第 {step} 步源柱无效")
    disk = state[source][-1]
    require(not state[target] or disk < state[target][-1], f"第 {step} 步大盘压小盘")
    state[source].pop()
    state[target].append(disk)
    print(step, json.dumps(state))
require(state == {"1": [], "2": [], "3": list(range(n, 0, -1))}, "计划未达目标")
print("PLAN_VALID; robot_executed=false")
```

从手册根目录运行（Bash 或 PowerShell 均可）：

```bash
python runs/real-planning/run-01/check_hanoi.py runs/real-planning/run-01/hanoi_state.json runs/real-planning/run-01/hanoi_reference.txt
```

参考计划应依次输出 7 个状态，最后为 `{"1": [], "2": [], "3": [3, 2, 1]}`，并输出 `PLAN_VALID; robot_executed=false`。有模型计划时，把命令最后一个文件名替换为 `hanoi_plan.txt` 再检查。这只表示离线计划合法，尚未执行实机。三盘最短解为 7 步；一般 `n` 盘标准初始状态的最少步数为 `2**n - 1`，合法但更长的计划须如实记下步数。

保留参考计划，将以下反例分别保存为新文件，每次均从原始 `hanoi_state.json` 开始检查：

| 反例文件 | 文件内容 | 应拒绝的位置 |
|---|---|---|
| `hanoi_empty.txt` | 仅一行 `(2)->(3)` | 第 1 步源柱为空 |
| `hanoi_order.txt` | 两行均为 `(1)->(3)` | 第 2 步试图把盘 2 放到盘 1 上 |
| `hanoi_format.txt` | 仅一行 `(1)->(4)` | 第 1 行格式不在三柱协议内 |
| `hanoi_short.txt` | 仅保留参考计划前 6 行 | 动作本身合法，但结束时未达目标 |

每次把命令最后一个参数改为对应文件，如 `runs/real-planning/run-01/hanoi_order.txt`。分别保存报错及退出状态；失败后从原始状态重新检查完整计划。

#### 3.3.2 场景识别与固定柱位执行

1. 拍摄带柱子编号的初始图，要求 Qwen-VL 输出三根柱子的盘子列表，并与实物逐个核对。盘的数量不能替代大小和上下顺序检查；视觉无法辨认时人工确认后再填入状态文件。
2. 将状态、目标与汉诺塔规则交给 Qwen-max，得到逐步计划，再转成上述动作协议并执行离线校验。保留教材的“规划 → 结构化动作 → 解析”顺序。
3. 检查已标定的固定柱位表：除每根柱的平面位置，还需源柱当前顶层抓取高度、目标柱放置高度和越过柱顶的高度；盘厚不同时按实际盘厚计算或逐层标定。不能把三个固定点反复用于所有层数。
4. 先由负责人验证一条合法搬运，确认盘完全离柱后才横移，放置时能够套入目标柱并释放。该步骤使用现场确认的抓放技能，不把 `(1)->(3)` 直接当作机械臂接口。
5. 全部单动作条件满足后，按计划逐步执行。每步记录源/目标柱、实际移动盘、抓放反馈和执行后照片；实际状态与预测不一致时停止并重新规划，完成后再检查第 1、2 柱为空且第 3 柱顺序正确。

本实验使用固定抓放位姿。改用动态抓取时，另需验证柱体避碰和套柱对准。

## 四、实验结果

| 阶段 | 需提交的记录 | 核对标准 |
|---|---|---|
| 方块离线规划 | 初始状态、计划、逐步状态表及两个反例 | 每次取栈顶，放置区有效，最终三块均已移走；反例在首个非法动作处停止 |
| 汉诺塔离线规划 | 状态文件、参考/模型计划、检查输出及四个反例 | 逐步遵守规则，最终盘数、盘编号和顺序完整；规则失败和未达目标均能识别 |
| 视觉与抓取准备 | RGB-D、相机参数、场景描述、框图、点云与候选位姿 | 身份、上下关系、深度尺度与坐标系一致；无效观测不进入执行 |
| 实机闭环 | `checks.csv`、逐步照片/录像、驱动反馈及 `result.md` | 每步实际状态支持动作已完成，最终目标达成；失败时有明确停止位置 |

在 `result.md` 中分别填写“离线规则检查、模型规划、相机感知、单次搬运、完整任务”的实际状态。未取得设备工程时填写缺失文件及停在哪一步；离线检查通过不能记为实机成功。

## 五、排错建议与注意事项

| 现象 | 优先检查 | 处理与复测 |
|---|---|---|
| 找不到启动入口 | `for_real` 是否仍只有占位文件；交付材料是否完整 | 向助教领取工程和设备配置；先完成离线规则检查 |
| 模型输出无法解析或违反规则 | 动作格式、物体 ID、场景状态、原始回答 | 保存失败输出，修正提示词后从当前真实状态重新规划，不使用 `eval`/`exec` 执行回答 |
| 框错位、包含相邻物体 | 目标描述、多个候选、目标尺寸顺序、RGB-D 对齐 | 修改描述并重新定位，核对框图；不能仅降低阈值后直接抓取 |
| 点云尺度或位置异常 | 深度单位、K/P、畸变、裁剪/缩放、手眼变换 | 用已知尺寸与位置验证；修复前不下发位姿 |
| 抓取位姿可视化正常但逆解失败 | 工具坐标系、关节限位、接近姿态 | 调整经验证的起始姿态或更换候选，重新检查完整路径 |
| 途中碰桌面、方块或柱子 | 障碍物模型、抬升路径、盘是否已离柱 | 按现场停机流程处理；重新验证路径后再恢复 |
| 物体滑落或盘未套入 | 夹爪宽度/力度、位姿、物体表面、柱位和层高 | 记录实际状态，按设备和物体允许范围调整；不盲目增加夹爪力度 |
| 驱动超时或反馈未知 | 最后确认动作、当前机器人/夹爪状态 | 停止后续动作，由现场人员核查；不可自动重试同一搬运 |

教材对应位置、参考检查结果与缺失资源见[检查记录](../assets/ch4-real/verification.md)。
