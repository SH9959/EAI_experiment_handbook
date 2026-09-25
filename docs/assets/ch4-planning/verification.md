# 仿真任务规划：修订与验证记录

检查日期：2026-09-20。**本次完成教材/源码审阅和辅助逻辑离线检查；ALFWorld、ALFRED、AI2THOR、VirtualHome 的真实交互及模型实验均未运行。**

## 来源与归因

- 本轮重新读取《具身智能导论-v2.0.pdf》印刷页 133—140（PDF 第 151—158 页）并查看页面图像。页面保留教材三部分结构：ALFWorld、ALFRED、基于大模型的规划；第三部分包含 AI2THOR 和 VirtualHome。
- 在已有 `feature/whr` 上修订，起点为 `7a9b42600858b3dd15edc889e3f0b98f13fc0fe0`，保留第一个实验的文件和提交。原规划页 blob `1c11203c710ce3e28f62f4a096dd5523830e6313` 与附件 manifest 一致。
- 附件作者的 `checks/` 记录了 Linux、Python 3.13.5 下 32 项测试及静态预览；那不是学生本机或本轮 Codex 的执行结果。本次独立审阅、修订候选后重新测试，实际结果另列。未把附件 `preview/` 作为网站部署目录提交。

只读核对课程 [EAI_project 固定提交](https://github.com/SH9959/EAI_project/tree/e6bb5d5de828b5d87834ea169b53c09b376d8b09)：

- [AI2THOR demo](https://github.com/SH9959/EAI_project/blob/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/demo_in_ai2thor.py)，blob `836a98e382f12d7e2ea77aa10e28914c1dcd30ee`。
- [myController.py](https://github.com/SH9959/EAI_project/blob/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/myController.py)，blob `aadd9fd3fdbc8274ea2dbb28a70ef0ed9989b55c`。
- [action.json](https://github.com/SH9959/EAI_project/blob/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/action.json)，blob `189c5672cce57400c6858517def3987c4789630a`。
- 同目录 requirements.txt 固定 AI2THOR 5.0.0、DashScope 1.23.1，并含 Linux GPU 依赖；本轮未安装这些依赖。
- [VirtualHome demo](https://github.com/SH9959/EAI_project/blob/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_simulator/for_virtualhome/demo_in_virtualhome.py)，blob `421a754e91fca5688765afc7512bf002f7aa272a`。

另读取 [ALFWorld README](https://github.com/alfworld/alfworld/blob/master/README.md) 和[下载脚本](https://github.com/alfworld/alfworld/blob/master/scripts/alfworld-download)、[ALFRED README](https://github.com/askforalfred/alfred/blob/master/README.md)、[模型说明](https://github.com/askforalfred/alfred/blob/master/models/README.md)、训练/评测参数，以及 [VirtualHome README](https://github.com/xavierpuigf/virtualhome) 和 [setup.py](https://github.com/xavierpuigf/virtualhome/blob/master/setup.py)。这些公开材料核对不代表安装成功；可变分支更新后需要重新检查。

## 问题与修订

| 编号 | 问题 | 处理与证据边界 |
|---|---|---|
| P01 | `Done` 在技能表中，但没有对应控制器方法，原循环仍可能分发 | 主循环精确处理结束词；假控制器测试，不是 Unity 运行 |
| P02 | `split('-')` 截断含负坐标的完整物体 ID | 用 `partition('-')` 保留整个目标串 |
| P03 | 动作大小写、白名单与方法名不一致 | 映射到规范技能名，拒绝未知及重复技能 |
| P04 | 物体子串匹配可能选错对象，空列表取 `[0]` 会崩溃 | 精确 ID/类型匹配；重名要求完整 ID，空目标或接近姿态明确报错 |
| P05 | `'false' in str(False)` 漏掉失败；缺字段也不能当成功 | 检查布尔反馈，将失败信息送回下一轮；执行后反馈未知时停止并如实记录 |
| P06 | `Done` 和退出码不能证明目标实现 | 记录结束原因，`task_success` 保持 `NOT_EVALUATED` |
| P07 | ALFRED 教材目录、续行注释与实际预处理/模型输入不一致 | 统一根目录、`json_feat` 数据、checkpoint 与评测输出；标注数据准备调整，未训练或评测 |
| P08 | VirtualHome 教材 Python 3.9 与当前声明 ≥3.10 不符 | 保留历史 Unity 2.3.0 线索，要求匹配版本及连接样例，不修改版本声明绕过安装 |
| P09 | 课程实际脚本操作 cereal 且硬编码 ID，教材目标是 salmon | 从本轮图精确选 salmon/fridge；导图→候选计划→执行反馈→回读图的示例尚未实测 |
| P10 | 候选入口的格式错误可能不记录；截图失败会误记已执行动作 | 保留拒绝动作，区分执行状态未知与未执行，写盘失败不重复登记动作 |

`planning_checks.py` 和 `ai2thor_checked_demo.py` 是新增辅助工具/手册侧包装入口，未修改课程控制器或 EAI_project。步数限制、手动模式、发送开关和运行记录属于辅助修订，不是教材原代码已完整跑通的证明。当前演示含粗粒度动作和部分 `forceAction`，不能据此报告标准导航或任务成功率。

## 本轮实际执行

执行者：Codex，通过当前 Windows PowerShell 工作区运行；Python **3.12.5**。这不是学生自行操作的记录。以下命令从手册仓库根目录执行，使用标准库、合成场景图/metadata 和假控制器。

```text
python docs/assets/ch4-planning/test_planning_checks.py
Ran 47 tests
OK
```

47 项测试覆盖动作协议、负坐标 ID、精确目标、空接近姿态、布尔反馈、技能白名单、课程文件版本、VirtualHome 节点/状态和包含方向。其中主循环测试检查 Done 不分发、拒绝动作留档、失败反馈回传、执行状态未知时停止、截图失败不重复记录及退出释放；模型和模拟器由 Mock 替代。

| 命令 | 实际结果与范围 |
|---|---|
| `python docs/assets/ch4-planning/planning_checks.py action --text "PickupObject-Cup"` | 返回 0，输出 `FORMAT_ONLY`、`executed: false`、`task_success: NOT_EVALUATED` |
| 下方负坐标 ID 命令 | 返回 0，完整保留目标 ID，输出仍为 `FORMAT_ONLY` |
| `python docs/assets/ch4-planning/planning_checks.py action --text "Done-Cup"` | 返回 2，拒绝带目标的 Done |
| `python docs/assets/ch4-planning/ai2thor_checked_demo.py --help` | 正常列出参数 |
| `python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir chapter_4/4_1_task_planning/for_simulator/for_ai2thor` | 返回 0，输出 `CHECK ONLY`；使用手册仓库已有课程代码副本，仅校验两份文件的 Git blob 和技能表 |

负坐标 ID 的实际检查命令：

```powershell
python docs/assets/ch4-planning/planning_checks.py action --text "PickupObject-Cup|-00.25|+01.00|-02.00"
```

来源预检没有使用 `--run` 或 `--send`，不导入课程控制器，也没有启动 Unity、调用模型或验证任务成功。未修改本地课程副本。

## 文档与提交范围检查

本轮对两项实验合计 5 个 Python 文件执行内存编译检查，对页面内 3 段 Python 示例做 AST 语法解析，均通过。它们不代表教材 Python 3.9/仿真依赖环境已验证。`git diff --check`、4 份相关 Markdown 的相对链接及构建后 HTML 本地资源/锚点检查通过。

完整仓库使用已有 MkDocs 1.6.1、Material 9.7.7 环境构建成功，输出在仓库外临时目录；HTML 中文、代码块和导航由解析检查通过，本轮未做浏览器目视验收。修改前已有 Material 关于未来 MkDocs 2.0 的提示，以及第一个实验两份辅助页未列入导航的 INFO；本次新增两份验证记录未列入导航的 INFO，已分别由实验页链接进入。未发现新增文档 WARNING。Git 的 LF→CRLF 提示不是空白格式错误。

仅提交本实验页、两个辅助脚本、测试和本记录；未修改 `site/`、部署工作流或 EAI_project。抓取实验使用独立提交，第一个实验的修改保留。

## ALFWorld 下一条真实运行路线

本轮只读检查当前 Windows 主机：`wsl --list --verbose` 返回未安装 WSL；Conda 可用，列出的 8 个环境中未找到 ALFWorld；默认缓存候选位置和 `ALFWORLD_DATA` 环境变量未发现可用数据。检查范围不涵盖所有磁盘、远程 Linux 主机或实验室共享盘，不能认定它们没有资源。

优先在已确认的 Linux 环境运行人工 TextWorld 交互，无需模型 API Key。先确认机器、独立 Conda 环境、已有缓存和下载目录；没有现成 Linux 时，WSL 安装属于另一步准备，需要用户确认。本轮没有安装 WSL、创建新环境或下载数据。

当前官方默认下载器会获取三份游戏/JSON/PDDL 压缩包，合计 **143,407,869 字节**，以及 **177,877,450 字节**的 Mask R-CNN 权重，总计 **321,285,319 字节（约 321 MB）**；这些数字来自 [0.2.2 发布附件元数据](https://github.com/alfworld/alfworld/releases/tag/0.2.2)和 [0.4.2 发布附件元数据](https://github.com/alfworld/alfworld/releases/tag/0.4.2)，没有下载其内容。还需另计 Python 依赖、解压和环境空间，当前未测量其总量。只安装不带 `[full]` 的 Python 包，并不会让默认下载器跳过视觉权重。

下一轮集中确认：使用哪台 Linux 机器、是否可复用缓存、数据存放位置和空间，以及是否允许默认下载器包含的视觉权重。确认前不运行 `alfworld-download`，也不运行 `--extra`。完成准备后才执行文字交互，保存任务、输入动作、环境反馈及成功/失败消息。

## 未运行内容与最小复测条件

| 路线 | 当前状态 | 下一条真实证据 |
|---|---|---|
| ALFWorld TextWorld | 未运行，待确认 Linux/数据条件 | 人工完成一个任务的动作—反馈序列和 `you won` 或真实失败记录 |
| ALFWorld THOR | 未运行 | 文字路线后配置匹配渲染环境，记录图像、动作和结果 |
| ALFRED | 未运行 | 匹配历史依赖、数据与预训练模型，先真实评测，再决定是否训练 |
| AI2THOR 手动入口 | 仅来源预检和假控制器测试 | 确认 Unity 下载/显示条件后用 `--run --mode manual`，保存逐步图像及 metadata |
| AI2THOR LLM | 未运行 | 手动仿真通过，再确认合法 Key 和预算，使用 `--send`；核对动作反馈及最终目标 |
| VirtualHome 人工脚本 | 仅图/动作逻辑测试，连接与执行示例未实测 | 匹配 Unity/Python、连接样例和角色，导出含 salmon/fridge 的真实图后执行并回读 |
| VirtualHome LLM 扩展 | 未实现/未运行 | 另补受限动作协议、规划器和反馈；人工规则脚本不算模型成功 |

未调用收费 API、运行 Unity、训练模型或启动机器人。Mock、格式检查和 `PLAN_ONLY` 均不能写成真实平台实验通过。
