<div class="hero" markdown>

# 《具身智能导论》实验手册

从教材到代码，从第一次运行到完成实验。

**教材实验范围：第 3 章具身感知 · 第 4 章具身推理 · 第 5 章具身执行**

<div class="hero-actions" markdown>
[学生从这里开始](student/index.md){ .md-button .md-button--primary }
[助教查看课前联调](ta/preclass.md){ .md-button }
[课程代码仓库](https://github.com/SH9959/EAI_project){ .md-button }
</div>

</div>

!!! tip "第一次做实验？只做三件事"
    1. 克隆课程代码仓库；
    2. 在下面的“实验路线”中找到本次实验；
    3. 进入对应页面，按 **环境 → 运行 → 成功判据** 顺序完成。不要一次安装所有实验环境。

## 先获取课程代码

```bash
cd ~
git clone https://github.com/SH9959/EAI_project.git
cd EAI_project
```

课程仓库中目前与教材实验直接对应的代码主要集中在以下位置：

| 教材实验 | 课程代码位置 | 说明 |
|---|---|---|
| 3.4.3 语音识别 | [`chapter_3/3_3_human_perception/3.3.3/SenseVoice`](https://github.com/SH9959/EAI_project/tree/main/chapter_3/3_3_human_perception/3.3.3/SenseVoice) | 含 `demo1.py`、`webui.py`、`requirements.txt` |
| 4.4.1 ALFWorld | [`chapter_4/4_1_task_planning/for_benchmark/alfworld`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_benchmark/alfworld) | 课程仓库记录官方子模块；实验页给出独立安装方法 |
| 4.4.1 ALFRED | [`chapter_4/4_1_task_planning/for_benchmark/alfred`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_benchmark/alfred) | 课程仓库记录官方子模块；实验页给出独立安装方法 |
| 4.4.1 AI2THOR + 大模型规划 | [`for_ai2thor`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor) | **课程自带可直接运行示例**：`demo_in_ai2thor.py`、`myController.py`、`action.json` |
| 4.4.1 VirtualHome | [`for_virtualhome`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_simulator/for_virtualhome) | 含课程示例 `demo_in_virtualhome.py`，需另装 VirtualHome 仿真器 |

!!! note "当前课程仓库未收录的教材实验代码"
    教材中的 **AnyGrasp 完整抓取工程、方块重排/汉诺塔实机工程、iGibson 课程工程、ACT/cobot-magic 工程** 当前不在 `SH9959/EAI_project` 主仓库中。本手册只按教材给出其官方依赖和实验流程，不虚构本地代码路径。

## 实验路线

<div class="grid cards" markdown>

-   :material-eye-outline:{ .lg .middle } **第 3 章 · 具身感知**

    ---

    先让智能体“看见、听见”，再把感知结果接入交互和抓取。

    **实验：** 人机对话、多模态对话、语音交互、AnyGrasp 仿真与实机抓取

    [:octicons-arrow-right-24: 进入第 3 章实验](student/ch3-dialogue.md)

-   :material-head-cog-outline:{ .lg .middle } **第 4 章 · 具身推理**

    ---

    让智能体根据目标和环境状态决定“下一步做什么”。

    **实验：** ALFWorld、ALFRED、AI2THOR、VirtualHome、方块重排、汉诺塔、iGibson

    [:octicons-arrow-right-24: 进入第 4 章实验](student/ch4-planning.md)

-   :material-robot-industrial-outline:{ .lg .middle } **第 5 章 · 具身执行**

    ---

    从示教数据学习策略，再让模型直接生成机器人动作。

    **实验：** ACT 仿真、cobot-magic 数据采集、训练与实机推理

    [:octicons-arrow-right-24: 进入第 5 章实验](student/ch5-imitation.md)

</div>

## 建议学习顺序

```text
人机对话 / 感知接口
        ↓
AnyGrasp 抓取
        ↓
任务规划（ALFWorld → AI2THOR / VirtualHome）
        ↓
实机任务规划（方块重排 → 汉诺塔）
        ↓
iGibson 具身导航
        ↓
ACT 模仿学习（仿真 → 实机）
```

不同实验使用的 Python、CUDA、ROS 版本并不相同，**不要试图把全部实验装在一个 Conda 环境中**。每个实验页都给出了独立环境名称和最小运行步骤。
