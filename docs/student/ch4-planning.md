# 第 4 章：仿真任务规划

对应教材 **4.4.1 在仿真环境上的规划实验**，印刷页 133—140（v2.0 PDF 第 151—158 页）。教材分成三部分：ALFWorld 交互体验、ALFRED 小模型测试、基于大模型的规划演示；第三部分包含 AI2THOR 和 VirtualHome。

> **验证范围（2026-09-20）**：已核对教材、课程代码和上游说明，完成配套动作/状态校验的离线测试。尚未安装和运行完整 ALFWorld、ALFRED、AI2THOR 或 VirtualHome 环境，没有模型规划成功率或实测视频。[检查记录](../assets/ch4-planning/verification.md)区分源码问题、已测逻辑和待实测部分。

## 一、实验目标与安排

任务规划不是只生成一句动作指令。你要观察：**任务目标、当前状态、可用技能、历史动作和环境反馈，怎样一起决定下一步。**模型说 `Done`、环境执行了一步、整个任务完成，必须分别记录。

| 教材部分 | 先完成的内容 | 是否需要云端模型 API |
|---|---|---|
| ALFWorld 交互体验 | 人工在 TextWorld 里选择动作，完成一个环境任务 | 不需要；首次安装和下载数据仍需网络 |
| ALFRED 小模型测试 | 加载 Seq2Seq/LSTM 模型，在对应 THOR 环境评测 SR/GC 等 | 不需要云端 API，但需要模型、数据和兼容运行环境 |
| AI2THOR 大模型演示 | 图像/状态 → 大模型动作 → 执行 → 反馈 | 原课程示例需要 DashScope Key；可先独立检查仿真器 |
| VirtualHome | 先执行“把三文鱼放入冰箱”的人工脚本，再尝试模型规划 | 人工脚本不需要；模型路线另需规划器 |

第一次先做 ALFWorld 文字交互。不要把四套依赖全部装进 `eai-dialogue`。本页 Linux 命令放在 Bash 中执行；Windows 下有 Git Bash 不等于已经具备 Linux 仿真环境。先确定课程 Linux 机器或经过确认的 WSL 环境，不能仅凭 Python 包安装成功就认定 Unity 可运行。

各工程放在手册仓库旁边，不放进手册 Git。文件、视频和模型输出先留在各自本地实验目录，公开提交前筛选并去除个人信息。

## 二、先做两项不联网的入口检查

从**手册仓库根目录**运行，需要 Python 3.9 或更高版本，无需安装仿真器或模型依赖：

```bash
python docs/assets/ch4-planning/test_planning_checks.py
python docs/assets/ch4-planning/planning_checks.py action --text "PickupObject-Cup"
```

第二条只应得到 `FORMAT_ONLY`，且 `executed: false`、`task_success: NOT_EVALUATED`。输入合法不代表场景里存在杯子。这两步仅用于认识接口和检查配套代码，不算完成 ALFWorld 或大模型规划实验。

## 三、第一部分：ALFWorld 交互体验

### 3.1 文字路线优先

教材使用 Python 3.9 和 `alfworld[full]`。当前上游 README 也提供**不带 full 的文字版安装**；这里把它列作同一交互体验的轻量起步方式，不代替后面的视觉路线。没有 API Key 不影响人工 TextWorld 交互。

以下从你选定的 Linux 实验目录运行，安装前确认网络、磁盘和数据下载权限：

```bash
conda create -n eai-alfworld python=3.9 -y
conda activate eai-alfworld
python -m pip install alfworld
python -m pip check
python -c "from importlib.metadata import version; print('alfworld', version('alfworld'))"
alfworld-download
alfworld-play-tw
```

`alfworld-download` 按上游说明下载 PDDL、游戏文件和预训练检测器等资源，默认缓存为 `~/.cache/alfworld/`；并非“文字路线就没有下载”。教材的体积数字是当时示例，不作为当前下载量保证。数据未准备好时停在下载，不反复重装 Conda。

如果必须严格按教材全量环境，使用单独环境并将安装项改为 `"alfworld[full]"`。不要在基础文字路线通过前先下载所有可选 checkpoint。

### 3.2 窗口在哪里，怎样操作

`alfworld-play-tw` 的主要窗口就是启动它的终端：显示一段场景文字和本轮目标，等待你输入命令。**没有三维窗口是文字版的正常现象。**按当前版本终端提示查看帮助/可执行动作，使用当前场景中的实际物体名称与编号，不照抄另一个房间的编号。

记录一个小任务：原始目标、每一步输入、每一步反馈和结束结果。如果尝试的动作失败，先读取反馈，再决定是位置不对、对象不对还是前置动作缺失。按教材，任务成功时能看到 `you won`；若所用版本输出不同，记录版本及实际完成信号，不能人为补写成功文字。

**验收**：真实启动环境并完成至少一个交互任务，保留连续记录。检查“环境成功”而不只是退出终端。这里规划者是学生本人，不是 LLM。

### 3.3 视觉路线

文字任务通过后，在匹配的 Linux 图形环境中按官方说明安装视觉依赖并运行：

```bash
python -m pip install "alfworld[vis]"
alfworld-play-thor
```

此时应同时出现文字交互与仿真渲染。没有显示环境或 THOR 可执行文件时，记录停止位置；不要将新版 AI2THOR 包直接升级到 ALFWorld 的依赖组合中。原生 Windows、WSL 和服务器的图形设置并不等价，先按对应上游版本配置，必要时由课程管理员准备。

## 四、第二部分：ALFRED 小模型训练与评价

### 4.1 获取环境和数据

教材中的模型是 Seq2Seq/LSTM，并使用视觉特征，**不是只读一份文本 JSON 就能完成模型执行评测**。官方评测需要在 THOR 中实际执行。原始项目列出的 PyTorch/torchvision/AI2THOR 版本较旧，不能与下一节课程 AI2THOR 5.0.0 环境混装。先向助教取得可运行的历史环境或按官方兼容组合单独建立环境；本页没有编造已验证的 Python/CUDA 锁文件。

```bash
# 从独立实验父目录开始，不在手册目录内部下载模型。
git clone https://github.com/askforalfred/alfred.git
cd alfred
export ALFRED_ROOT="$PWD"
git rev-parse HEAD
```

在助教确认的专用环境中，从 `$ALFRED_ROOT` 执行 `python -m pip install -r requirements.txt`，再用 `python -m pip check` 检查冲突。官方 quickstart 采用 `json_feat` 数据（其 README 标注约 17 GB）。**这是相对教材 `json_2.1.0` 文字 JSON 路线的数据调整**：本页按上游示例统一使用包含轨迹和预提取视觉特征的 `json_feat_2.1.0`，不是简单给原目录改名。下面仅供资源确认后执行，不作为本次已经下载的记录：

```bash
cd "$ALFRED_ROOT/data"
bash download_data.sh json_feat
cd "$ALFRED_ROOT"
```

若课程选择仅轨迹 JSON 的路线，需进一步核实该版本如何获取视觉输入、渲染和预处理；不能把“没有下载完整图片数据集”解释成“模型不使用图像”。

### 4.2 先评价预训练模型

不必为了学习指标先完成全量训练。按官方 `models/README.md` 下载其 Seq2Seq+PM checkpoint，解压后定位实际的 `best_seen.pth`，不要猜它会落在哪一级目录。

```bash
# 工作目录：$ALFRED_ROOT；下载前确认额度。
wget https://ai2-vision-alfred.s3-us-west-2.amazonaws.com/seq2seq_pm_chkpt.zip
unzip seq2seq_pm_chkpt.zip
find . -name best_seen.pth
```

将下面路径替换为刚找到的真实路径。此多行命令为 Bash；反斜杠后不能追加注释。首次安装或更换数据机器，官方说明要求一次 `--preprocess`；首次用单线程以便准备 THOR 程序。

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

教材命令的训练路径漏了 `alfred`，模型路径也与前面目录不一致。本页统一从 `$ALFRED_ROOT` 运行。环境准备和模型加载可能需要额外下载；完整 split 评测并非短时检查，开始前确认时间与资源。只运行部分任务时必须记录选择方法和数量，不能与全量指标直接比较。

官方说明的结果为 checkpoint 所在目录内 `task_results_<timestamp>.json`。找到文件后核对本次时间、数据划分、任务数和退出状态，不把旧文件作为新结果。

| 指标 | 教材含义 | 阅读结果时注意 |
|---|---|---|
| SR | 任务成功率 | 一次成功不等于整体模型成功率高 |
| GC | 满足的目标条件比例 | 部分目标满足但整体仍可能失败 |
| PLW SR | 路径长度加权的任务成功率 | 权重口径按官方评测实现，不自行替换公式 |
| PLW GC | 路径长度加权的目标条件完成率 | 不与未加权 GC 混为同一指标 |

模型提前 `<stop>` 或被障碍挡住时，保留原始失败轨迹。这正是教材要求分析的内容，不需要为了报告好看删掉失败。

### 4.3 训练与调优（教材练习，资源允许再做）

在已验证的专用环境和数据上，下面给出一轮训练的命令入口，`--epoch` 名称已与源码核对。仍可能耗时较长，不承诺训练时间。

```bash
python models/train/train_seq2seq.py --data data/json_feat_2.1.0 --model seq2seq_im_mask --dout exp/student_seq2seq --splits data/splits/oct21.json --gpu --batch 8 --pm_aux_loss_wt 0.1 --subgoal_aux_loss_wt 0.1 --epoch 1 --preprocess
```

比较调优前后时，保持数据划分和评测设置一致，记录训练轮数、随机种子和资源。没有运行训练，写“本次使用预训练模型评价”或“未运行”，不补造训练曲线。

## 五、第三部分 A：AI2THOR 大模型规划

### 5.1 来源与已发现的问题

课程源码位于 `EAI_project/chapter_4/4_1_task_planning/for_simulator/for_ai2thor/`。本次核对提交为 `e6bb5d5de828b5d87834ea169b53c09b376d8b09`；任务保留教材的 `place a cup with a knife in it on the kitchen counter space`，场景为 `FloorPlan10`。

| 原课程示例问题 | 本页配套入口的处理 |
|---|---|
| 技能表有 `Done`，但控制器没有对应方法；循环内仍尝试分发它 | 精确识别终止词，在执行前停止，不调用 `getattr(..., 'Done')` |
| `split('-')` 会截断包含负坐标的 objectId | 仅按第一个分隔符拆分 |
| 动作小写白名单通过后，原大小写又用于动态方法查找 | 映射为技能表中的规范拼写 |
| 子串匹配物体，完整 ID 又被丢弃 | 完整 ID 精确匹配；类别重名要求选 ID，不悄悄挑另一个实例 |
| 对空物体/空接近姿态直接 `[0]` | 给出明确失败信息，停止该动作 |
| `'false' in str(False)` 大小写不符，失败反馈可能遗漏 | 检查真实布尔值和 errorMessage |
| 原循环没有次数上限，API 失败可继续重复 | 配套入口限制步数，请求异常停止，不自动无限重试 |
| 把 `done` 当作任务完成 | 只记结束原因；结果一律保留人工目标验收 |

这些不是对原文件的远端修改。本页新增[修订入口](../assets/ch4-planning/ai2thor_checked_demo.py)，通过手册侧派生控制器修复上述控制流程；原 `EAI_project` 不变。依赖版本仍需实际环境联调，因此不能把离线测试通过当作 Unity 接口已验证。

### 5.2 先检查源码和仿真，不调用模型

先获取课程仓库；已下载则使用原副本，确保没有未保存修改后再决定是否切换到核对版本。**不要在手册仓库执行这条 checkout。**新副本从手册旁边的实验父目录获取：

```bash
git clone https://github.com/SH9959/EAI_project.git
cd EAI_project
git checkout e6bb5d5de828b5d87834ea169b53c09b376d8b09
cd chapter_4/4_1_task_planning/for_simulator/for_ai2thor
```

进入该提交的 `for_ai2thor` 目录，建立独立环境后安装其 requirements。文件固定了 `ai2thor==5.0.0`，也含 Linux CUDA/NCCL/Triton 等较大依赖；不要直接在 Windows 基础环境中整份安装。没有对应 Linux 条件时先记录平台缺项，不能把 pip 成功误记为仿真就绪。

```bash
conda create -n eai-ai2thor python=3.9 -y
conda activate eai-ai2thor
python -m pip install -r requirements.txt
python -m pip check
```

回到**手册根目录**后，传入课程 `for_ai2thor` 的实际绝对路径：

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir "实际的/for_ai2thor目录"
```

不加 `--run` 只检查两份课程文件的内容哈希和动作表，不启动 Unity、不联网。源码内容不同则停止，先核对差异，不覆盖别人的文件。哈希检查允许正常的 CRLF/LF 换行转换。

取得图形运行条件后，显式允许启动 Unity，先用手动动作排查接口：

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir "实际的/for_ai2thor目录" --mode manual --run --max-steps 10
```

这会启动仿真，首次可能下载 THOR 可执行程序，但不会调用云端模型。终端显示场景物体 ID，由你输入一条 `Action-Target`；`Done` 结束。遇到多个 Cup 时选择输出中的完整 ID。不要输入多行计划或 Python 代码。

截图与状态保存在 `runs/planning/<本次UTC时间>/frame_000.png`、`metadata_000.json` 等，结束时有 `run.json`。脚本不修改相机硬件，不控制真实机械臂。**手动成功只证明人工规划和仿真动作路线，不证明 LLM 规划成功。**

### 5.3 再接入大模型

前一项手动交互通过，并确认模型权限、地域和费用后，在同一 Bash 终端配置 `DASHSCOPE_API_KEY`：

```bash
read -rsp "输入本机 DashScope Key（不回显）: " DASHSCOPE_API_KEY
export DASHSCOPE_API_KEY
printf '\n'
```

密钥不得硬编码或提交。端点有地域要求时，从百炼控制台对应地域的官方调用示例复制原生 `/api/v1` 地址，设置 `DASHSCOPE_HTTP_BASE_URL`；不用兼容 API 地址。本入口限制为 `dashscope.aliyuncs.com`、`dashscope-intl.aliyuncs.com` 或 `dashscope-us.aliyuncs.com` 的 HTTPS 原生端点；若课程账号使用其他官方端点，先让助教核对后调整白名单，不填第三方转发地址。实际模型名以账号可用列表为准。

```bash
python docs/assets/ch4-planning/ai2thor_checked_demo.py --course-dir "实际的/for_ai2thor目录" --mode llm --model qwen-vl-plus --run --send --max-steps 10
```

`--run` 允许仿真；`--send` 另行允许上传本轮仿真图片与文字并消耗 API 额度。每轮回车确认后才发送，最多尝试指定步数；模型失败时保留错误并停止。CLI 本身不会替你申请权限或设置费用上限。

每轮保留场景图、模型动作、执行反馈和后续状态，最终检查：是否同一个杯子、刀是否在杯子里、杯子是否在厨房台面。场景没有合适物体或关系不成立时，记录失败，不修改任务表述来冒充原任务成功。`run.json` 的 `task_success` 默认是 `NOT_EVALUATED`，需要你补充目标核对记录。

动作格式错误或没有目标时，本轮记为 `executed: false`，把原因传入下一轮；环境明确返回失败时，记为 `executed: true`、`lastActionSuccess: false`。若请求已尝试但不能确认是否执行，`executed` 为 `null`；若已收到动作结果但缺少可信成功字段，`lastActionSuccess` 为 `null`。后两种情况均以 `ACTION_OUTCOME_UNKNOWN` 停止，先检查保存的记录与仿真状态，不把“未知”改写成失败前完全未动过。截图或写盘失败会停止，已执行的动作记录保留。

`PutObject` 的参数是**目标容器或台面**，不是正在拿的物体。例如要把刀放入杯子，目标应是杯子。原代码注释中出现的 `TeleportObject` 也不在动作白名单中，不能把那段注释当可直接运行的标准答案。

本课程控制器用 `GotoObject` 封装粗粒度瞬移，部分操作沿用了 `forceAction`。因此这里是课程任务规划演示，不可直接作为标准 ALFRED 导航指标，也不能声称验证了真实机器人可行性。

## 六、第三部分 B：VirtualHome 家庭任务

### 6.1 先统一版本，再连接 Unity

教材写 Python 3.9，并建议改 `setup.py` 中的版本声明；本次读取的上游 `setup.py` 已要求 Python ≥3.10，同时还固定了若干旧依赖。**不要只把 `python_requires` 改低来绕过检查，也不要假定升级 Python 就自动解决全部兼容性。**向助教取得 Python 包提交、Unity 程序版本和经过验证的依赖组合，然后按对应官方说明安装。

教材 140 页的可执行文件链接指向历史 Windows Unity 2.3.0 包 `release/simulator/v2.0/v2.3.0/windows_exec.zip`，当前[官方 README 的下载段](https://github.com/xavierpuigf/virtualhome#download-unity-simulator)也列出 2.3.0 的各平台程序。这提供了版本线索，但不保证历史文件当前能下载、也不保证与最新 Python 包兼容。**尚未领到匹配版本和可工作的连接样例时，真实执行停在本节；下节的 `PLAN_ONLY` 不能填补这个缺项。**

课程 `demo_in_virtualhome.py` 的导入路径是 `from simulation...`；你安装的包布局可能不同，先确认 `comm_unity` 实际路径。它还硬编码 Unity 可执行路径、视频目录及物体 ID。仅修改路径不代表任务就正确：实际运行的 `script2` 操作的是 `cereal`，而教材练习目标是 `salmon`。

### 6.2 人工脚本：把三文鱼放入冰箱

先用与 Unity 版本对应的官方最小样例确认连接，确保它建立了 `comm` 并添加执行脚本的角色 `<char0>`。下面代码在**这个仍持有 `comm` 的 Python 会话或 notebook** 中运行；替换实验目录为自己的绝对路径：

```python
import json
from pathlib import Path

run_dir = Path("/你的实验目录/virtualhome_run").resolve()
run_dir.mkdir(parents=True, exist_ok=True)
ok, graph_before = comm.environment_graph()
if not ok:
    raise RuntimeError("环境图读取失败，停止规划。")
(run_dir / "graph_before.json").write_text(
    json.dumps(graph_before, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

确认本轮图中确有 salmon 和 fridge，不照搬示例中的 333、304。每次复测使用新的实验输出目录，以免把旧图与新执行混用。

回到手册根目录，用配套函数按图生成候选脚本：

```bash
python -X utf8 docs/assets/ch4-planning/planning_checks.py vh-plan --graph "/你的实验目录/virtualhome_run/graph_before.json" > "/你的实验目录/virtualhome_run/plan.json"
```

这是 Bash 命令；确认退出码为 0，再打开 `plan.json`。同类节点多个时，显式添加 `--food-id` 和 `--fridge-id`，ID 必须来自本轮真实图。输出为 `PLAN_ONLY`，不能把生成脚本记为任务执行成功。命令失败时可能留下空文件，不要继续读取或消费旧计划。

候选顺序是走到三文鱼、拿取、走到冰箱、必要时打开、放入、关闭。回到上面仍持有 `comm` 和 `run_dir` 的 Python 会话，用实际计划作为 `render_script` 输入，保存原始执行反馈并再次导图：

```python
plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
if plan.get("mode") != "PLAN_ONLY" or not plan.get("steps"):
    raise RuntimeError("没有可用的候选步骤，停止执行。")
ok, message = comm.render_script(
    plan["steps"], recording=True, camera_mode=["FIRST_PERSON"],
    output_folder=str(run_dir / "recording"), find_solution=True, frame_rate=10
)
(run_dir / "execution.json").write_text(
    json.dumps({"render_success": ok, "message": message}, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
graph_ok, graph_after = comm.environment_graph()
if not graph_ok:
    raise RuntimeError("执行后的环境图读取失败，目标状态未知。")
(run_dir / "graph_after.json").write_text(
    json.dumps(graph_after, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("render_script 返回：", ok, message)
```

**这里的规划者仍然是人工规则，不是大模型。**参数沿用课程样例的 `recording=True`、`camera_mode=['FIRST_PERSON']`、`find_solution=True`、`frame_rate=10`；实际支持情况以匹配的 Unity/Python 版本为准，这段输入输出接线尚未实测。返回 `ok` 不为真时保留失败消息和执行后图，不继续把它写成成功。

执行后重新获取 `graph_after.json`，对照视频核对三文鱼是否进入目标冰箱。配套函数 `inside_relation(graph, food_id, fridge_id)` 仅检查给定图的 `INSIDE` 关系；图必须是本轮执行后从环境导出的真实结果。不能手工改 JSON 或只看渲染视频文件存在来判成功。

输出可能是逐帧图片而不是已经封装的视频，按所用版本的录像流程确认，不直接把输出目录改名为 `.mp4`。没有匹配 Unity 程序或缺少 salmon 时，明确记录缺项，不把麦片任务自动替代三文鱼任务。

### 6.3 大模型规划扩展

这是教材单独提出的第二个练习。输入自然语言目标与当前环境图，输出可解析的规划步骤；执行前验证动作名、参数数量和节点 ID，再将执行反馈传回规划器。不要 `eval`/`exec` 模型生成的任意代码。

当前课程示例未实现这条 LLM 调用链，本页也没有伪造一个“已验证的大模型 VirtualHome 工程”。只有人工脚本通过时，扩展仍记“未实现/未运行”；后续补代码需再次验证接口、目标条件及错误恢复。

## 七、结果记录与常见问题

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

每条路线分别记录：环境/代码版本、数据或场景、真实运行命令、输入任务、动作—反馈序列、输出文件位置、结束原因和目标验证。离线检查、人工规划、模型规划三类记录不要混在同一“成功率”里。

思考：模型生成的动作在技能表里，就一定可执行吗？模型停止和目标完成怎样区分？带有全部场景元数据、瞬移能力的教学演示，与标准评测差在哪里？

扩展资料：[ALFWorld 官方项目](https://github.com/alfworld/alfworld)、[ALFRED 官方模型说明](https://github.com/askforalfred/alfred/blob/master/models/README.md)、[AI2THOR 初始化说明](https://ai2thor.allenai.org/ithor/documentation/)、[VirtualHome 官方项目](https://github.com/xavierpuigf/virtualhome)。
