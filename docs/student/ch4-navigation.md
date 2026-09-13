# 第 4 章：iGibson 具身导航

> 对应教材：**4.4.4 具身导航实验**。

## 实验目标

在 iGibson 交互式室内环境中完成导航实验，理解具身导航不仅是“从 A 点走到 B 点”，还需要机器人根据视觉观测在可交互环境中持续做决策。

## 1. 硬件与系统要求

教材给出的最低要求包括：

- Nvidia GPU，显存大于 6 GB；
- Nvidia Driver ≥ 384；
- CUDA ≥ 9.0；
- CMake ≥ 2.8.12；
- Python 3.8（教材后续安装流程使用）；
- Windows 10 或 Linux 环境。

先检查 GPU：

```bash
nvidia-smi
```

检查 CUDA：

```bash
nvcc --version
```

## 2. 按教材路线创建环境

```bash
conda create -n eai-eval python=3.8 -y
conda activate eai-eval
```

安装 EAI evaluation 包：

```bash
pip install eai-eval
```

或使用教材给出的源码方式：

```bash
git clone https://github.com/embodied-agent-interface/embodied-agent-interface.git
cd embodied-agent-interface
pip install -e .
```

安装 CMake：

```bash
conda install cmake
```

安装 iGibson：

```bash
python -m behavior_eval.utils.install_igibson_utils
```

下载资产：

```bash
python -m behavior_eval.utils.download_utils
```

## 3. 安装完成后先验证环境

不要直接开始写导航策略。先确认三件事：

1. Python 可以正常导入 iGibson / behavior_eval；
2. 仿真场景可以打开；
3. 摄像头观测和机器人运动可以更新。

只有这三步都正常，再开始导航任务。

!!! note "课程代码状态"
    当前 `SH9959/EAI_project/chapter_4/4_2_navigation` 目录尚未包含教材 4.4.4 的可运行脚本，因此本页严格使用教材给出的 `eai-eval + iGibson` 安装路线。
