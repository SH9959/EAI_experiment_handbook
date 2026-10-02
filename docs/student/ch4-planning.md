# 第 4 章：仿真任务规划

对应教材 **4.4.1 在仿真环境上的规划实验**，印刷页 133—140（v2.0 PDF 第 151—158 页）。

## 一、实验目标

根据任务目标、场景状态和执行反馈选择动作，记录执行结果，并检查最终目标是否达成。

| 教材部分 | 实验任务 | 模型 API 条件 |
|---|---|---|
| ALFWorld 交互体验 | 人工在 TextWorld 里选择动作，完成一个环境任务 | 不需要；首次安装和下载数据仍需网络 |
| ALFRED 小模型测试 | 加载 Seq2Seq/LSTM 模型，在对应 THOR 环境评测 SR/GC 等 | 不需要云端 API，但需要模型、数据和兼容运行环境 |
| AI2THOR 大模型演示 | 图像/状态 → 大模型动作 → 执行 → 反馈 | 原课程示例需要 DashScope Key；可先独立检查仿真器 |
| VirtualHome | 先执行“把三文鱼放入冰箱”的人工脚本，再尝试模型规划 | 人工脚本不需要；模型路线另需规划器 |

先完成 ALFWorld 文字任务，再按课程安排选择其余路线。各路线分别验收；人工规则任务通过后，才能继续检查模型生成的计划。

## 二、实验环境配置

本页 Bash 命令在课程 Linux 机器或已确认兼容的 WSL 环境中执行；VirtualHome 另提供 Windows PowerShell 步骤。Git Bash 不能替代 Linux 仿真环境。各工程使用独立环境，放在手册仓库旁的实验目录中。

| 路线 | 平台与依赖条件 | 资源条件 |
|---|---|---|
| ALFWorld 文字交互 | Ubuntu 22.04、Python 3.10、独立 venv | 三份文字任务数据包；无需模型 API |
| ALFWorld 视觉交互 | 匹配的 THOR 和图形/显示环境 | 视觉依赖和 THOR 程序 |
| ALFRED | 兼容的历史 PyTorch、torchvision、AI2THOR；本页命令使用 GPU | 数据和预训练模型 |
| AI2THOR | Ubuntu 22.04、Python 3.10、AI2THOR 5.0.0、Unity 图形环境 | THOR 程序；大模型模式另需 SDK、模型权限和额度 |
| VirtualHome | 本页人工路线使用 Windows、Python 3.12、官方 Unity 通信模块 | Unity 2.3.0 Windows 程序 |

先确认机器、磁盘空间和已有缓存，再安装所选路线；ALFRED 与 AI2THOR 5.0.0 的依赖分开配置。

### 2.1 基础检查

从**手册仓库根目录**运行，需要 Python 3.9 或更高版本，无需安装仿真器或模型依赖：

```bash
python --version
python docs/assets/ch4-planning/planning_checks.py action --text "PickupObject-Cup"
```

第二条应输出 `FORMAT_ONLY`、`executed: false` 和 `task_success: NOT_EVALUATED`。这一步只检查动作格式，后续还要在场景中执行。

### 2.2 ALFWorld 环境

教材使用 Python 3.9 和 `alfworld[full]`。以下文字路线使用 Ubuntu 22.04、Python 3.10、[固定 ALFWorld 源码](https://github.com/alfworld/alfworld/tree/aaba6870f86c5be6a08a491f32a50b906227bc3e)和 TextWorld 1.6.2；视觉路线见 3.1.2。

从独立的实验父目录打开 Bash。下面新建 `eai-alfworld`；若已有同名目录，换一个新名称，不覆盖原环境。缺少系统依赖时先安装：

```bash
sudo apt-get update
sudo apt-get install -y python3.10-venv python3.10-dev build-essential libffi-dev curl util-linux
```

建立并激活环境，后续步骤在同一个终端执行：

```bash
set -e
mkdir eai-alfworld
cd eai-alfworld
python3.10 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
curl --fail --location --output alfworld-source.zip https://github.com/alfworld/alfworld/archive/aaba6870f86c5be6a08a491f32a50b906227bc3e.zip
python -m zipfile -e alfworld-source.zip .
python -m pip install ./alfworld-aaba6870f86c5be6a08a491f32a50b906227bc3e "textworld==1.6.2"
python -m pip check
python -c "from importlib.metadata import version; print('alfworld', version('alfworld')); print('textworld', version('textworld'))"
```

下载三份文字任务包，共约 143 MB；依赖和解压另占空间。本路线不使用会同时下载视觉权重的 `alfworld-download`。

```bash
mkdir downloads data
export ALFWORLD_DATA="$PWD/data"
curl --fail --location --output downloads/json_2.1.1_json.zip https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_json.zip
curl --fail --location --output downloads/json_2.1.1_pddl.zip https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_pddl.zip
curl --fail --location --output downloads/json_2.1.3_tw-pddl.zip https://github.com/alfworld/alfworld/releases/download/0.4.2/json_2.1.3_tw-pddl.zip
for archive in downloads/*.zip; do
  python -m zipfile -e "$archive" "$ALFWORLD_DATA"
done
```

重新打开终端时，先进入自己的 `eai-alfworld` 目录，运行 `source venv/bin/activate` 和 `export ALFWORLD_DATA="$PWD/data"`，再继续实验。

### 2.3 ALFRED 环境与数据

ALFRED 使用视觉特征和历史环境：固定源码列出 PyTorch 1.1.0、torchvision 0.3.0、AI2THOR 2.1.0。**目前缺少经过验证的完整环境锁文件，本路线尚未跑通。** 已有课程环境时先核对这三个版本和 GPU；没有兼容环境时停在此处，记录缺少的环境材料，不在 AI2THOR 5.0.0 环境中降级依赖。

```bash
# 从独立实验父目录开始，不在手册目录内部下载模型。
git clone https://github.com/askforalfred/alfred.git
cd alfred
git checkout f91f4c0c96c7a29f33d0557f86b0a21035379b3b
export ALFRED_ROOT="$PWD"
git rev-parse HEAD
```

激活兼容的专用环境，从 `$ALFRED_ROOT` 执行 `python -m pip install -r requirements.txt`，再运行 `python -m pip check`。本页使用官方 quickstart 的 `json_feat_2.1.0`，包含轨迹和预提取视觉特征，下载约 17 GB；仅有教材的 `json_2.1.0` 轨迹 JSON 不足以直接使用以下命令。优先复用同版本数据；需要下载时执行：

```bash
cd "$ALFRED_ROOT/data"
bash download_data.sh json_feat
cd "$ALFRED_ROOT"
```

按官方 `models/README.md` 下载其 Seq2Seq+PM checkpoint，解压后定位实际的 `best_seen.pth`，供后续评测使用。

```bash
# 工作目录：$ALFRED_ROOT；下载前确认额度。
wget https://ai2-vision-alfred.s3-us-west-2.amazonaws.com/seq2seq_pm_chkpt.zip
unzip seq2seq_pm_chkpt.zip
find . -name best_seen.pth
```

新终端中重新激活 ALFRED 环境、进入 `alfred` 目录并执行 `export ALFRED_ROOT="$PWD"`。缺少 `json_feat_2.1.0`、`best_seen.pth` 或匹配的 THOR 程序时，先补齐对应资源，再进入 3.2。

### 2.4 AI2THOR 环境与课程代码

使用本仓库 `chapter_4/4_1_task_planning/for_simulator/for_ai2thor/` 中的课程文件，无需另行克隆工程。[配套入口](../assets/ch4-planning/ai2thor_checked_demo.py)会核对这些文件是否匹配课程提交 `e6bb5d5de828b5d87834ea169b53c09b376d8b09`。任务为“把装有餐刀的杯子放在厨房台面”，场景为 `FloorPlan10`。

在 Ubuntu 22.04、Python 3.10 中建立独立环境。Unity 需要可用的桌面会话和 OpenGL；缺少 `venv` 时先执行 `sudo apt-get install python3.10-venv`。环境目录已存在时，激活原环境或换一个新名称。

```bash
mkdir -p "$HOME/eai-lab"
python3.10 -m venv "$HOME/eai-lab/eai-ai2thor/venv"
source "$HOME/eai-lab/eai-ai2thor/venv/bin/activate"
python -m pip install pip==24.3.1
python -m pip install ai2thor==5.0.0 numpy==1.26.4 opencv-python==4.10.0.84 Flask==2.1.1 Werkzeug==2.0.3 Pillow==11.0.0
python -m pip check
python -c "from ai2thor.controller import Controller; import ai2thor._builds; print(ai2thor._builds.COMMIT_ID)"
python -m pip freeze > "$HOME/eai-lab/eai-ai2thor/environment-manual.txt"
```

构建编号应为 `f0825767cd50d69f666c7f282e54abfe58f1e917`。新终端先运行上面的 `source` 命令。

VMware 中如需使用 Mesa 软件渲染，在当前 Bash 执行 `export LIBGL_ALWAYS_SOFTWARE=1`；已有正常 GPU 渲染的机器不需要此设置。无桌面显示会话时，先完成图形环境配置。

回到**手册根目录**，检查课程文件：

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir chapter_4/4_1_task_planning/for_simulator/for_ai2thor
```

应输出 `CHECK ONLY`。不加 `--run` 只检查文件与动作表；若提示版本不符，核对 `myController.py`、`action.json` 的本地修改。

### 2.5 VirtualHome 环境与连接

以下人工路线使用 Python 3.12 和[固定版本源码](https://github.com/xavierpuigf/virtualhome/tree/58970fd80951c2eaa1af713e0917d1a105353ad8)中的 Unity 通信模块。在独立实验目录打开 PowerShell：

```powershell
conda create -n eai-virtualhome python=3.12 -y
conda activate eai-virtualhome
git clone https://github.com/xavierpuigf/virtualhome.git
git -C virtualhome checkout 58970fd80951c2eaa1af713e0917d1a105353ad8
python -m pip install numpy==1.26.4 opencv-python-headless==4.8.1.78 Pillow==11.3.0 requests==2.32.5
python -m pip install certifi==2025.8.3 charset-normalizer==3.4.3 idna==3.10 urllib3==2.5.0
python -m pip check
```

已有源码时跳过克隆并核对提交。此路线直接导入 `unity_simulator`，无需运行 `pip install -e .` 安装整包。

从[官方下载页](https://github.com/xavierpuigf/virtualhome#download-unity-simulator)下载 Unity 2.3.0 Windows 程序，解压到同一实验目录。包约 289 MB，解压后应有 `windows_exec.v2.3.0/VirtualHome.exe`。在该实验目录启动并保留程序：

```powershell
& ".\windows_exec.v2.3.0\VirtualHome.exe" -http-port=8080 -screen-fullscreen 0
```

另开 PowerShell，激活 `eai-virtualhome` 并回到上述实验目录，再执行 3.4。若端口被占用，同时更改启动参数和 Python 连接端口。教材任务使用 `salmon`，物体编号从当前场景图读取。

## 三、实验过程

### 3.1 ALFWorld 交互

#### 3.1.1 文字交互

在 2.2 的实验目录和环境中，先复制一个“将闹钟放到桌上”的任务。官方入口会生成游戏文件，因此使用独立任务副本：

```bash
set -e
task="$ALFWORLD_DATA/json_2.1.1/train/pick_and_place_simple-AlarmClock-None-Desk-307/trial_T20190907_072303_146844"
mkdir task-alarmclock
cp "$task/initial_state.pddl" "$task/traj_data.json" task-alarmclock/
domain=$(python -c "from alfworld.info import ALFRED_PDDL_PATH; print(ALFRED_PDDL_PATH)")
grammar=$(python -c "from alfworld.info import ALFRED_TWL2_PATH; print(ALFRED_TWL2_PATH)")
script --quiet --return --flush --command "alfworld-play-tw task-alarmclock --domain \"$domain\" --grammar \"$grammar\" --expert heuristic" "task-alarmclock/session-$(date +%Y%m%d-%H%M%S).txt"
```

命令将交互保存到 `task-alarmclock/session-时间.txt`。文字版在终端运行；按 Tab 查看可用动作，名称与编号之间保留空格，例如 `go to sidetable 1`。目标是把闹钟放到桌上，可按下列顺序操作；编号以终端当前输出为准。

| 动作示例 | 检查反馈 |
|---|---|
| `go to sidetable 1` | 到达边桌，找到闹钟及其编号 |
| `take alarmclock 3 from sidetable 1` | 已拿起对应闹钟 |
| `go to desk 1` | 到达桌子 |
| `move alarmclock 3 to desk 1` | 出现 `You won!` |

若反馈为 `Nothing happens.`，先核对空格、物体编号和所在位置。至少完成一个任务，保留原始目标、连续动作与反馈、完成信号。重复任务时重跑最后一条 `script` 命令，无需重新复制文件。

#### 3.1.2 视觉交互

文字任务完成后，在 2.2 的目录和环境中安装视觉依赖。确认下载空间和显示环境后，用官方下载器补齐任务数据、逻辑文件和 Mask R-CNN 权重，再启动视觉入口；首次启动还需准备匹配的 THOR 程序。

```bash
python -m pip install "./alfworld-aaba6870f86c5be6a08a491f32a50b906227bc3e[vis]"
python -m pip check
alfworld-download --data-dir "$ALFWORLD_DATA"
alfworld-play-thor
```

此时应同时出现文字交互与仿真渲染。没有显示环境或 THOR 可执行文件时，记录停止位置；不要将新版 AI2THOR 包直接升级到 ALFWorld 的依赖组合中。图形配置按所用 Linux、WSL 或服务器环境准备。

### 3.2 ALFRED 模型评价

#### 3.2.1 预训练模型评测

激活 ALFRED 专用环境，从 `$ALFRED_ROOT` 执行，将模型路径替换为 2.3 找到的真实文件位置。此多行命令为 Bash；反斜杠后不能追加注释。首次安装或更换数据机器，官方说明要求一次 `--preprocess`；首次用单线程以便准备 THOR 程序。

```bash
python models/eval/eval_seq2seq.py \
  --model_path "实际路径/best_seen.pth" \
  --eval_split valid_seen \
  --data data/json_feat_2.1.0 \
  --model models.model.seq2seq_im_mask \
  --gpu \
  --num_threads 1 \
  --preprocess
```

环境准备和模型加载可能需要额外下载；完整 split 评测并非短时检查，开始前确认时间与资源。只运行部分任务时必须记录选择方法和数量，不能与全量指标直接比较。

官方说明的结果为 checkpoint 所在目录内 `task_results_<timestamp>.json`。找到文件后核对本次时间、数据划分、任务数和退出状态，确认文件对应本次评测。

模型提前 `<stop>` 或被障碍挡住时，保留原始失败轨迹。指标解释见第四节。

#### 3.2.2 训练与调优

完成预训练模型评价并确认训练时间和 GPU 资源后，可在同一专用环境和数据上进行教材的训练练习。以下命令训练一轮：

```bash
python models/train/train_seq2seq.py --data data/json_feat_2.1.0 --model seq2seq_im_mask --dout exp/student_seq2seq --splits data/splits/oct21.json --gpu --batch 8 --pm_aux_loss_wt 0.1 --subgoal_aux_loss_wt 0.1 --epoch 1 --preprocess
```

比较调优前后时，保持数据划分和评测设置一致，记录训练轮数、随机种子、资源和实际输出目录。

### 3.3 AI2THOR 任务规划

#### 3.3.1 人工交互

激活 2.4 的环境，从手册根目录运行；此步启动 Unity：

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir chapter_4/4_1_task_planning/for_simulator/for_ai2thor --mode manual --run --max-steps 10
```

这会启动仿真，首次可能下载 THOR 可执行程序，但不会调用云端模型。终端显示场景物体 ID，每次输入一条 `Action-Target`；`Done` 结束。遇到多个 Cup 时选择输出中的完整 ID。每次只提交一个动作。

从终端物体列表各选一个 `ButterKnife`（餐刀）、`Cup` 和 `CounterTop`，记录完整 ID。[容器规则](https://ai2thor.allenai.org/ithor/documentation/objects/object-types/)允许 `ButterKnife` 放入 `Cup`，普通 `Knife` 不支持这一关系。逐条输入下表动作，把尖括号内容替换成刚才的完整 ID，保留 ID 内的负号。

| 步骤 | 输入 | 应发生的变化 |
|---|---|---|
| 1、2 | `GotoObject-<杯子ID>`，再输入 `PickupObject-<杯子ID>` | 到杯旁并拿起杯子 |
| 3、4 | `GotoObject-<台面ID>`，再输入 `PutObject-<台面ID>` | 杯子放到选定台面 |
| 5、6 | `GotoObject-<餐刀ID>`，再输入 `PickupObject-<餐刀ID>` | 到餐刀旁并拿起餐刀 |
| 7、8 | `GotoObject-<同一杯子ID>`，再输入 `PutObject-<同一杯子ID>` | 餐刀放入该杯 |
| 9 | `Done` | 保存记录并结束 |

每条动作后检查 `lastActionSuccess`；失败时先读错误，检查当前持物和位置。`PutObject` 的参数是要放入的容器或台面。`Done` 只结束输入，不判断任务成功。

截图与状态保存在 `runs/planning/<本次UTC时间>/frame_000.png`、`metadata_000.json` 等，结束时有 `run.json`。查看最后一份 metadata 的 `objects`：餐刀的 `parentReceptacles` 应包含所选杯子 ID，杯子的 `parentReceptacles` 应包含所选台面 ID；两者的 `isPickedUp` 均为 `false`，杯子的 `isBroken` 为 `false`。将这几项与最后截图一起记入结果。

#### 3.3.2 大模型规划

前一项手动交互通过后，在同一环境补装课程使用的模型 SDK：

```bash
python -m pip install dashscope==1.23.1
python -m pip check
python -m pip freeze > "$HOME/eai-lab/eai-ai2thor/environment-llm.txt"
```

确认模型权限、地域和费用后，在同一 Bash 终端配置 `DASHSCOPE_API_KEY`：

```bash
read -rsp "输入本机 DashScope Key（不回显）: " DASHSCOPE_API_KEY
export DASHSCOPE_API_KEY
printf '\n'
```

密钥不得硬编码或提交。端点有地域要求时，从百炼控制台对应地域的官方调用示例复制原生 `/api/v1` 地址，设置 `DASHSCOPE_HTTP_BASE_URL`；不用兼容 API 地址。本入口限制为 `dashscope.aliyuncs.com`、`dashscope-intl.aliyuncs.com` 或 `dashscope-us.aliyuncs.com` 的 HTTPS 原生端点；若课程账号使用其他官方端点，先让助教核对后调整白名单，不填第三方转发地址。实际模型名以账号可用列表为准。

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir chapter_4/4_1_task_planning/for_simulator/for_ai2thor --mode llm --model qwen-vl-plus --run --send --max-steps 10
```

`--run` 允许仿真；`--send` 另行允许上传本轮仿真图片与文字并消耗 API 额度。每轮回车确认后才发送，最多尝试指定步数；模型失败时保留错误并停止。

每轮保留场景图、模型动作、执行反馈和后续状态，最终检查：是否同一个杯子、刀是否在杯子里、杯子是否在厨房台面。缺少目标物体或关系不成立时，记录具体原因。`run.json` 的 `task_success` 默认是 `NOT_EVALUATED`，需要你补充目标核对记录。

| 执行状态 | 记录与后续处理 |
|---|---|
| 动作格式错误或目标缺失 | `executed: false`，将原因传给下一轮 |
| 环境明确返回失败 | `executed: true`、`lastActionSuccess: false`，保留失败反馈 |
| 已尝试请求，无法确认是否执行 | `executed: null`，以 `ACTION_OUTCOME_UNKNOWN` 停止 |
| 已收到动作结果，但缺少可信成功字段 | `lastActionSuccess: null`，以 `ACTION_OUTCOME_UNKNOWN` 停止 |
| 截图或写盘失败 | 停止并保留已执行动作的记录；复测前核对仿真状态 |

本课程控制器用 `GotoObject` 封装粗粒度瞬移，部分操作沿用了 `forceAction`。分析结果时说明这些设置，不将本演示与标准 ALFRED 导航指标直接比较。

### 3.4 VirtualHome 家庭任务

#### 3.4.1 人工规则脚本

保持 2.5 启动的 Unity 运行，另开 PowerShell，激活 `eai-virtualhome` 并进入**手册仓库根目录**。

把 `$apiDir` 改为 2.5 克隆的源码中的 `virtualhome/simulation` **绝对路径**，其下应有 `unity_simulator/comm_unity.py`：

```powershell
$apiDir = "D:/自己的实验目录/virtualhome/virtualhome/simulation"
python -X utf8 docs/assets/ch4-planning/virtualhome_checked_demo.py --api-dir "$apiDir" --output-dir runs/virtualhome/rule-01
```

预期 `CHECK_ONLY`、`NOT_EVALUATED`：只检查文件路径，不连接 Unity，不创建结果目录。确认路径和端口后执行：

```powershell
python -X utf8 docs/assets/ch4-planning/virtualhome_checked_demo.py --api-dir "$apiDir" --output-dir runs/virtualhome/rule-01 --run
```

`--run` 会将本机 Unity 重置到场景 0，添加角色，再根据本轮真实图生成并逐步执行“走向三文鱼、拿取、走向冰箱、必要时开门、放入、关门”。不要同时让其他程序控制此 Unity 实例。每次复测换一个新输出目录，脚本拒绝覆盖已有目录。

| 参数或文件 | 用途 |
|---|---|
| `--port` / `--scene` | 默认 8080 / 0；端口须与 Unity 启动参数一致，仅连接本机 |
| `--food-id` / `--fridge-id` | 多个同类物体时，从保存的 `graph_before.json` 选择实例；不能照抄其他场景的 ID |
| `graph_before.json` / `graph_after.json` | 初始与最终真实环境图；缺图时不能验收 |
| `plan.json`、`step_*.json`、`graph_*.json` | 本次候选计划、各步原始返回值及执行后状态；失败时立即停止后续动作 |
| `result.json` | 完整记录：`task_success`、`evidence_complete`、失败原因、最终判据和录制帧数 |
| `recording/` | 按步骤分开命名的第一人称录像帧，10 fps；没有录像时须补齐证据 |

**成功必须同时满足**：全部动作返回真，选定 salmon 到选定 fridge 存在 `INSIDE`，冰箱为 `CLOSED` 且非 `OPEN`，salmon 不被角色持有。程序显示 `task_success=True` 后，仍需查看 `result.json` 与录像。原始图缺失、角色或状态不完整时记为 `UNKNOWN`；退出码 0 的文件预检或场景准备不是任务成功。

同时检查 `evidence_complete` 为真且每步有录制帧。任务状态与证据完整性分开报告：目标达成但录像缺失时，保留本次记录并补齐录像；`run.json` 是简版，完整字段以 `result.json` 为准。

这是人工规则计划，程序使用 `find_solution=False`，不调用模型。报告中填写“规则任务”；模型计划另按 3.4.2 执行。

#### 3.4.2 大模型规划

先在同一 PowerShell、`eai-virtualhome` 环境和手册根目录准备一个新场景，只保存初始图：

```powershell
python -X utf8 docs/assets/ch4-planning/virtualhome_checked_demo.py --api-dir "$apiDir" --output-dir runs/virtualhome/prepare-01 --run --prepare
```

检查 `$LASTEXITCODE` 为 0、`run.json` 为 `PREPARED` / `NOT_EVALUATED`。此命令确实重置场景，但没有执行任务动作。若失败先处理报错，不继续调用模型。

激活已按[第3章](ch3-dialogue.md)配置的 `eai-dialogue` 环境，保留当前目录。确认 Key、地域、模型权限及费用后，运行下面**整个脚本块**，每个阶段失败都会停止后续调用：

```powershell
conda activate eai-dialogue
& {
    $ErrorActionPreference = "Stop"
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $prepareDir = (Resolve-Path "runs/virtualhome/prepare-01").Path
    $selection = Get-Content "$prepareDir/run.json" -Raw | ConvertFrom-Json
    if ($selection.execution_state -ne "PREPARED") { throw "场景尚未准备好" }
    if (Test-Path "$prepareDir/answer.txt") { throw "已有模型回答，请创建新的准备目录" }
    python -X utf8 docs/assets/ch4-planning/planning_checks.py vh-prompt --graph "$prepareDir/graph_before.json" --food-id $selection.food_id --fridge-id $selection.fridge_id | Set-Content -Encoding utf8 "$prepareDir/question.txt"
    if ($LASTEXITCODE -ne 0) { throw "生成问题失败，未调用模型" }
    python -X utf8 docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --question-file "$prepareDir/question.txt" --output "$prepareDir/answer.txt" --max-tokens 1024 --send
    if ($LASTEXITCODE -ne 0) { throw "模型请求失败，停止执行" }
    python -X utf8 docs/assets/ch4-planning/planning_checks.py vh-check --graph "$prepareDir/graph_before.json" --response "$prepareDir/answer.txt" --food-id $selection.food_id --fridge-id $selection.fridge_id
    if ($LASTEXITCODE -ne 0) { throw "模型动作格式或目标 ID 不合法" }
}
```

模型回答必须是仅含 `steps` 的 JSON，动作限于 `WALK/GRAB/OPEN/PUTIN/CLOSE`。格式检查不判断可达性或动作顺序。此模型路线尚未实测，保留原始回答与请求记录，并按下一步在 Unity 中检验。

三阶段均成功后，切回 `eai-virtualhome`。保持相同 Unity 版本和场景 0，使用新的执行目录；入口会重新初始化场景并再次对当前真实图检查计划中的 ID：

```powershell
conda activate eai-virtualhome
$selection = Get-Content runs/virtualhome/prepare-01/run.json -Raw | ConvertFrom-Json
python -X utf8 docs/assets/ch4-planning/virtualhome_checked_demo.py --api-dir "$apiDir" --scene $selection.scene --food-id $selection.food_id --fridge-id $selection.fridge_id --plan runs/virtualhome/prepare-01/answer.txt --plan-source model --output-dir runs/virtualhome/model-01 --run
```

传入的是原始 `answer.txt`，不是 `vh-check` 打印的带状态摘要。`--plan-source model` 只记录你声明的来源，程序本身不调用模型，也不能认证计划来源。按 3.4.1 的完整目标判据验收；失败时保留旧目录，将失败动作与原因补入新的问题后再准备下一次实验，不把规则计划结果混入模型成绩。

上述示例使用端口 8080；若在 2.5 更换端口，准备与执行两条命令都需添加相同的 `--port`。选择其他场景或物体时也须前后一致，不以另一轮的图替代当前准备记录。

## 四、实验结果

| 路线 | 结果文件或记录 | 检查内容 |
|---|---|---|
| ALFWorld | 连续的目标、动作、反馈记录 | 至少完成一个任务，保留环境完成信号；失败时保留终止位置 |
| ALFRED | `task_results_<timestamp>.json`、失败轨迹 | 数据划分、任务数与 SR/GC 等指标一致 |
| AI2THOR | 截图、metadata、`run.json` | 杯子实例一致，刀在杯内，杯在厨房台面；人工和模型模式分别记录 |
| VirtualHome | 执行前后环境图、计划、执行反馈、录像 | 全部动作成功，三文鱼位于指定冰箱内、冰箱已关闭且三文鱼未被持有；人工与模型计划分别记录 |

ALFRED 指标：

| 指标 | 教材含义 | 阅读结果时注意 |
|---|---|---|
| SR | 任务成功率 | 一次成功不等于整体模型成功率高 |
| GC | 满足的目标条件比例 | 部分目标满足但整体仍可能失败 |
| PLW SR | 路径长度加权的任务成功率 | 权重口径按官方评测实现，不自行替换公式 |
| PLW GC | 路径长度加权的目标条件完成率 | 不与未加权 GC 混为同一指标 |

每条路线记录环境/代码版本、场景或数据、命令、任务、动作与反馈、输出位置、结束原因及目标检查结果；未运行的步骤注明状态。

## 五、排错建议与注意事项

| 现象 | 先看哪里 |
|---|---|
| 文字版没有弹三维窗口 | 是否运行 `alfworld-play-tw`；文字模式本来就在终端交互 |
| 缺少游戏文件 | 下载是否完成、`ALFWORLD_DATA` 与缓存目录是否一致 |
| 卡在 resetting env / Unity 初始化 | THOR 版本、可执行文件、图形/显示条件；不先改模型提示词 |
| ALFRED 导入或词表错误 | 专用环境、`ALFRED_ROOT`、预处理目录、模型对应数据 |
| AI2THOR 输出 Done 但没有完成 | `Done` 只是停止信号，重新检查目标关系 |
| 某个物体类型有多个实例 | 从当前状态选择完整 ID，不用子串匹配 |
| PutObject 持续失败 | 目标是否容器、当前手持物与位置是否满足前置条件 |
| VirtualHome 脚本指向错误物体 | 是否照抄了别的场景 ID，当前角色/场景版本是否一致 |

成功、失败和准备阶段的参考记录见[检查记录](../assets/ch4-planning/verification.md)，其中 VirtualHome 六步结果来自人工规则任务。

参考资料：[ALFWorld 官方项目](https://github.com/alfworld/alfworld)、[ALFRED 官方模型说明](https://github.com/askforalfred/alfred/blob/master/models/README.md)、[AI2THOR 初始化说明](https://ai2thor.allenai.org/ithor/documentation/)、[VirtualHome 官方项目](https://github.com/xavierpuigf/virtualhome)。
