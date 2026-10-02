# 导航实验核验记录

核验日期：2026-10-01。对应 `docs/student/ch4-navigation.md`，用于维护者复核源码与验证边界。

## 教材依据

《具身智能导论-v2.0》4.4.4，印刷页 151–154（PDF 页 169–172），要求在 iGibson 中完成交互式导航，给出 Python 3.8、`eai-eval`、`behavior_eval.utils.install_igibson_utils` 和 `behavior_eval.utils.download_utils`。教材没有给出导航控制器、任务调用和结果保存代码。本页增加的交互式导航回合属于教学补充。

## 固定源码依据

| 项目 | 固定版本与已核对内容 |
| --- | --- |
| EAI | [531c62f8df2cb392bdf1907923c76da41cad4fe6](https://github.com/embodied-agent-interface/embodied-agent-interface/tree/531c62f8df2cb392bdf1907923c76da41cad4fe6)，`setup.py` 声明 1.0.5；README 的安装路线与教材一致，CLI 未提供导航评测类型 |
| 安装与下载 | [安装器](https://github.com/embodied-agent-interface/embodied-agent-interface/blob/531c62f8df2cb392bdf1907923c76da41cad4fe6/src/behavior_eval/utils/install_igibson_utils.py)使用当前目录已有的 `iGibson`，否则递归克隆 EAI fork；[下载器](https://github.com/embodied-agent-interface/embodied-agent-interface/blob/531c62f8df2cb392bdf1907923c76da41cad4fe6/src/behavior_eval/utils/download_utils.py)下载场景、资产、密钥并调用 Git LFS |
| iGibson | [a4f6021c47d03612b429170b282e983aa916bdaf](https://github.com/embodied-agent-interface/iGibson/tree/a4f6021c47d03612b429170b282e983aa916bdaf)，`__init__.py` 和 `pyproject.toml` 声明 2.2.3；后者声明 Python 依赖，但不是完整锁文件 |
| 资源与版本 | [数据说明](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/docs/dataset.md)标注约 20 GB 压缩包、申请与密钥；[`__init__.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/__init__.py)检查资产与场景版本 `[2.0.6, 2.2.4)` |
| 官方入口 | [`env_int_example.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/examples/environments/env_int_example.py)支持 `main(headless=False, short_exec=False)`；短模式为一次最多 100 步的随机动作演示 |
| 交互任务 | [`turtlebot_interactive_nav.yaml`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/configs/turtlebot_interactive_nav.yaml)指定 `Rs_int`、`interactive_nav_random`、500 步、0.36 m 阈值；[`interactive_nav_random_task.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/tasks/interactive_nav_random_task.py)加载五个 YCB 对象并忽略其碰撞计数 |
| 观测与动作 | [`point_nav_fixed_task.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/tasks/point_nav_fixed_task.py)定义极坐标目标观测和初始 `geodesic_dist`；[`dd_controller.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/controllers/dd_controller.py)将线、角速度转换成轮速；归一化由 `robot_base.py` 配置 |
| 回合与终止 | [`igibson_env.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/envs/igibson_env.py)的 `reset` 返回观测，`step` 返回四项并记录 `collision_step`；[`point_goal.py`](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/igibson/termination_conditions/point_goal.py)按平面距离判定成功 |

源码中的 `get_termination()` 在 `task.step()` 更新路径长度之前调用，因此本页从逐步保存的位置自行计算完整回合路径长度和 SPL，而非直接复用可能少计末步距离的原生 `info['path_length']`。初始最短距离取 `env.task.geodesic_dist`，成功标记仍取上游任务的 `info['success']`。

## 检查范围

- 已完成：新教材相关章节文本核对；通过 GitHub API 固定两个提交；只读审阅以上源码、安装文档、`pyproject.toml` 和渲染 CMake 配置。
- 已通过的离线检查：唯一 Python 代码块共 73 行，通过 `ast.parse(feature_version=(3, 8))` 和 `compile()`；学生页五个二级标题顺序正确；两页代码围栏闭合、相对链接目标存在；`git diff --check` 未发现空白错误。没有导入仿真包或执行该示例。
- 未执行：创建 Conda 环境、构建 iGibson、下载约 20 GB 场景/模型与密钥、GPU 渲染、导航回合以及六回合策略比较。没有真实成功率、轨迹截图或性能结论。

`goal` 是本页给出的简单方位反馈控制器，没有训练过程和避障规划；不得将其等同于纯视觉导航或经过验证的策略。种子不足以保证跨机器、跨依赖版本的完全复现，实验必须保存实际起终点、配置和环境版本。

## 待实验机器验证

2026-10-01 本机资源检查：Windows 主机为 RTX 4060 Laptop GPU（8188 MiB 显存，驱动 566.24）；现有 Ubuntu 22.04 虚拟机分配 4 GB 内存，图形设备为 VMware SVGA3D，未直接使用主机 NVIDIA 显卡。主机显存达到上游最低要求，但尚未构建 iGibson 或验证渲染。交互场景、对象资产及密钥尚未配置，导航回合未运行。

按学生页依次检查：安装与依赖 → 资产版本与密钥 → 官方短示例 → 一次完整交互回合 → 六回合策略对比。任一阶段失败，记录命令、完整异常和当前环境，停止该阶段之后的结论填写。

CMake 3.x 限制用于兼容 `igibson/render/CMakeLists.txt` 中的 `cmake_minimum_required(VERSION 2.8.12)`；[CMake 4.0 变更说明](https://cmake.org/cmake/help/latest/release/4.0.html#deprecated-and-removed-features)确认已移除低于 3.5 的兼容策略。该限制和源码固定不是已验证的平台锁文件；Windows/Linux 的编译工具、GPU 驱动及传递依赖仍需实验机器验证。
