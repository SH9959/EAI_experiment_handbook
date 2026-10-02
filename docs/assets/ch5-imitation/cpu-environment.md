# ACT 独立 CPU 环境

先选择要检查的范围。复用已有 checkpoint 和参考输入时，无需重新采集、训练或执行 50 回合。

| 路线 | 用途 | 依赖与边界 |
|---|---|---|
| Windows 单输入 | 检查权重加载及一次动作预测与已保存 GPU 参考的差异 | Python 3.12、CPU 版 PyTorch；不启动仿真，不产生新的任务成功率 |
| Ubuntu 历史评估环境重建 | 准备与原 50 回合评估同版本的 Python 包和 OSMesa | Ubuntu 22.04 x86_64、Python 3.10；本页配置尚未通过干净环境安装验证 |

单输入入口为 [`run_act_cpu_reference.py`](run_act_cpu_reference.py)。完整评估的既有结果仍见[核验说明](verification.md)。环境检查、单输入推理与完整任务评估分别记录。

## Windows：只运行一个已有输入

[Windows 依赖文件](requirements-cpu-reference-windows.txt)固定 28 个包及其 wheel 的 SHA256，适用于 **CPython 3.12 / Windows x86_64**。其中 `torch==2.7.1+cpu`、`torchvision==0.22.1+cpu` 与 Ubuntu 历史版本不同。它只支持读取已有图像和关节状态进行一次动作预测，不安装仿真器。固定源中的 `policy.py` 和 DETR 模型还会导入 IPython 和 packaging，不能只装 PyTorch。

2026-10-02 已在新建的 Python 3.12.12 venv 中完成离线安装、`pip check` 和包路径检查，并用已有 best 与 GPU 参考完成 **1 次 CPU 前向推理、0 个仿真回合**，结果为 `SINGLE_INPUT_VERIFIED`。系统包继承关闭，未借用另一 venv；证据与数值误差见[本次验证记录](verification.md#cpu-reference-portable)。这不代表 Ubuntu 仿真环境重建或新的任务评估通过。

先领取配套 wheelhouse。以下在 PowerShell 中执行，替换前三个路径；基础 Python 必须是 3.12 的 64 位解释器：

```powershell
$ActBasePython = 'C:/绝对路径/python.exe'
$Handbook = 'C:/绝对路径/EAI_experiment_handbook'
$ActWheelhouse = 'C:/绝对路径/act-windows-cp312-wheelhouse'
$ActEnv = Join-Path (Get-Location) 'act-cpu-reference-01'
if (Test-Path -LiteralPath $ActEnv) { throw '请更换为新的环境目录' }
& $ActBasePython -I -m venv $ActEnv
if ($LASTEXITCODE -ne 0) { throw '创建 venv 失败，请保留错误' }
$ActPython = Join-Path $ActEnv 'Scripts/python.exe'
$ActRequirements = Join-Path $Handbook 'docs/assets/ch5-imitation/requirements-cpu-reference-windows.txt'
& $ActPython -I -m pip --isolated install --no-index --require-hashes --only-binary=:all: `
    --find-links $ActWheelhouse -r $ActRequirements 2>&1 |
    Tee-Object -FilePath (Join-Path $ActEnv 'install.log')
if ($LASTEXITCODE -ne 0) { throw '离线安装失败，查看 install.log 的缺包或哈希错误' }
& $ActPython -I -m pip --isolated check 2>&1 |
    Tee-Object -FilePath (Join-Path $ActEnv 'pip-check.log')
if ($LASTEXITCODE -ne 0) { throw '依赖检查失败' }
& $ActPython -I -m pip --isolated freeze --all |
    Set-Content -LiteralPath (Join-Path $ActEnv 'environment.txt')
```

不要加 `--system-site-packages`。继续检查环境继承关闭、发行包均来自新 venv、Torch 确为 CPU 构建：

```powershell
@'
from importlib import metadata
from pathlib import Path
import site
import sys
root = Path(sys.prefix).resolve()
assert sys.platform == 'win32' and sys.version_info[:2] == (3, 12)
assert sys.prefix != sys.base_prefix and not site.ENABLE_USER_SITE
assert 'include-system-site-packages = false' in (root / 'pyvenv.cfg').read_text().lower()
for dist in metadata.distributions():
    location = Path(dist.locate_file('')).resolve()
    assert location.is_relative_to(root), (dist.metadata['Name'], str(location))
import torch
import torchvision
import numpy
for module in (torch, torchvision, numpy):
    assert Path(module.__file__).resolve().is_relative_to(root), module.__file__
assert torch.__version__ == '2.7.1+cpu'
assert torchvision.__version__ == '0.22.1+cpu'
assert numpy.__version__ == '1.26.4'
assert torch.version.cuda is None and not torch.cuda.is_available()
print('独立 CPU 环境检查通过；尚未执行 ACT 推理。')
'@ | & $ActPython -I -
if ($LASTEXITCODE -ne 0) { throw '独立环境检查失败' }
```

这一步通过后，再从[单输入入口](run_act_cpu_reference.py)的 `--help` 查看参数，提供本页末尾列出的模型与参考材料。运行时间和输出目录必须有界；数值对照通过只证明这一个输入下的输出一致性。实际新环境安装、推理状态与日志见[验证记录](verification.md)，不能用本页的命令示例代替实测结论。

## Ubuntu：准备独立环境

[依赖文件](requirements-cpu-evaluation.txt)由[原采集环境快照](ubuntu-collection-environment-20261002.txt)加上真实 CPU 评估使用的 `torchvision==0.15.2+cpu`、`einops==0.8.0` 整理而来。历史安装日志还记录 `pip==24.3.1`、`setuptools==59.6.0`，因此补入这两个被普通 freeze 省略的安装工具。它是**待验证的固定版本清单**，没有完整 wheel 哈希锁，也不保证新机器可从现有缓存装齐。

先向课程维护者领取适用于 **CPython 3.10 / Linux x86_64** 的 wheelhouse。Windows 的 `cp312-win_amd64` wheel 不能用于这条路线。维护者应同时提供 wheel 文件的 SHA256 清单；不要把其他 venv 的 `site-packages` 复制或通过 `.pth`、`PYTHONPATH` 接入。

下面命令在 Ubuntu Bash 中执行。先替换两个目录；venv 和日志写入一个新目录，若目录已存在则更换名称：

```bash
set -euo pipefail
HANDBOOK="/绝对路径/EAI_experiment_handbook"
ACT_WHEELHOUSE="/绝对路径/act-linux-cp310-wheelhouse"
ACT_ENV_DIR="$PWD/act-cpu-clean-01"
test ! -e "$ACT_ENV_DIR"
test -d "$ACT_WHEELHOUSE"
python3.10 -m venv "$ACT_ENV_DIR"
ACT_PY="$ACT_ENV_DIR/bin/python"
"$ACT_PY" -I -m pip --isolated install --no-index --only-binary=:all: \
  --find-links "$ACT_WHEELHOUSE" \
  -r "$HANDBOOK/docs/assets/ch5-imitation/requirements-cpu-evaluation.txt" \
  2>&1 | tee "$ACT_ENV_DIR/install.log"
"$ACT_PY" -I -m pip --isolated check \
  2>&1 | tee "$ACT_ENV_DIR/pip-check.log"
"$ACT_PY" -I -m pip --isolated freeze --all > "$ACT_ENV_DIR/environment.txt"
```

`No matching distribution found` 表示 wheelhouse 缺包、版本不符或平台不符；保留 `install.log`，请维护者补齐。命令不会联网，也不会编译源码包。若 `python3.10 -m venv` 不可用，先由系统维护者准备 Ubuntu 的 `python3.10-venv`；不把旧 venv 改造成新环境。

安装完成后检查版本和包位置：

```bash
"$ACT_PY" -I - "$HANDBOOK/docs/assets/ch5-imitation/requirements-cpu-evaluation.txt" <<'PY'
from importlib import metadata
from pathlib import Path
import platform
import site
import sys

root = Path(sys.prefix).resolve()
assert sys.prefix != sys.base_prefix, '未使用独立 venv'
assert sys.platform == 'linux' and platform.machine() == 'x86_64'
assert sys.version_info[:2] == (3, 10), sys.version
assert not site.ENABLE_USER_SITE, '用户 site-packages 未禁用'
cfg = (root / 'pyvenv.cfg').read_text().lower()
assert 'include-system-site-packages = false' in cfg, cfg
for dist in metadata.distributions():
    location = Path(dist.locate_file('')).resolve()
    assert location.is_relative_to(root), (dist.metadata['Name'], str(location))
for line in Path(sys.argv[1]).read_text().splitlines():
    if not line or line.startswith('#'):
        continue
    name, expected = line.split('==')
    assert metadata.version(name) == expected, (name, metadata.version(name), expected)
for entry in sys.path:
    path = Path(entry).resolve()
    if 'site-packages' in path.parts or 'dist-packages' in path.parts:
        assert path.is_relative_to(root), ('借用其他环境', str(path))
import numpy
import torch
import torchvision
for module in (numpy, torch, torchvision):
    assert Path(module.__file__).resolve().is_relative_to(root), module.__file__
assert torch.version.cuda is None and not torch.cuda.is_available()
print('环境版本与包路径检查通过；尚未执行 ACT 推理或任务评估。')
PY
```

`distutils-precedence.pth` 等安装工具自己的文件不等于借用环境；关键是包实际来自当前 venv、系统包继承关闭。保留上面的输出和 `pip-check.log`，不要只记录“安装成功”。

## Ubuntu：OSMesa 系统依赖

只有读取已保存图像并预测动作时，不需要 MuJoCo 渲染。以后要重建历史仿真环境，还需系统库；pip 无法安装它们。

历史 Ubuntu 22.04 安装记录使用 `libosmesa6`（当时为 `23.2.1-1ubuntu3.1~22.04.4`）及 `libgl1-mesa-glx`（`22.0.1-1ubuntu2`），并由 apt 安装/更新配套 Mesa 库。这不是可直接套用到其他 Ubuntu 版本的系统锁。让系统维护者按本机发行版准备这两个包及其依赖，记录实际版本；本轮没有新安装这些系统库。

```bash
dpkg-query -W libosmesa6 libgl1-mesa-glx
MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa MPLBACKEND=Agg \
  "$ACT_PY" -I - <<'PY'
import ctypes
ctypes.CDLL('libOSMesa.so.8')
import mujoco
import dm_control
print('OSMesa 动态库及仿真包可导入；尚未验证渲染或 ACT 回合。')
PY
```

`libOSMesa.so.8` 缺失时停在系统库准备阶段；MuJoCo 导入成功也不能证明能渲染 ACT 场景。无可访问的 Ubuntu 环境、无系统权限或缺 wheel 时，记录具体缺项后继续做已有证据核验。

## 已有材料与仍需领取的文件

独立 venv 外还需：固定提交 `742c753c0d4a5d87076c8f69e5628c79a8cc5488` 的原源码 ZIP、`policy_best.ckpt`、对应的 `dataset_stats.pkl`、已有 ResNet-18 缓存、参考输入 NPZ、参考报告和训练验收报告。大文件未随手册发布；用单输入入口校验它们的身份后再推理。

2026-10-02 本机只读核对发现，旧任务宿主机 wheel 目录保留的 Linux 评估包只有以下两项；已重算哈希，与旧下载清单一致。这**不是完整 wheelhouse**。

| 文件 | SHA256 |
|---|---|
| `torchvision-0.15.2+cpu-cp310-cp310-linux_x86_64.whl` | `aae0be6883d2cd5a23cb544ee0928288a27df0455430ef9dd6e631c5464095f5` |
| `einops-0.8.0-py3-none-any.whl` | `9572fb63046264a862693b0a87088af3bdc8c068fde03de63453cbbde245465f` |

未在已检查的旧任务工作目录、当前工作目录、ACT 数据目录和下载目录中找到 Linux CPU torch wheel。历史日志证明它曾在 VM 内下载，不能据此认为 VM 的 pip 缓存仍完整。VM 访问恢复后应先检查其缓存与 apt 缓存，核对 wheel 元数据、平台和哈希，再决定是否需要外部下载。

本轮尚未验证 Ubuntu 干净安装、OSMesa 渲染或新的仿真回合。原有 50 回合评估的 `37/50`、平均回报 `490.26`、末步仍满足 `34/50` 保持为历史完整基线，不受上述环境准备检查影响。
