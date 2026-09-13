# 第 4 章：仿真任务规划

> 对应教材：**4.4.1 在仿真环境上的规划实验**。教材安排了 ALFWorld、ALFRED、AI2THOR 和 VirtualHome 四条路线。

## 你在这一章真正要学什么

任务规划回答的是：**给定任务目标、环境状态和可执行技能，智能体下一步应该做什么？**

建议按下面顺序做：

```text
ALFWorld：先理解规划任务的交互形式
    ↓
ALFRED：理解规划模型的训练与评价指标
    ↓
AI2THOR：让大模型根据图像 + 历史反馈逐步规划
    ↓
VirtualHome：把规划结果转成家庭活动脚本执行
```

## 1. ALFWorld：先体验规划任务

### 安装

```bash
conda create -n alfworld python=3.9 -y
conda activate alfworld
pip install 'alfworld[full]'
alfworld-download
```

### 运行

纯文本交互：

```bash
alfworld-play-tw
```

带 AI2THOR 实时画面：

```bash
alfworld-play-thor
```

**成功判据：** 可以根据文字观察选择动作，完成任务后终端出现 `you won`。

!!! question "做完以后想一想"
    仅凭“任务指令”还不够。一个能稳定规划的智能体至少还需要环境状态、可执行动作/技能、历史动作及执行反馈等信息。

## 2. ALFRED：训练与评价一个小规划模型

### 获取代码

```bash
mkdir -p ~/alfred_lab && cd ~/alfred_lab
git clone https://github.com/askforalfred/alfred.git
cd alfred
```

教材以 Seq2Seq/LSTM 模型为例。训练命令较重，若课程只要求体验评价流程，可直接使用官方预训练模型：

```bash
wget https://ai2-vision-alfred.s3-us-west-2.amazonaws.com/seq2seq_pm_chkpt.zip
unzip seq2seq_pm_chkpt.zip
```

### 主要评价指标

| 指标 | 含义 |
|---|---|
| SR | 整个任务是否成功 |
| GC | 已满足的子目标比例 |
| PLW SR | 路径长度加权的任务成功率 |
| PLW GC | 路径长度加权的子目标完成率 |

教材强调：即使最终任务失败，也要记录**为什么失败**，例如模型提前输出 `<stop>`、代理被障碍物卡住等。

## 3. AI2THOR：课程主仓库中的大模型规划 Demo

### 课程代码

- [`for_ai2thor/`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor)
- [`demo_in_ai2thor.py`](https://github.com/SH9959/EAI_project/blob/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/demo_in_ai2thor.py)
- [`myController.py`](https://github.com/SH9959/EAI_project/blob/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/myController.py)
- [`action.json`](https://github.com/SH9959/EAI_project/blob/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/action.json)

这个实验最能体现“观测—规划—执行—反馈”的闭环。代码默认任务是：

> `place a cup with a knife in it on the kitchen counter space`

默认场景为 `FloorPlan10`。

### 1. 创建环境

```bash
cd ~/EAI_project/chapter_4/4_1_task_planning/for_simulator/for_ai2thor
conda create -n ai2thor-plan python=3.9 -y
conda activate ai2thor-plan
pip install -r requirements.txt
```

### 2. 设置 API Key

```bash
export DASHSCOPE_API_KEY="你的Key"
```

课程示例会通过：

```python
os.getenv("DASHSCOPE_API_KEY")
```

读取 Key。

### 3. 运行

```bash
python demo_in_ai2thor.py
```

程序每一步会：

1. 读取当前环境图像；
2. 把任务、场景物体、技能集合、历史动作和反馈组成 Prompt；
3. 调用 `qwen-vl-plus` 输出下一步动作；
4. 用 `action.json` 检查动作是否合法；
5. 在 AI2THOR 中执行；
6. 把成功/失败反馈写入历史，再规划下一步。

![AI2THOR 示例](../assets/ai2thor_example.png)

**成功判据：** 终端连续输出合法动作，AI2THOR 场景随动作变化，最终模型输出 `done`；如果任务失败，应能从 `history` 中定位失败动作和环境错误信息。

### 4. 你的修改应该从哪里开始

最推荐先改两个变量：

```python
instruction = "你的新任务"
scene = "FloorPlanXX"
```

确认新任务可由 `action.json` 中已有技能完成，再修改 Prompt 或动作验证逻辑。

## 4. VirtualHome：把规划转成家庭活动脚本

### 课程代码

[`demo_in_virtualhome.py`](https://github.com/SH9959/EAI_project/blob/main/chapter_4/4_1_task_planning/for_simulator/for_virtualhome/demo_in_virtualhome.py)

### 安装主项目

```bash
git clone https://github.com/xavierpuigf/virtualhome.git
conda create -n virtualhome python=3.9 -y
conda activate virtualhome
cd virtualhome
pip install -e .
```

随后按 VirtualHome 官方方式下载 Unity 可执行程序。

课程示例运行前至少要修改两处本机路径：

```python
YOUR_FILE_NAME = "你的 VirtualHome 可执行程序路径"
```

以及示例末尾的视频输出目录。

教材给出的练习是：先让智能体完成“**把三文鱼放进冰箱**”，再尝试让大模型直接生成 VirtualHome 的规划脚本或易解析的规划语言。

## 本页完成检查

- [ ] ALFWorld 至少完成 1 个交互任务；
- [ ] 能解释 ALFRED 的 SR / GC / PLW 指标；
- [ ] 课程 AI2THOR demo 能运行，并能看到逐步动作与反馈；
- [ ] 能修改 AI2THOR 的任务指令并分析一次成功或失败；
- [ ] VirtualHome 能连接 Unity 仿真器并执行一段动作脚本。
