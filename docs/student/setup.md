# 开始实验前

这里只做所有实验共同需要的准备。**CUDA、ROS、仿真器、模型依赖请到对应实验页再安装。**

## 1. 准备 Git 和 Python 环境管理工具

确认 Git 已安装：

```bash
git --version
```

推荐使用 Conda 管理不同实验的 Python 版本：

```bash
conda --version
```

如果课程机器已经预装 Conda，直接使用即可。

## 2. 克隆课程代码

```bash
cd ~
git clone https://github.com/SH9959/EAI_project.git
cd EAI_project
```

以后更新课程代码：

```bash
cd ~/EAI_project
git pull
```

## 3. 认识目录

```text
EAI_project/
├── chapter_3/
│   └── 3_3_human_perception/3.3.3/SenseVoice/
└── chapter_4/
    ├── 4_1_task_planning/for_benchmark/
    │   ├── alfworld/
    │   └── alfred/
    └── 4_1_task_planning/for_simulator/
        ├── for_ai2thor/
        └── for_virtualhome/
```

其中 **SenseVoice、AI2THOR 课程示例、VirtualHome 课程示例** 在当前仓库中有实际文件；ALFWorld、ALFRED、VirtualHome 主项目来自各自官方仓库，具体安装方式见第 4 章实验页。

## 4. 不要把 API Key 写进代码

教材中的大模型实验需要 API Key。建议放在环境变量中，例如：

```bash
export DASHSCOPE_API_KEY="你的Key"
```

Python 中通过：

```python
import os
api_key = os.getenv("DASHSCOPE_API_KEY")
```

这样提交代码时不会把个人 Key 一并上传。
