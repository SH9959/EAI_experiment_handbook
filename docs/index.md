<div class="hero" markdown>

# 《具身智能导论》实验手册

**教材实验范围：第 3 章具身感知 · 第 4 章具身推理 · 第 5 章具身执行**

<div class="hero-actions" markdown>
[学生从这里开始](student/index.md){ .md-button .md-button--primary }
[助教查看课前联调](ta/preclass.md){ .md-button }
[课程代码仓库](https://github.com/SH9959/EAI_project){ .md-button }
</div>

</div>

## 使用说明 {#usage-notes}

按课程安排选择实验，依次完成环境配置、实验过程和结果检查。依赖不同的实验分别配置环境。

部分页面配有辅助脚本；代码来源、版本和运行条件见对应实验页。离线测试及 `CHECK ONLY`、`FORMAT_ONLY`、`PLAN_ONLY` 只检查输入、格式或辅助逻辑，不能代替 API、模型、仿真或设备的真实运行。已执行的检查和待验证项保存在各页链接的检查记录中。

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
| 4.4.1 AI2THOR + 大模型规划 | [`for_ai2thor`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_simulator/for_ai2thor) | 课程示例：`demo_in_ai2thor.py`、`myController.py`、`action.json`；接口适配见[仿真任务规划](student/ch4-planning.md) |
| 4.4.1 VirtualHome | [`for_virtualhome`](https://github.com/SH9959/EAI_project/tree/main/chapter_4/4_1_task_planning/for_simulator/for_virtualhome) | 含课程示例 `demo_in_virtualhome.py`，需另装 VirtualHome 仿真器 |

!!! note "课程工程准备"
    教材中的 **AnyGrasp 完整抓取工程、方块重排/汉诺塔实机工程、iGibson 课程工程、ACT/cobot-magic 工程** 尚需向助教领取。具体文件与设备条件见各实验页。

## 实验路线

<div class="grid cards" markdown>

-   :material-eye-outline:{ .lg .middle } **第 3 章 · 具身感知**

    ---

    **实验：** 人机对话、多模态对话、语音交互、AnyGrasp 仿真与实机抓取

    [:octicons-arrow-right-24: 进入第 3 章实验](student/ch3-dialogue.md)

-   :material-head-cog-outline:{ .lg .middle } **第 4 章 · 具身推理**

    ---

    **实验：** ALFWorld、ALFRED、AI2THOR、VirtualHome、方块重排、汉诺塔、iGibson

    [:octicons-arrow-right-24: 进入第 4 章实验](student/ch4-planning.md)

-   :material-robot-industrial-outline:{ .lg .middle } **第 5 章 · 具身执行**

    ---

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
