# 助教：课前联调

本页按照教材实验顺序给出“课前最小可运行检查”。每项只要求证明实验链路能跑，不需要提前完成学生的实验任务。

## 0. 代码仓库

确认课程仓库可以访问：

```bash
git clone https://github.com/SH9959/EAI_project.git
```

重点检查：

```text
chapter_3/.../SenseVoice/demo1.py
chapter_4/.../for_ai2thor/demo_in_ai2thor.py
chapter_4/.../for_ai2thor/action.json
chapter_4/.../for_virtualhome/demo_in_virtualhome.py
```

## 1. 第 3 章人机对话

课前至少验证：

- DashScope 文本 API 能返回一次回答；
- 一张本地图片能被多模态模型或 BLIP 处理；
- `SenseVoice/demo1.py` 能正常转写示例音频；
- 若本次课要求 TTS，提前用 CosyVoice 生成一个 `.wav`。

## 2. 第 3 章 AnyGrasp

课前必须准备好：

- 与 Python 版本对应的 AnyGrasp SDK 二进制；
- 有效 License；
- detection checkpoint；
- 已编译 MinkowskiEngine；
- 官方 demo 能显示抓取候选。

若上实机，还要提前完成：

- RealSense RGB / Depth 检查；
- Dobot CR5 和 DH AG95 单独控制测试；
- 手眼标定结果可加载；
- `move.launch`、`anygrasp_ros.py`、`mover.py` 三段链路至少跑通一次。

## 3. 第 4 章仿真规划

### ALFWorld

```bash
alfworld-play-tw
```

至少进入一个任务并完成一次动作。

### AI2THOR

```bash
cd ~/EAI_project/chapter_4/4_1_task_planning/for_simulator/for_ai2thor
python demo_in_ai2thor.py
```

至少确认：场景打开、图像保存、模型返回动作、动作被环境执行。

### VirtualHome

提前确认 Unity 可执行程序路径和课程 demo 中的输出路径已针对实验机器修改。

## 4. 第 4 章实机规划

不要直接从“完整任务”开始联调。按以下顺序逐层检查：

1. 相机 RGB / Depth；
2. Qwen-VL 场景描述；
3. GroundingDINO 目标框；
4. 点云；
5. AnyGrasp 抓取位姿；
6. 单次机械臂抓取；
7. 大模型规划；
8. 完整闭环。

汉诺塔再额外检查规划输出是否始终满足“大盘不能放在小盘上”。

## 5. iGibson

检查：

```bash
nvidia-smi
nvcc --version
```

然后至少启动一次场景，确保资产下载完整。

## 6. ACT

仿真课前建议准备一个很小的数据集用于快速验证：

```bash
python3 record_sim_episodes.py \
  --task_name sim_transfer_cube_scripted \
  --dataset_dir ./smoke_data \
  --num_episodes 2 \
  --onscreen_render
```

确认 `visualize_episodes.py` 可以打开数据，再准备正式 50 条数据实验。

实机课前确认 CAN/USB 映射、主从臂、三个相机话题和 `collect_data.py` 均可用。
