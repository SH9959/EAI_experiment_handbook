# 验证入口与资源清单

更新：2026-10-02。先选择要做的路线，再打开相应实验页。表中的“已验证”只对应列出的步骤；六项实验尚未全部实测完成。

| 实验 | 已验证范围 | 尚未验证 | 开始前需取得或确认 |
|---|---|---|---|
| [人机对话与多模态](ch3-dialogue.md) | 配套脚本的离线检查 | 真实文本/图像 API、BLIP、语音识别与合成、完整交互及本地大模型 | 课程模型名、地域、权限与额度；BLIP-base、SenseVoiceSmall/fsmn-vad、CosyVoice2 完整快照及版本 |
| [AnyGrasp 抓取](ch3-grasp.md) | 几何和文件检查 | AnyGrasp 推理、仿真与实机抓取 | 匹配 SDK、权重和本机授权；`grasp_sim_anygrasp.py`、`anygrasp_model.py`；实机另需 ROS 工程、标定和设备 |
| [仿真任务规划](ch4-planning.md) | ALFWorld 文字任务、AI2THOR 预设八步、VirtualHome 人工规则放置任务 | ALFWorld 视觉、ALFRED、AI2THOR/VirtualHome 模型自主规划 | 视觉依赖与 THOR；ALFRED `f91f4c0` 对应 `json_feat`、checkpoint 和历史环境；模型路线另需账号配置 |
| [实机任务规划](ch4-real.md) | 代码、规则与接口核对 | 抓取、搬运及真实设备闭环 | 完整 ROS 工程，CR5/AG95/D435i、设备负责人；相机内参、深度单位、坐标变换、TCP 与 IK 配置 |
| [iGibson 导航](ch4-navigation.md) | 固定源码和配置核对 | 场景加载、导航回合与策略比较 | iGibson 2.2.3 对应通用资产、`Rs_int` 场景，二者 `VERSION` 在 `[2.0.6, 2.2.4)`；合法密钥与可用渲染环境 |
| [ACT 模仿学习](ch5-imitation.md) | 原完整基线 50 条/2000 轮/50 回合，**37/50**；另通过 Windows 独立 CPU 环境的一次保存输入对照 | Ubuntu 独立环境安装与渲染、原 Linux CUDA 全流程、cobot-magic 实机 | 单输入需已有 best、stats、缓存、参考输入和报告；Ubuntu 需完整 Linux wheelhouse 与系统库；实机需实验台与设备配置 |

没有相应资源时，记录**停在哪一步、缺少哪项、由谁提供、版本如何匹配**，暂不填写成功率。模型授权、场景和实机配置向课程负责人领取；Key 和密码只在本机配置，不提交实验报告或 Git。

## 直接检查结果

- **ACT 完整基线**：[学生操作与结果](ch5-imitation.md#41)、[逐回合 JSON](../assets/ch5-imitation/act-evaluation-20261002.json)、[原始证据核验说明](../assets/ch5-imitation/verification.md#evidence-check-20261002)。37 回合曾达到奖励 4，其中 34 回合末步仍为 4；二者不能称为稳定夹持率。早期短训练失败记录继续保留。
- **ACT 独立 CPU 单输入**：[操作步骤](ch5-imitation.md#42-cpu)、[环境配置](../assets/ch5-imitation/cpu-environment.md)、[实测结果](../assets/ch5-imitation/cpu-reference-validation-20261002.json)。新环境未借用其他 venv，一次输出与保存的 GPU 参考通过数值比较；没有新回合或新成功率，Ubuntu 完整环境仍待验证。
- **VirtualHome**：按[仿真任务规划](ch4-planning.md#34-virtualhome)运行仓库内入口。检查执行反馈、目标实例关系、冰箱关门与未持握状态；原始动作失败或最终图缺失时不能记作任务通过。
- **ALFWorld / AI2THOR**：[实验步骤](ch4-planning.md)、[真实运行与失败恢复记录](../assets/ch4-planning/verification.md)。预设动作完成只验证对应任务，不证明模型能够自主规划。
- **其余实验**：[对话](../assets/ch3-dialogue/verification.md)、[抓取](../assets/ch3-grasp/verification.md)、[实机规划](../assets/ch4-real/verification.md)、[导航](../assets/ch4-navigation/verification.md)的记录分别说明已做检查、实际失败和待补条件。

仓库保留可公开的摘要、脚本与检查记录。ACT 全部 HDF5、checkpoint、原始轨迹及视频体积较大，不包含在 Git 中；向课程维护者领取后，按文件哈希核对。缺原件时只能检查摘要，不能声称已独立复核原始实验。

## 保存自己的记录

每次使用新的输出目录，保留命令、环境版本、完整日志、输入与结果文件。区分以下状态：

| 状态 | 可以得出的结论 |
|---|---|
| 参数/依赖/摘要检查通过 | 仅该项检查通过，尚未证明实验任务完成 |
| 仿真动作执行成功 | 继续检查最终目标；正常退出或 `Done` 不是目标判据 |
| 任务通过 | 对应路线的目标判据有实际状态与日志支持 |
| 任务失败 | 已运行，有明确失败反馈或目标未满足；保留失败材料 |
| `UNKNOWN` / 未执行 | 单列数量与原因；预定回合未齐或状态未核清时，不报告完整成功率 |
