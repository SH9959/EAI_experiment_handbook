# 实测范围与资源缺项

本页供助教安排机器、资源和复测；学生按[实验前检查](../student/verification.md)与各实验页操作。以下记录不代表所有学生机器或全部教材实验已通过。

| 实验 | 已有实测或检查 | 仍需完成 |
|---|---|---|
| [对话与多模态](../student/ch3-dialogue.md) | 配套脚本离线检查 | 真实 API、BLIP、语音、完整交互及本地大模型；缺课程配置与完整模型快照 |
| [AnyGrasp](../student/ch3-grasp.md) | 几何和文件检查 | SDK、权重、本机授权及课程脚本；模型推理、仿真和实机抓取 |
| [仿真规划](../student/ch4-planning.md) | ALFWorld 人工文字；AI2THOR 预设动作；VirtualHome 六步规则任务 | 模型自主规划、ALFWorld 视觉、ALFRED；缺匹配数据/checkpoint 与历史环境 |
| [实机规划](../student/ch4-real.md) | 源码、接口和规则检查 | ROS 工程、设备、负责人、标定和实际搬运 |
| [导航](../student/ch4-navigation.md) | 固定源码及配置核对 | 匹配资产、`Rs_int`、合法解密与渲染；场景加载和导航比较 |
| [ACT](../student/ch5-imitation.md) | Windows CUDA 训练＋Ubuntu CPU 评估适配，50 条/2000 轮/50 回合；另有 Windows 独立 CPU 单输入 | Ubuntu 独立安装/OSMesa、原 Linux CUDA 全流程和 cobot-magic 实机 |

## ACT 记录

完整基线按“回合中最高奖励达到 4”判定成功，37/50（74%），平均回报 490.26；其中 34/50 末步仍为 4。早期短训练的 0/1 失败保留在历史记录中，不能替代这组完整结果。

独立 Windows CPU 单输入使用全新 Python 3.12.12 venv、torch 2.7.1+cpu / torchvision 0.22.1+cpu。28 个包按 wheel 哈希离线安装，未通过 `.pth` 借用其他环境；一次预测与保存的 GPU 参考通过 `rtol=atol=1e-4`。这不包含新的仿真回合。

Ubuntu 独立配置已整理，干净安装和 OSMesa 渲染未验证；先恢复现有 VM 访问并盘点 Linux wheel 与系统缓存。

## 查看原始检查和失败记录

- [对话与多模态](../assets/ch3-dialogue/verification.md)
- [AnyGrasp](../assets/ch3-grasp/verification.md)
- [仿真规划](../assets/ch4-planning/verification.md)：VirtualHome 六步规则成功、空手放入失败和场景准备记录；不据此认定模型自主规划完成。
- [实机规划](../assets/ch4-real/verification.md)
- [iGibson](../assets/ch4-navigation/verification.md)
- [ACT](../assets/ch5-imitation/verification.md)：训练、完整评估、CPU 单输入和历史失败。

验收按[课堂验收表](grading.md)检查真实输出。安装、格式检查、预检和正常退出不计作任务成功；缺资源时保留具体停止点。
