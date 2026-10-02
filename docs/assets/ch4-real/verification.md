# 实机任务规划检查记录

检查日期：2026-10-01。本轮完成教材、上游目录和接口的只读核对，以及手册内嵌规划检查代码的离线验证；未运行模型、相机或机器人。

## 教材依据

阅读《具身智能导论-v2.0.pdf》4.4.2—4.4.3，印刷页 140—151，对应 PDF 第 158—169 页。抽取相关页全文，并渲染核对 PDF 第 159、160、168 页的场景图、示例和操作顺序。

| 教材位置 | 本页对应处理 |
|---|---|
| 图 4.23，141 页 | 图中方块自下而上为黄、蓝、红；按此建立离线输入和三步状态表 |
| 142—145 页，脚本 4.21—4.26 | 保留场景识别、规划、细粒度物体描述、定位、RGB-D 与抓取路线，补充逐阶段输入输出和观测检查 |
| 143、145 页的 `caminfo.D`；144 页脚本 4.23 的 `target_sizes=[img.shape]` | 与官方接口核对后指出内参和目标尺寸问题，未把教材片段包装成完整驱动 |
| 145—146 页，脚本 4.27 与故障建议 | 说明姿态阈值、翻转矩阵依赖坐标约定；保留逆解、碰撞和滑落排查 |
| 146、150—151 页 | 保留汉诺塔识别、规划、动作转写/解析和固定位姿路线；补充盘大小/顺序核查及各层高度 |
| 图 4.28，150 页 | 教材图为四盘；手册三盘七步例明确为离线练习，并验证检查器可接受四盘十五步计划 |

`scene_000.json`、`plan.json`、`checks.csv` 等文件约定、`pick_place` 协议、反例练习和内嵌 `check_hanoi.py` 是本手册补充。教材未提供这些同名文件。每次搬运后重新观测的顺序也为本页的执行检查安排。

## 本轮上游与接口核对

- 重新请求 [课程工程递归树](https://api.github.com/repos/SH9959/EAI_project/git/trees/main?recursive=1)，返回提交 `e6bb5d5de828b5d87834ea169b53c09b376d8b09`、`truncated: false`、81 个条目。该提交的 [`chapter_4/4_1_task_planning/for_real`](https://github.com/SH9959/EAI_project/tree/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_4/4_1_task_planning/for_real)只有 `.gitkeep`，未提供这两项实验的启动工程。此结论只针对本次可见的课程仓库提交，不推断其他位置没有材料。
- 读取 [ROS `sensor_msgs/CameraInfo.msg` 原始定义](https://raw.githubusercontent.com/ros/common_msgs/noetic-devel/sensor_msgs/msg/CameraInfo.msg)，核对 `D` 为畸变参数、`K` 为原图内参、`P` 为校正图投影矩阵及光学坐标系约定。ROS 文档站本次返回访问拒绝，因此使用官方仓库源文件。
- 阅读 [Transformers Grounding DINO 官方接口](https://huggingface.co/docs/transformers/model_doc/grounding-dino)，核对 `target_sizes` 的 `(height, width)` 顺序、后处理框格式以及当前文档的 `threshold` / `text_threshold` 参数。教材环境的实际处理器与依赖版本尚未取得，未宣称新旧接口可直接混用。
- 阅读 [Open3D RGBDImage 官方接口](https://www.open3d.org/docs/latest/python_api/open3d.geometry.RGBDImage.html)，核对深度缩放、截断及 RGB 转灰度开关。教材的 1.5 m 截断只是例值，实际深度单位和工作距离需要采集数据确认。

未重新核验其他实验页所列 SDK、模型或设备驱动，也未把其历史检查记为本轮结果。

## 离线验证

从本轮 `docs/student/ch4-real.md` 提取实际代码块，在仓库外临时目录执行。运行解释器为 Python 3.12.14；另用 AST 按 Python 3.9 语法解析。

| 检查 | 本轮结果 |
|---|---|
| 三个 JSON 示例 | 均可解析；方块状态、动作参数与表中三步更新一致 |
| 方块两个反例 | 初始取 blue 不满足栈顶条件；第二步指向 `place_red` 不满足对应空放置区条件 |
| 三盘七步、四盘十五步 | 内嵌检查代码退出码为 0，最终输出 `PLAN_VALID; robot_executed=false` |
| 空源柱、大盘压小盘、未知柱号、未达目标 | 均在预期位置拒绝，退出码非 0，没有输出 `PLAN_VALID` |
| 同源目标柱、空计划、非法初始堆叠、重复盘号、布尔盘号 | 均拒绝；共执行 11 个汉诺塔输入用例 |
| 五个二级标题 | 顺序与统一结构一致 |
| 文档完整性 | 两份 Markdown 的 UTF-8 与围栏配对正常；3 个本地文件链接存在；实验页 `git diff --check` 通过 |

以上检查验证符号规划和文档内代码，不验证相机识别、机械臂运动可行性或任务执行成功。未新增仓库内的机器人或模型运行入口。

## 未运行范围与恢复条件

| 范围 | 本轮状态 | 下一步所需材料 |
|---|---|---|
| Qwen-VL / Qwen-max | 未调用，未产生模型计划 | 课程模型账号/本地环境、实际调用入口和提示词；按本页保存原始回答并校验 |
| RealSense / GroundingDINO | 未采集、未推理 | 匹配的采集工程、图像/CameraInfo、模型权重与处理器环境 |
| AnyGrasp 候选与坐标变换 | 未推理、未实测 | SDK 授权、权重、手眼标定、TCP 和完整场景碰撞信息 |
| 方块和汉诺塔搬运 | 未运行 | 完整实机工程、固定放置区/柱位与层高表、驱动完成反馈及现场设备验证 |

学生复测应另记日期、设备、工程版本、实际输入和结果，不覆盖本轮“未运行”记录。
