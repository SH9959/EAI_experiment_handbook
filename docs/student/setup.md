# 开始实验前

## 1. 选对终端

| 命令块标注 | 使用的终端 | 多行命令续行符 |
|---|---|---|
| `bash` | 对应实验的 Linux Bash | 行末反斜杠 |
| `powershell` | Windows PowerShell | 行末反引号 |
| `python` | Python 文件或明确要求的 Python 解释器 | 按代码原样保存 |

Git Bash 可以执行 Git 命令，但不能代替 Linux 仿真环境。需要 GPU、桌面或 ROS 的实验，先使用课程指定机器；具体条件见各实验页。

检查 Git；需要 Conda 的实验另检查 Conda：

```bash
git --version
conda --version
```

出现版本号即可。若提示找不到命令，先安装课程指定的 Git 或 Conda；机器已预装时直接使用。

## 2. 下载手册和配套代码

在自己的实验文件夹打开终端，执行：

```bash
git clone --branch feature/whr https://github.com/SH9959/EAI_experiment_handbook.git
cd EAI_experiment_handbook
```

已有副本时直接进入该目录。后文以 `docs/assets/` 或 `chapter_3/`、`chapter_4/` 开头的路径，都相对于这个目录。

```text
EAI_experiment_handbook/
├── docs/student/       # 学生说明
├── docs/assets/        # 配套脚本和示例结果
├── chapter_3/3_3_human_perception/3.3.3/SenseVoice/
└── chapter_4/4_1_task_planning/for_simulator/
    ├── for_ai2thor/
    └── for_virtualhome/
```

SenseVoice、AI2THOR 和 VirtualHome 的课程示例已随仓库提供。独立项目和仿真器按各实验页获取，无需再为这些课程文件克隆一份 `EAI_project`。

模型、SDK 授权、场景和实机工程需另行准备。先按[资源清单](verification.md)确认，再安装该实验的依赖；不同实验使用各自环境。

## 3. 填写路径并保存结果

- 命令中的“绝对路径”“你的模型名”等是待填写内容，先替换再运行。
- 路径有空格时保留引号；不要同时混用 Windows 盘符和 Linux 路径。
- 新开终端后，重新进入要求的目录并激活环境；使用 `ACT_PY`、`EAI_ROOT` 等变量时，先重新设置变量。
- 每次实验使用新的结果目录。失败日志也保留，重新运行时换目录。

API Key 按[对话实验](ch3-dialogue.md)配置到环境变量。Key、设备密码和私人输入不写入源码或报告。
