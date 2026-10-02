# 第 3 章：人机对话与多模态交互

对应教材 **3.4.1 人机对话实验、3.4.2 结合图像小模型、3.4.3 实机部署**。实验包括文本与图像问答、语音识别、语音合成及文件级集成。

## 一、实验目标

完成文本问答、图像问答和语音交互，比较直接图像输入与 BLIP 描述输入的结果，并通过中间文件定位识别、描述、问答和合成阶段的错误。

| 路线 | 输入与输出 | 完成标准 |
|---|---|---|
| A 文本API | 问题→千问文本模型→回答 | 得到与问题相关的回答，保存实际输出和请求编号 |
| B 图像API | 图片和问题→千问视觉模型→回答 | 能核对图片中的主要物体；换图后回答随之变化 |
| C 图像小模型 | 图片→BLIP描述→文本模型回答 | 同时保留caption与answer，并指出描述漏掉的细节 |
| D 语音识别 | 录音→SenseVoice→文字 | 转写与录音内容一致，记录误字、漏字 |
| E 语音合成 | 回答文本和参考音频→CosyVoice2→wav | 文件可播放，内容与输入文字基本一致 |
| F 摄像头与集成 | 录音/图像→文字回答→语音 | 保存同轮输入、中间文件和合成音频，核对最终回答 |

按 A → B/C → D → E → F 的顺序操作。本地 Qwen 和 MiniCPM 部署见 3.7，可在具备对应资源后单独开展。

## 二、实验环境配置

### 2.1 代码与工作目录

首次获取手册时执行以下命令；已有副本直接进入仓库根目录。Git 和 Conda 的准备方法见[开始实验前](setup.md)。

```bash
git --version
conda --version
git clone --branch feature/whr https://github.com/SH9959/EAI_experiment_handbook.git
cd EAI_experiment_handbook
```

除另有说明，所有命令均从 **`EAI_experiment_handbook` 根目录**运行，输出保存在 `runs/dialogue/`，手工填写的文本文件保存为 UTF-8。配套入口为 [dialogue_lab.py](../assets/ch3-dialogue/dialogue_lab.py)。新终端先进入仓库，再激活所需环境。

| 路线 | 平台与硬件 | 环境及输入 |
|---|---|---|
| A/B 文本与图像 API | Windows、Linux 或 macOS；无需本地 GPU | `eai-dialogue`；有效 Key、网络和允许上传的图片 |
| C BLIP | 可先使用 CPU；CUDA 需匹配驱动与 PyTorch | `eai-dialogue`，另装 torch、Transformers；完整模型快照 |
| D SenseVoice | 优先使用课程 Linux 机器；可选择 CPU/CUDA | 独立 `eai-sensevoice` 环境；短录音与模型/VAD 文件 |
| E CosyVoice2 | 课程 Linux 机器及匹配的推理依赖 | 独立 `eai-cosyvoice` 环境；回答文本、参考音频及转写 |
| F 采集与集成 | 摄像头、麦克风和播放设备；仅文件链路可用已有图片/录音 | 复用各模块环境，以同轮文件衔接 |

### 2.2 A—C 的基础环境

```bash
conda create -n eai-dialogue python=3.10 -y
conda activate eai-dialogue
python -m pip install dashscope pillow
python -c "import sys; print(sys.executable); print(sys.version)"
python -c "from pathlib import Path; Path('runs/dialogue').mkdir(parents=True, exist_ok=True)"
python docs/assets/ch3-dialogue/dialogue_lab.py --help
```

帮助中应列出 `api`、`caption`、`asr`、`tts` 和 `capture`；这一步不执行模型。本地 Qwen 使用 3.7 的独立环境。

模型首次加载可能下载权重，安装语音依赖也可能占用较大空间；执行前确认网络、磁盘和下载额度。

### 2.3 配置密钥、地域和模型

按[百炼密钥说明](https://help.aliyun.com/zh/model-studio/get-api-key)取得 Key，并核对业务空间、地域和模型权限。Key 仅保存在本机，不提交到 Git。

**Linux/macOS Bash：**

```bash
export DASHSCOPE_API_KEY="在本机填入自己的Key"
```

**Windows PowerShell：**

```powershell
$env:DASHSCOPE_API_KEY="在本机填入自己的Key"
```

检查是否设置，不打印密钥：

```bash
python -c "import os; print('已设置' if os.getenv('DASHSCOPE_API_KEY') else '未设置')"
```

| 配置项 | 设置要求 |
|---|---|
| `DASHSCOPE_API_KEY` | 在执行命令的终端设置；与模型所在业务空间和地域匹配 |
| `DASHSCOPE_HTTP_BASE_URL` / `--base-url` | 使用对应地域的官方 HTTPS `/api/v1` 地址；命令行参数优先于环境变量，不使用 `/compatible-mode/v1` |
| `--model` | 必填；示例沿用 `qwen-turbo`、`qwen-vl-plus`，需在控制台确认模型已开通且支持该接口的非流式调用 |

## 三、实验过程

### 3.1 文本 API 问答（A）

#### 3.1.1 输入检查

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --question "如何做西红柿鸡蛋？"
```

预期显示 `CHECK ONLY`。此步骤只检查参数、路径和文件后缀，不发送请求，也不生成回答文件。

#### 3.1.2 请求与结果

确认账号、模型和费用后执行：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --question "如何做西红柿鸡蛋？" --output runs/dialogue/text_answer.txt --send
```

| 参数或输出 | 说明 |
|---|---|
| `--question` / `--question-file` | 分别输入文字或读取文本文件，二者互斥；均省略时使用默认问题“如何做西红柿鸡蛋？” |
| `--send` | 发送真实请求，可能计费；省略时仅检查输入 |
| `--output` | 默认 `runs/dialogue/answer.txt`；必须为 `.txt`，输出及其 JSON 记录不能覆盖输入文件 |
| `--max-tokens` | 默认 256，范围 1—2048；限制输出长度，不限制图片大小或总费用 |
| `text_answer.txt` / `text_answer.json` | 分别保存回答和模型、耗时、SDK 版本、请求编号等记录 |

每次调用创建新对话，不继承上轮上下文。复测时换一个输出文件名。运行后立即用 PowerShell 的 `$LASTEXITCODE` 或 Bash 的 `echo $?` 查看退出码；非 0 时先处理报错，不读取旧输出。

**结果检查**：核对回答是否切题，记录遗漏或事实错误。HTTP 200 表示请求成功，不代表内容正确；回答无需与教材逐字一致。

### 3.2 图像 API 问答（B）

自己拍一张清晰的桌面照片，命名为 `scene.jpg`，放入手册根目录的 `runs/dialogue/`。先用图片查看器打开，确认方向、清晰度和隐私内容。

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-vl-plus --image runs/dialogue/scene.jpg --question "桌面上有哪些物品？看不清的部分请说明。" --output runs/dialogue/vision_answer.txt --send
```

| 参数或返回值 | 说明 |
|---|---|
| `--image` | 非空 JPG/JPEG/PNG 文件；与 `--caption-file` 互斥。发送前校验图片内容，执行 `--send` 时上传，仅使用获授权的内容 |
| `--question` | 针对该图片的问题；对照实验保持问题一致 |
| `--output` | 回答保存为 `vision_answer.txt`，请求记录保存为同名 JSON |
| `content` | 图像接口返回的内容通常为含 `text` 字段的列表，由脚本提取文字 |

**结果检查**：将回答中的主要物体与图片对应。移走一个物品后重新拍照，以相同问题再次调用，比较回答变化；两次案例用于功能检查，不据此计算模型准确率。

### 3.3 BLIP 描述与文本问答（C）

```bash
conda activate eai-dialogue
python -m pip install torch "transformers>=4.45,<5"
```

先在 CPU 上检查单张图片。使用 CUDA 时按[PyTorch 安装说明](https://pytorch.org/get-started/locally/)选择匹配包，并记录实际依赖版本。

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py caption --image runs/dialogue/scene.jpg --device cpu --output runs/dialogue/caption.txt
```

立即查看退出码：PowerShell 用 `$LASTEXITCODE`，Bash 用 `echo $?`。**非 0 时停止，不执行下面的 API 命令，也不读取旧 `caption.txt`。** 退出码为 0 后，打开本轮生成的 `caption.txt`，确认非空并与 `scene.jpg` 对应，再发送：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --caption-file runs/dialogue/caption.txt --question "桌面上有哪些物品？看不清的部分请说明。" --output runs/dialogue/caption_answer.txt --send
```

BLIP 首次加载会下载模型与处理器。离线机器需按[官方模型卡](https://huggingface.co/Salesforce/blip-image-captioning-base)准备完整快照，并用 `caption --model 本地目录` 指定；仅权重和 `config.json` 不足以加载。

脚本使用无条件描述，`max_new_tokens=50`，保存 `caption.txt` 和同名 JSON。`--device` 可选 `cpu` / `cuda`，默认 `cpu`；使用 CUDA 前确认 `torch.cuda.is_available()`。

**结果检查**：依次打开原图、`caption.txt` 和 `caption_answer.txt`，标出第一次出现遗漏或错误的位置。文本模型只接收 caption，无法查看原图。与 3.2 对比时使用同一张图片和相同问题，并记录两个模型的名称。

### 3.4 SenseVoice 语音识别（D）

#### 3.4.1 环境与输入

先用电脑录音软件录制约 5—10 秒的普通话问题，并实际播放一次。建议保存为单声道 WAV，将录音保存或复制到**手册根目录的 `runs/dialogue/question.wav`**。重命名扩展名不等于音频格式转换。

使用手册仓库内的 SenseVoice 源码，从仓库根目录安装：

```bash
conda create -n eai-sensevoice python=3.10 -y
conda activate eai-sensevoice
python -m pip install -r chapter_3/3_3_human_perception/3.3.3/SenseVoice/requirements.txt
python -m pip check
python -c "import torch, torchaudio, funasr; print(torch.__version__, torchaudio.__version__, torch.cuda.is_available())"
```

依赖要求包括 `funasr>=1.1.3`、`torch<=2.3`、`numpy<=1.26.4`；torch 与 torchaudio 必须兼容，导入或 `pip check` 失败时先解决依赖。模型加载会执行课程目录的 `model.py`，不要换成来源不明的文件。

#### 3.4.2 转写与问答

保持 `eai-sensevoice` 环境，在手册仓库根目录执行：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py asr --repo chapter_3/3_3_human_perception/3.3.3/SenseVoice --audio runs/dialogue/question.wav --device cpu --output runs/dialogue/question.txt
```

首次运行会下载 `iic/SenseVoiceSmall` 和 `fsmn-vad`；离线时需先准备匹配缓存。有可用 GPU 时可改为 `--device cuda:0`。

先打开 `question.txt`，与录音逐句核对。若使用了新终端，先按 2.3 在这个终端重新设置 Key 和地域；切换 Conda 环境不会从另一个终端取得环境变量。确认内容正确后再执行：

```bash
conda activate eai-dialogue
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --question-file runs/dialogue/question.txt --output runs/dialogue/answer.txt --send
```

输入传递使用 `question.txt`，不使用包含模型加载日志的控制台输出。

**结果检查**：`question.txt` 与录音意思一致；记录误字、漏字及同名 JSON 中的耗时。脚本自动识别语言、规整文字并合并语音段。

### 3.5 CosyVoice2 语音合成（E）

#### 3.5.1 依赖与模型

使用 **CosyVoice2-0.5B** 和下方固定源码版本，参考音频参数传文件路径；不要混用教材旧接口的音频张量写法。

本节按 Linux 配置，Windows 依赖尚未验证。安装前确认驱动、磁盘和下载额度；requirements 中的 PyTorch、torchaudio、CUDA/TensorRT 等依赖也会占用空间。

```bash
# 从存放手册仓库的父目录开始
git clone --recursive https://github.com/QwenAudio/CosyVoice.git
cd CosyVoice
git checkout 074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc
git submodule update --init --recursive
conda create -n eai-cosyvoice python=3.10 -y
conda activate eai-cosyvoice
conda install -y -c conda-forge pynini==2.1.5
python -m pip install -r requirements.txt
python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')"
```

检查完整模型快照、`pretrained_models/CosyVoice2-0.5B/cosyvoice2.yaml` 和 `third_party/Matcha-TTS/matcha/`，并记录快照版本；Git LFS 指针不能代替模型文件。

该版本的 `python example.py` 默认运行 CosyVoice3；本实验使用下方 CosyVoice2 入口。

#### 3.5.2 合成与播放

第一次可使用该提交自带的 `asset/zero_shot_prompt.wav`。在手册的 `runs/dialogue/prompt.txt` 中保存与之对应的参考文本：

```text
希望你以后能够做的比我还好呦。
```

使用 3.4 生成的 `answer.txt`；若问答尚未通过，可先在该文件写一句待合成文本，单独验证 E。回到手册仓库根目录，保持 `eai-cosyvoice` 环境；将命令中的 `/你的目录/CosyVoice` 替换为实际绝对路径：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py tts --repo "/你的目录/CosyVoice" --text-file runs/dialogue/answer.txt --prompt-text-file runs/dialogue/prompt.txt --prompt-wav "/你的目录/CosyVoice/asset/zero_shot_prompt.wav" --output runs/dialogue/reply.wav
```

参考音频与其准确转写均为必需输入。使用本人或获授权的声音，音频不超过 30 秒。输出片段按模型采样率拼接为一个 WAV，不自动播放或上传。

**结果检查**：播放 `reply.wav`，对照 `answer.txt` 检查漏句、误读、爆音和语速；上游问题或回答有误时先修正对应阶段。

### 3.6 摄像头与文件级集成（F）

#### 3.6.1 图像采集

```bash
conda activate eai-dialogue
python -m pip install opencv-python
python docs/assets/ch3-dialogue/dialogue_lab.py capture --camera 0 --output runs/dialogue/camera_scene.jpg
```

`capture` 会立即打开摄像头，保存最后一个有效帧并释放设备；执行前确认使用许可。图片仅保存在本机，不录音、不上传。`--camera 0` 为默认编号；打开失败时检查权限、设备占用和实际编号。核对图片后，可按 3.2 使用 `--image runs/dialogue/camera_scene.jpg` 问答。

#### 3.6.2 文件级集成

各模块按以下文件顺序衔接：

```text
question.wav → SenseVoice → question.txt
camera_scene.jpg → BLIP → caption.txt
question.txt + caption.txt → 文本API → answer.txt
                                         ↓
zero_shot_prompt.wav + prompt.txt → CosyVoice2 → reply.wav → 人工播放
```

按教材 3.4.3 的图像描述路线操作：先在 `eai-sensevoice` 环境执行 3.4 命令得到 `question.txt`，人工核对；再从手册根目录执行：

```bash
conda activate eai-dialogue
python docs/assets/ch3-dialogue/dialogue_lab.py caption --image runs/dialogue/camera_scene.jpg --device cpu --output runs/dialogue/caption.txt
```

立即用 PowerShell 的 `$LASTEXITCODE` 或 Bash 的 `echo $?` 检查退出码。**非 0 时停止，不调用 API 或沿用旧 caption。** 退出码为 0 后，打开本轮 `caption.txt`，确认非空且对应 `camera_scene.jpg`；同时确认 `question.txt` 来自本轮录音，再执行：

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-turbo --question-file runs/dialogue/question.txt --caption-file runs/dialogue/caption.txt --output runs/dialogue/answer.txt --send
```

API 退出码为 0 后，打开本轮 `answer.txt` 核对，再激活 `eai-cosyvoice` 执行 3.5 的 TTS 命令。任一步退出非 0 就停止并排错，不继续使用上次运行的同名文件。

**直接图像路线**：也可用下面的视觉 API 命令替换 caption 与文本 API 两步，再执行同一条 TTS 命令；记录为“直接图像输入”，与 BLIP 路线分开比较。

```bash
python docs/assets/ch3-dialogue/dialogue_lab.py api --model qwen-vl-plus --question-file runs/dialogue/question.txt --image runs/dialogue/camera_scene.jpg --output runs/dialogue/answer.txt --send
```

本节逐段处理文件并人工播放结果，不包含实时录音或打断功能。

**结果检查**：保留同轮录音、图片、转写、caption、回答和合成音频；对照原始问题与画面，逐项核对内容，确认最终音频回答了本轮问题。

### 3.7 本地模型部署

#### 3.7.1 Qwen-7B-Chat

在本机完成三轮文字对话，用 `history` 传递上下文。模型与接口依据[第一代 Qwen 模型卡](https://huggingface.co/Qwen/Qwen-7B-Chat)及教材 69—71 页。

| 项目 | 配置与条件 |
|---|---|
| 模型与接口 | 第一代 `qwen/Qwen-7B-Chat`，使用 ModelScope、`transformers==4.32.0` 和 `model.chat(...)` |
| 硬件与空间 | 使用教师确认可承载该模型的 Linux GPU 机器。教材标注模型文件约 14.4 GB；运行还需显存中的激活、缓存等空间，14.4 GB 不是最低显存要求 |
| 环境条件 | 需教师提供兼容的 torch/驱动版本和完整模型快照；下方依赖组合尚未实测，安装冲突时保留报错并领取环境锁文件 |

从手册仓库根目录创建独立环境，按课程驱动和 [PyTorch 安装说明](https://pytorch.org/get-started/locally/)安装兼容的 torch，再执行下方导入检查。

```bash
conda create -n eai-qwen-original python=3.9 -y
conda activate eai-qwen-original
python -m pip install modelscope "transformers==4.32.0" accelerate tiktoken einops scipy "transformers_stream_generator==0.0.4"
python -m pip check
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

确认下载额度和磁盘后执行以下命令，将模型保存到 `runs/dialogue/qwen-cache/`，并记录实际路径：

```bash
python -c "from pathlib import Path; from modelscope import snapshot_download; p=snapshot_download('qwen/Qwen-7B-Chat', cache_dir='runs/dialogue/qwen-cache'); Path('runs/dialogue/qwen-model-path.txt').write_text(str(Path(p).resolve()), encoding='utf-8')"
```

已有离线快照时，跳过下载，在 `runs/dialogue/qwen-model-path.txt` 写入完整快照绝对路径。保存下面代码为 `runs/dialogue/local_qwen.py`，再从手册根目录执行它。这里沿用教材的 ModelScope 导入；`trust_remote_code=True` 会执行模型快照中的 Python，只加载核对过来源和版本的模型。

```python
from pathlib import Path
from modelscope import AutoModelForCausalLM, AutoTokenizer

root = Path("runs/dialogue")
model_dir = (root / "qwen-model-path.txt").read_text(encoding="utf-8-sig").strip()
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_dir, device_map="auto", trust_remote_code=True
).eval()
history = None
records = []
for question in ["你好", "给我讲一个年轻人奋斗创业最终取得成功的故事。", "给这个故事起一个标题"]:
    answer, history = model.chat(tokenizer, question, history=history)
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("模型未返回文字，停止本轮实验。")
    records.append(f"问题：{question}\n回答：{answer}")
(root / "local_qwen_answers.txt").write_text("\n\n".join(records), encoding="utf-8")
print("已保存 runs/dialogue/local_qwen_answers.txt，请人工核对三轮上下文。")
```

```bash
python runs/dialogue/local_qwen.py
```

**结果检查**：三轮均有回答，第三轮标题对应第二轮故事；保存输出、模型快照 revision、驱动和依赖版本。若改用其他模型，单独记录为替代练习，并注明模型和接口。

#### 3.7.2 MiniCPM-V-2.6

在 AutoDL GPU 实例中通过 `run.ipynb` 加载多模态模型，输入图片和问题并保存回答。教材印刷页 72—73 的示例配置如下：

| 项目 | 教材示例 |
|---|---|
| 社区镜像显示名 | `OpenBMB/MiniCPM-V/MiniCPM-V-2.6` |
| GPU | RTX4090 24 GB；实际配置需按交付镜像确认 |
| 工作目录 | `/root/MiniCPM-V` |
| 模型路径 | `pretrained_weights/MiniCPM-V-2_6` |

**运行资料待补齐**：唯一镜像 ID/版本、完整 `run.ipynb`、依赖清单和模型 revision 尚未提供，需向教师领取并确认镜像当前可用后再启动实例。上述 GPU 为教材示例，并非最低硬件要求；本路线尚未实测。

**资料补齐后的步骤**：确认预算和 GPU 配置 → 选择指定镜像 → 在 JupyterLab 进入工作目录 → 逐格执行 `run.ipynb` → 输入图片和问题 → 保存已执行 notebook、回答及环境版本。输出目录以交付 notebook 为准。

**结果检查**：模型加载成功，回答与图片主要内容对应。加载失败时核对镜像/模型 revision、依赖和显存。资料未齐可先完成 B 路线，其结果单独记录。

## 四、实验结果

按第一节的完成标准逐条验收，提交环境与模型版本、运行命令、实际输出，以及至少一个失败或不确定案例的定位过程。使用[运行记录模板](../assets/ch3-dialogue/run-record-template.md)保存记录，未执行的路线标注“未运行”。

| 路线 | 主要输出 |
|---|---|
| A/B | `text_answer.txt` / `vision_answer.txt` 及对应 JSON |
| C | `caption.txt`、`caption_answer.txt` 及对应 JSON |
| D/E | `question.wav`、`question.txt`、`answer.txt`、参考音频/文本、`reply.wav` |
| F | 同轮图片、录音、转写、caption、回答和合成音频 |
| 本地 Qwen / MiniCPM | 三轮对话文本 / 已执行 notebook 和图文回答 |

输出保留在 `runs/dialogue/`，MiniCPM 输出以云端 notebook 为准。不提交密钥、私人图片或模型文件。已验证范围与资料缺项见[检查记录](../assets/ch3-dialogue/verification.md)。

## 五、排错建议与注意事项

| 现象 | 检查项 | 处理方法 |
|---|---|---|
| `CHECK ONLY`，但没有回答文件 | 是否少了 `--send` | 确认模型与费用后再发送，不把检查提示当模型输出 |
| 提示Key未设置 | 是否在当前终端设置，是否换了终端 | 只检查存在性，勿打印Key截图 |
| 401 / 403 | Key、业务空间、地域、模型权限 | 按百炼控制台调用示例核对，不无限重试 |
| 429 / 额度错误 | 限流、余额或额度 | 先停止批量调用，按平台提示处理 |
| 导入失败 | 当前Python解释器和Conda环境 | 在对应环境安装，不混装语音和图像依赖 |
| 本地 Qwen 显存不足 | GPU 型号、可用显存和其他进程占用 | 保存报错与显存信息，向教师确认可用资源 |
| 本地 Qwen 无 `model.chat` | 模型代际、快照版本、模型代码加载 | 核对第一代 Qwen 快照，确认已审核的模型代码可通过 `trust_remote_code` 加载 |
| 本地 Qwen 依赖冲突 | `eai-qwen-original` 环境及 `pip check` 输出 | 保留报错并向教师索取可用的历史环境锁文件；不在 A—C 环境降级 Transformers |
| 模型下载慢或失败 | 模型地址连通性、缓存目录、磁盘 | 保留完整快照及版本；不要反复删除缓存重下 |
| BLIP漏掉小物体 | 输入图清晰度及caption本身 | 对照原图；文本模型不能恢复从未传给它的细节 |
| SenseVoice输出不对 | 先听原录音 | 检查静音、噪声、格式和语言，不先改LLM提示词 |
| TTS加载错误 | CosyVoice源码提交、模型代际、子模块 | 核对本页指定接口，勿混用旧张量与新路径写法 |
| 有WAV但听起来不对 | 回答文本、参考文本、输出采样率 | 实际播放后逐段定位，不只检查文件大小 |
| 摄像头打不开 | 隐私权限、设备编号、占用 | 关闭占用程序，再单独采一帧 |

**思考题**：同一幅图通过B、C两条路线得到不同回答，能否确定是谁出错？应保存哪些中间结果？将问题换成图片中看不见的细节时，模型应怎样回答？加入语音后，如何区分ASR错误与推理错误？

阅读：[百炼视觉输入与本地文件说明](https://help.aliyun.com/zh/model-studio/vision)、[BLIP模型卡](https://huggingface.co/Salesforce/blip-image-captioning-base)、[课程SenseVoice示例](https://github.com/SH9959/EAI_project/blob/e6bb5d5de828b5d87834ea169b53c09b376d8b09/chapter_3/3_3_human_perception/3.3.3/SenseVoice/demo1.py)、[本页采用的CosyVoice示例](https://github.com/QwenAudio/CosyVoice/blob/074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc/example.py)。
