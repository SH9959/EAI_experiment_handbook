# AnyGrasp 抓取：修订与验证记录

检查日期：2026-09-20。**教材/源码审阅和辅助工具离线验证已完成；AnyGrasp 推理、仿真抓取及实机实验未运行。**

## 证据来源

- 本次重新读取《具身智能导论-v2.0.pdf》印刷页 79—96（PDF 第 97—114 页），并查看页面图像。
- 在已有手册仓库的 `feature/whr` 上修订，起点为 `7a9b42600858b3dd15edc889e3f0b98f13fc0fe0`，保留第一个实验的文件和提交。原抓取页 blob 为 `69f410ace0e65f34344089f77a21dc3b02bf42da`，与附件 manifest 匹配。
- 候选包 `checks/` 记录的是附件作者在 Linux、Python 3.13.5 下运行 22 项测试的结果。本次先审阅候选并补充回归测试，再在下述 Windows 环境重新执行；两者不是同一次运行。包内预览不是 MkDocs 构建产物，没有作为部署目录提交。
- 只读核对课程工程 [EAI_project 固定提交](https://github.com/SH9959/EAI_project/tree/e6bb5d5de828b5d87834ea169b53c09b376d8b09) 的完整递归树，未找到 `grasp_sim_anygrasp.py`、`anygrasp_model.py` 或 `anygrasp_open`。教材另引的 `SH9959/EAI.git` 完整工程本次未取得；不能据此断言其他位置也没有资料。
- 当前 SDK 固定提交为 `b8eaafc9eca7babd5208e7a5ade3c561060be4c5`；核对了 [README](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/README.md)、[授权说明](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/license_registration/README.md)、[检测 demo](https://github.com/graspnet/anygrasp_sdk/blob/b8eaafc9eca7babd5208e7a5ade3c561060be4c5/grasp_detection/demo.py)。对应 blob 分别为 `0e965aeb45d39038696f142097a9f2eccfdb9c62`、`ab65be1e2fc71b2543db212f70fb7634e655dd86`、`de8840f64e4a7d56bfea872aa52c0898069bf2ae`。

## 问题与处理

| 编号 | 核对结果 | 本次处理与边界 |
|---|---|---|
| G01 | 新 SDK 使用 `get_feature_id` / `check_license` 和 `create_detector`，与教材旧 `license_checker -f` 不同 | 保留旧路线，单列当前上游接口适配；未申请或验证授权 |
| G02 | 二进制、Python ABI、CPU 架构和编译依赖必须匹配；当前主分支面向 Linux x86_64 | 固定 SDK 提交，列出安装停止点；未形成实测锁定环境 |
| G03 | 当前 demo 还需 `seg_mask.png`，可视化参数为 `--vis` | 列明输入、终端/窗口输出和自行留存记录；退出码 0 不能单独证明有有效候选 |
| G04 | SDK 的权重另行提供，教材复制目录命令不完整 | 优先在原 SDK 目录运行；没有以空文件或 LFS 指针代替模型 |
| G05 | 教材 view 存储及“左乘”措辞有歧义 | 按列向量、列主序 view 和右乘坐标翻转说明；补充主点、FOV 弧度及显示镜像与刚体变换的区别 |
| G06 | 课程仿真入口、模型包装和 ROS 工程缺失 | 明确待补文件及坐标定义；没有编造替代抓取结果 |
| G07 | 原手册误写相机与标定板相对固定 | 改为相机相对基座固定、标定板相对末端固定；说明棋盘格数、内角点数与实测边长 |
| G08 | ROS1 步骤混入 ROS2 仓库，路径/launch 包名也不一致 | 保留设备路线，要求匹配工程；补充放置后的退离/抬起，不擅自换驱动 |
| G09 | 候选检查工具把空/LFS `gsnet.so` 当作已存在，按 Python 前缀匹配可能选错架构 | 检查文件状态、完整扩展后缀及授权包各类文件；匹配但未复制的二进制仍返回阻塞 |

`grasp_checks.py` 是新增的资料和解析几何辅助工具，不是 SDK 或课程仿真程序。工具系偏移、标定验收和抓取结果判据是补充说明，不冒充教材原有完整代码。

## 本轮实际执行

执行者：Codex，通过当前 Windows PowerShell 工作区运行；Python **3.12.5**。这不是学生自行操作的记录，也不是 Linux SDK 环境。以下命令均从手册仓库根目录执行，测试只使用标准库。

```text
python docs/assets/ch3-grasp/test_grasp_checks.py
Ran 30 tests
OK
```

30 项测试覆盖深度换算、FOV/主点、反投影、非平凡旋转和平移、列主序 view、镜像/非正交拒绝，以及缺文件、空文件、LFS 指针、平台/ABI、分割输入和授权包检查。文件测试使用临时合成文件，不是真实权重或 License。

| 命令 | 实际观察 | 验证范围 |
|---|---|---|
| `python docs/assets/ch3-grasp/grasp_checks.py geometry` | 返回 0，输出 `ANALYTIC_EXAMPLE_NOT_GRASP`；中心点为 `[0, 0, 1]` | 解析例子，不是抓取候选 |
| `python docs/assets/ch3-grasp/grasp_checks.py files` | 返回 2，`PLATFORM_MISMATCH`；SDK/仿真路径为 `NOT_CHECKED`，推理为 `NOT_RUN`、机器人为 `NOT_STARTED` | Windows 与教材 Linux SDK 不匹配；未提供真实 SDK 路径，未检查其授权有效性 |

## 文档与提交范围检查

本轮对两项实验合计 5 个 Python 文件执行内存编译检查，对页面内 3 段 Python 示例做 AST 语法解析，均通过；这不等于已在教材 Python 3.9 或 SDK 环境运行。`git diff --check` 和 4 份相关 Markdown 的相对链接检查通过。

使用已有 MkDocs 1.6.1、Material 9.7.7 文档环境，在完整仓库构建到仓库外临时目录。输出 HTML 的中文、代码块、导航、本地资源及锚点由解析检查通过；本轮未做浏览器目视验收。没有新增图片，也没有提交附件 HTML 预览。

修改前基线构建和修改后构建均通过。两者都有 Material 关于未来 MkDocs 2.0 的提示，以及第一个实验两份辅助页未列入导航的 INFO；本次新增两份验证记录未列入导航的 INFO，均已从对应实验页链接进入。未发现新增文档 WARNING。Git 另提示 LF 将转换为 CRLF，未发现空白格式错误。

仅提交本实验页及配套脚本、测试和本记录；未修改 `site/`、部署工作流、课程工程或第一个实验。

## 未运行内容与最小复测条件

| 阶段 | 本次状态与缺项 | 下一条真实证据 |
|---|---|---|
| Linux SDK 安装和授权 | 未运行；当前工作环境没有 WSL，未提供可用 SDK、匹配二进制、checkpoint 和有效 License | 确定 Linux 机器和 CUDA/PyTorch/编译依赖，记录 SDK 提交、授权检查和模型加载结果 |
| 官方 detection | 未运行 | 使用该版本的 RGB、深度和分割样例，保存有效候选的终端输出及图像 |
| PyBullet 抓取 | 未运行；缺两份课程脚本和完整环境 | 文件到位后记录 RGB、原始深度、矩阵及方块被夹住抬起的视频 |
| 手眼标定与 CR5 抓取 | 未运行；未提供匹配 ROS 工程和可供本次使用的设备条件 | 由现场人员确认 CR5、AG95、D435i、棋盘及安全条件，再记录标定和分步执行 |

本次只做资料/环境检查和离线验证，没有下载权重、收集机器特征码、申请授权或控制机器人。未在已检查位置找到资源，不代表实验室没有这些资源；需由资料持有人确认。离线测试不能替代上述任何一项真实实验。
