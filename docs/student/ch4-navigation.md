# 第 4 章：iGibson 具身导航

> 对应教材：**4.4.4 具身导航实验**（印刷页 151–154）。

## 一、实验目标

让 Turtlebot 在 iGibson 室内场景中导航到目标位置。分别运行随机动作和朝向目标的反馈控制，各做三个回合，比较成功率、路径长度和碰撞步数。

用 `eai-eval` 安装配套环境，再通过 `iGibsonEnv` 运行导航。第三节提供回合代码，无需训练模型或调用外部 API。

## 二、实验环境配置

### 2.1 系统与资源

在已启用 Conda 的终端中逐行执行命令；Windows 使用 Anaconda Prompt。

| 项目 | 要求与检查 |
| --- | --- |
| 系统 | 教材采用 Windows 10、Visual Studio 2017 的 C++ 工具和 Windows 10 SDK；Linux 需 C++ 编译器及 EGL 开发库 |
| GPU | 教材要求 NVIDIA 显存大于 6 GB、驱动 ≥ 384；执行 `nvidia-smi` 记录实际型号与驱动 |
| CUDA/cuDNN | 教材要求 CUDA ≥ 9.0、cuDNN ≥ 7；用 `nvcc --version` 检查编译工具，cuDNN 版本查对应安装目录的头文件 |
| Python/CMake | Python 3.8；CMake 从 Conda 安装。下文限制为 3.x，以适配此分支的旧 CMake 配置 |
| 资产 | iGibson 场景、机器人、YCB 对象和密钥；上游标注场景压缩包约 20 GB，还需预留解压空间 |
| 图形环境 | GUI 需要可用的桌面 OpenGL 上下文；无窗口模式仍需要受支持的 GPU 渲染环境 |

**先确认能取得交互场景、通用资产和密钥。仓库不包含这些文件；缺少其中一项就停在环境准备，无法运行导航。** 资源入口见 2.3。当前尚无本页六回合的实测结果，安装与 GPU 渲染需在实验机器上验证。

`nvidia-smi` 中的 CUDA 数字表示驱动支持能力，编译工具版本仍需用 `nvcc` 检查。编译器、驱动或渲染检查失败时，先按第五节排错。

### 2.2 安装教材指定的软件

在空的实验目录中安装下列固定版本：

```bash
mkdir ch4-navigation
cd ch4-navigation
conda create -n eai-eval python=3.8 -y
conda activate eai-eval
git clone https://github.com/embodied-agent-interface/embodied-agent-interface.git
cd embodied-agent-interface
git checkout 531c62f8df2cb392bdf1907923c76da41cad4fe6
python -m pip install -e .
conda install "cmake>=3.1,<4" -y
git clone --recursive https://github.com/embodied-agent-interface/iGibson.git
git -C iGibson checkout a4f6021c47d03612b429170b282e983aa916bdaf
git -C iGibson submodule update --init --recursive
python -m behavior_eval.utils.install_igibson_utils
python -m pip check
```

安装器使用当前目录下的 `iGibson`，因此必须先检出指定提交。后续命令均在 `embodied-agent-interface` 根目录执行；新开终端后先激活 `eai-eval` 并回到该目录。

### 2.3 准备资产并检查接口

先向教师领取已配置的资产路径，或通过[上游数据说明与申请入口](https://github.com/embodied-agent-interface/iGibson/blob/a4f6021c47d03612b429170b282e983aa916bdaf/docs/dataset.md)取得使用资格及密钥。自行下载时，确认磁盘空间与网络可用，再执行：

```bash
git lfs version
python -m behavior_eval.utils.download_utils
python -c "import igibson, behavior_eval; from igibson.envs.igibson_env import iGibsonEnv; print('iGibson:', igibson.__version__); print('source:', igibson.__file__); print('assets:', igibson.assets_path); print('dataset:', igibson.ig_dataset_path); print('key:', igibson.key_path)"
```

出现许可提示时阅读并作答。使用实验室资产时，跳过下载命令，在 `igibson/global_config.yaml` 中填入教师提供的路径，再执行上面的导入检查。资产和场景的 `VERSION` 均须处于 `[2.0.6, 2.2.4)`；缺少版本文件时检查资源完整性。

导入检查应显示 iGibson `2.2.3`，且来源为上述检出的目录。保存环境记录：

```bash
python -m pip freeze > navigation-environment.txt
git rev-parse HEAD > navigation-eai-commit.txt
git -C iGibson rev-parse HEAD > navigation-igibson-commit.txt
```

## 三、实验过程

### 3.1 运行官方环境示例

先运行一个短回合，检查场景、摄像头和动作接口：

```bash
python -c "from igibson.examples.environments.env_int_example import main; main(short_exec=True)"
```

应看到 `Rs_int` 室内场景与 Turtlebot 运动，最多 100 步后窗口关闭。这一步检查仿真能否工作，导航是否到达目标需看下一步的结果。

在已经配置 GPU 无窗口渲染的机器上，可改为 `main(headless=True, short_exec=True)`。若示例无法创建环境，保存完整报错并按第五节处理，暂不进入下一步。

### 3.2 运行交互式导航回合

本实验使用上游配置 `igibson/configs/turtlebot_interactive_nav.yaml`：

| 参数或接口 | 本实验含义 |
| --- | --- |
| `scene_id: Rs_int` | 有家具和交互对象的室内场景 |
| `task: interactive_nav_random` | 随机采样起点与目标，额外加载五个可移动 YCB 对象 |
| `task_obs` | 目标在机器人坐标系中的距离、方位角，以及当前线速度、角速度 |
| `rgb`、`depth`、`scan` | 视觉与激光观测；深度和激光输出经过归一化，不能直接按米解读 |
| 动作 | 两维归一化命令 `[前进, 转向]`，由差速控制器转换成轮速 |
| 终止 | 到达目标、超出碰撞限制、越界或达到 500 步；到达阈值为平面距离小于 0.36 m |

使用[配套程序](../assets/ch4-navigation/navigation_trial.py)，从手册仓库复制到当前 `embodied-agent-interface` 根目录。替换命令中的手册绝对路径；已有同名脚本时先保留旧文件，不覆盖自己的修改。

**Linux Bash：**

```bash
cp -i "/绝对路径/EAI_experiment_handbook/docs/assets/ch4-navigation/navigation_trial.py" ./navigation_trial.py
```

**Windows Anaconda Prompt：**

```bat
copy /-Y "C:\绝对路径\EAI_experiment_handbook\docs\assets\ch4-navigation\navigation_trial.py" navigation_trial.py
```

程序正常结束时保存完整回合；异常时保存错误日志和已确认步骤。先运行 `random`，再运行 `goal`。

执行：

```bash
python navigation_trial.py 0 random
python navigation_trial.py 0 goal
```

代码沿用旧 Gym 接口：`reset()` 返回观测字典，`step()` 返回四项 `(state, reward, done, info)`。不要直接套用 Gymnasium 的五返回值示例。无窗口运行时，将复制后的 `navigation_trial.py` 中的 `mode="gui_interactive"` 改为 `mode="headless"`，仍会保存首末 RGB 图像。

`goal` 根据模拟器给出的目标方位转向，方位误差小于 0.25 rad 时前进，**没有避障能力**。保留卡住和失败的回合，观察目标方向正确时为何仍会碰到家具。这是目标位置反馈控制，未使用图像预测动作。

### 3.3 比较多次运行

前两个回合完成后，运行其余四个回合：

```bash
python navigation_trial.py 1 random
python navigation_trial.py 1 goal
python navigation_trial.py 2 random
python navigation_trial.py 2 goal
```

同一种子的两份 `result.json` 中，先核对 `start` 和 `target` 是否一致，再比较轨迹和碰撞。场景或起终点不同的回合分开记录。已有结果目录会触发 `FileExistsError`；重试前归档旧目录，保留失败记录。

选做：增加深度或激光避障，保留原两种策略的结果，用相同场景和终止条件比较。

## 四、实验结果

正常结束的回合应生成 `config.json`、`start.png`、`end.png`、`trajectory.npz`、`result.json` 和 `run.log`。`trajectory.npz` 的 `xy` 包含初始位置和每步执行后的位置，行数应比 `actions` 多一。

异常退出时，查看 `run.log` 的完整错误栈和 `result.json` 的 `errors`。此时 `status=ERROR`、`completed=false`、`success=null`，进程返回非 0；已确认步骤保存为 `trajectory_partial.json`。`unconfirmed_action.outcome` 为 `UNKNOWN` 时，动作是否执行尚不明确；为 `STEP_RETURNED` 时，环境已返回反馈，但后续观测或数值检查未通过，已收到的 reward、done、info 保存在 `feedback_repr`。两者都不算完整步骤，不要盲目重发。非有限值以字符串留在错误记录中，关闭环境失败也不记为完整回合。

| 记录项 | 判读方式 |
| --- | --- |
| `status` / `completed` | 仅 `COMPLETE` / `true` 的回合进入成功率统计；`ERROR` 单列为运行故障，修复后保留旧目录重试 |
| 环境验证 | 官方示例可运行，观测存在且随动作更新；保存依赖和两个源码提交记录 |
| `done` | 回合是否终止；终止不等于成功 |
| `success` | 采用上游任务判据；到达目标时为 `true`，不能用程序无报错代替 |
| `final_distance_m` | 最终平面欧氏距离；到达判据为小于 0.36 m |
| `collision_steps` | 有有效碰撞的仿真步数，不是碰撞对象数；该任务主动忽略额外 YCB 对象的碰撞 |
| `path_length_m`、`spl` | 由保存的完整轨迹计算路径长度 P，以初始最短路径 L 计算 `S * L / max(L, P)`，其中 S 为成功标记 |

按策略分别报告尝试数、完整回合数、运行故障数，再汇总完整回合的成功率、平均 SPL、平均步数及平均碰撞步数。成功率写成“成功数 / 完整回合数”，不足三回合时注明；没有完整回合时不填写成功率。随机策略全部失败也应如实保留，不能更换种子只选成功回合。若安装或渲染阶段未通过，提交环境信息、失败命令和完整日志，填写“未进入导航仿真”。

实验报告至少包含一组首末图像、结果表和失败分析。说明反馈控制相比随机动作改善了什么，以及为何仅朝向目标仍不能解决障碍绕行。

## 五、排错建议与注意事项

| 现象 | 检查与处理 |
| --- | --- |
| CMake、编译器或 CUDA 编译失败 | 确认 Python 3.8 环境已激活，CMake 来自 Conda；检查 `nvcc`、Windows C++/SDK 或 Linux EGL 开发库。若使用了 CMake 4，恢复本页的 3.x 范围后重新构建 |
| `No module named behavior_eval/igibson` 或来源不符 | 用 `python -m pip show eai-eval igibson` 核对当前环境，确认使用指定源码安装并执行 `python -m pip check` |
| 资产缺失、`VERSION` 报错或解密失败 | 核对打印出的资产、场景和密钥路径；检查下载是否完整、版本是否匹配以及密钥授权，不要仅新建空目录绕过检查 |
| 缺少 Turtlebot 或 YCB 模型 | 检查通用 `assets`，不能只下载场景；仅有静态 `Rs` 演示场景不能运行本实验的 `Rs_int` |
| GUI 黑屏、EGL/OpenGL 或渲染器加载失败 | 先运行官方短示例并保存日志；核对 GPU 驱动和桌面/远程渲染配置。`headless` 只去掉窗口，不能弥补缺少渲染支持 |
| `reset` 失败或无法采样有效位置 | 核对场景、可通行地图和完整资产；检查起终点采样警告，不能在未加载场景时直接修改坐标继续 |
| 动作维度或返回值数量不符 | 核对 iGibson 提交、`turtlebot_interactive_nav.yaml` 和实际导入路径，恢复本页的两维动作、四项返回值接口 |
| `goal` 碰墙、原地转向或超时 | 先对照目标方位、轨迹与观测定位问题，再增加避障或路径规划；这不是重新安装环境的依据 |

接口版本与已做检查见[导航实验核验记录](../assets/ch4-navigation/verification.md)。
