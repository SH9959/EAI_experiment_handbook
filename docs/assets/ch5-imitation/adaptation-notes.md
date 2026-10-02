# ACT 已完成基线的适配范围

本页用于查阅 2026-10-02 已完成的 **50 条示教 → 2000 轮训练 → 50 回合评估**所用改动。核对已有结果用[证据核验入口](verification.md#evidence-check-20261002)，无需应用补丁或重新训练。

两份补丁均来自实际运行记录，基于 ACT 固定提交 `742c753c0d4a5d87076c8f69e5628c79a8cc5488`。训练与评估使用不同源码副本，不要把两份补丁叠加到同一副本。

| 环节 | 实际配置 | 可查阅材料 |
|---|---|---|
| Windows GPU 训练 | Python 3.12.12；torch 2.7.1+cu118 / torchvision 0.22.1+cu118；NumPy 1.26.4；RTX 4060 Laptop | [实际环境快照](windows-training-environment-20261002.txt)、[DataLoader 补丁](windows-dataloader.patch) |
| Ubuntu 采集 | Python 3.10.12；torch 2.0.1+cpu；MuJoCo 2.3.7 / dm_control 1.0.14；OSMesa | [采集环境快照](ubuntu-collection-environment-20261002.txt) |
| Ubuntu CPU 评估 | 复用采集环境，另有 torchvision 0.15.2+cpu、einops 0.8.0；固定 best 和配套统计文件 | [评估源码补丁](cpu-evaluation.patch)、[评估版本与哈希](act-evaluation-20261002.json) |

Windows 训练另将 `constants.py` 的 `DATA_DIR` 设为实际数据根目录；这里不保留维护者机器的绝对路径，按[学生手册](../../student/ch5-imitation.md#31)设置自己的路径。DataLoader 补丁完整保留实际改动：两处 `num_workers=0`，移除 `prefetch_factor`。单进程与 Linux worker 的随机采样不保证逐位一致。Windows 环境虽然安装了 MuJoCo 3.1.6 / dm_control 1.0.20，本次只用它读取 Ubuntu 采集的数据训练，没有用这组版本重新采集。

CPU 补丁改动设备放置、严格加载 checkpoint、保存逐步轨迹/进度和停止处理，不改任务、奖励或动作处理。它适配的是 `eval_bc`；本次还由外部运行器完成 seed 1000、模型哈希校验、CPU/GPU 同输入比较、缓存限制及运行监督。**仅应用补丁不等于复现了本次整套运行。**

若要检查补丁是否匹配，在另行准备、无本地修改的固定提交副本中，选其中一份执行以下只读命令，将路径替换为自己的手册位置：

```bash
git apply --check "/手册绝对路径/docs/assets/ch5-imitation/windows-dataloader.patch"
```

评估副本则检查 `cpu-evaluation.patch`。`--check` 不写入源码、不加载模型，也不启动训练或仿真。

## 尚未交付的独立复现条件

实际 CPU 评估 venv 通过 `.pth` 复用另一采集 venv，以上采集快照不是独立评估环境锁。搬到新机器前，还需课程维护者提供独立环境配置（含 OSMesa 系统库）、参数化运行器及其配套清单；不能直接照搬旧机器的虚拟机作业脚本。已有 checkpoint、`dataset_stats.pkl`、ResNet-18 缓存和参考输入也需领取并核对哈希。

本次发布的是实际改动与资源边界，未重新运行长训练或评估，也未验证一套新的独立安装流程。原 Linux CUDA 路线和实机路线仍以[学生实验页](../../student/ch5-imitation.md)的条件与未验证范围为准。
