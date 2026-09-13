# 第 3 章：人机对话与多模态交互

> 对应教材：**3.4.1 人机对话实验、3.4.2 结合图像小模型、3.4.3 实机部署**。

## 你将完成什么

这一组实验从最简单的文本问答开始，逐步把图像、语音和摄像头接入同一个交互系统：

```text
文本输入 → 大模型 → 文本回答
              ↑
图像 → 图像描述 ┘

麦克风 → SenseVoice → 文本 → 大模型 → 文本 → CosyVoice → 扬声器
摄像头 ───────────────→ 图像描述/多模态输入 ────────────────┘
```

## A. 最小实验：API 调用文本大模型

这是最容易跑通的一条路线，建议所有同学先完成。

### 1. 安装依赖

```bash
conda create -n dialogue python=3.9 -y
conda activate dialogue
pip install dashscope
```

### 2. 配置 Key

```bash
export DASHSCOPE_API_KEY="你的Key"
```

### 3. 调用模型

```python
import os
import dashscope
from http import HTTPStatus

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "如何做西红柿鸡蛋？"},
]

response = dashscope.Generation.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-turbo",
    messages=messages,
    result_format="message",
)

if response.status_code == HTTPStatus.OK:
    print(response.output.choices[0].message.content)
else:
    print(response.code, response.message)
```

**成功判据：** 终端能够返回模型生成的自然语言回答。

## B. 多模态大模型：图片 + 问题

教材给出的路线是使用 `MultiModalConversation` 直接传入本地图片。核心输入由两部分组成：图片路径和文本问题。

```python
from dashscope import MultiModalConversation

messages = [{
    "role": "user",
    "content": [
        {"image": "file:///你的绝对路径/image.jpg"},
        {"text": "图片里有什么东西？"},
    ],
}]

response = MultiModalConversation.call(
    model="qwen-vl-plus",
    messages=messages,
)
print(response)
```

**成功判据：** 回答能描述输入图片中的主要物体或场景。

## C. 图像小模型 + 文本大模型

教材 3.4.2 使用 **BLIP Image Captioning** 先生成图像描述，再将“图像描述 + 用户问题”交给文本大模型。

### 1. 安装

```bash
conda activate dialogue
pip install transformers pillow torch requests
```

### 2. 生成图像描述

```python
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

image = Image.open("face.png").convert("RGB")
inputs = processor(image, return_tensors="pt")
out = model.generate(**inputs)
caption = processor.decode(out[0], skip_special_tokens=True)
print(caption)
```

随后把 `caption` 和用户问题一起送入文本大模型即可。

**理解重点：** 这里不是让文本模型直接“看图”，而是让视觉小模型先把图像转成语言，再由文本模型完成后续回答。

## D. 语音识别：SenseVoice

### 课程代码

[`chapter_3/3_3_human_perception/3.3.3/SenseVoice`](https://github.com/SH9959/EAI_project/tree/main/chapter_3/3_3_human_perception/3.3.3/SenseVoice)

其中教材对应的最直接测试脚本是 [`demo1.py`](https://github.com/SH9959/EAI_project/blob/main/chapter_3/3_3_human_perception/3.3.3/SenseVoice/demo1.py)。

### 运行

```bash
cd ~/EAI_project/chapter_3/3_3_human_perception/3.3.3/SenseVoice

conda create -n sensevoice python=3.9 -y
conda activate sensevoice
pip install -r requirements.txt

python demo1.py
```

教材要求 `funasr >= 1.1.2`，并提醒 `torchaudio` 版本过旧可能报错。

要识别自己的音频，把脚本中的：

```python
input=f"{model.model_path}/example/zh.mp3"
```

改成自己的音频文件路径。

**成功判据：** 终端打印出音频的文字转写结果。

![SenseVoice WebUI](../assets/sensevoice_webui.png)

## E. 语音合成：CosyVoice

教材使用 CosyVoice 把大模型的文本回答重新转换为语音。

```bash
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice

git clone https://www.modelscope.cn/iic/CosyVoice2-0.5B.git pretrained_models/CosyVoice2-0.5B

conda create -n cosyvoice -y python=3.10
conda activate cosyvoice
conda install -y -c conda-forge pynini==2.1.5
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com
```

运行官方零样本合成示例，确认能生成 `.wav` 文件后，再把大模型回答接到 TTS 输入。

## F. 集成完整交互

最终把四个模块串起来：

1. 麦克风采集语音；
2. SenseVoice 转成文本；
3. 文本（以及需要时的摄像头图像）送入大模型；
4. 得到文字回答；
5. CosyVoice 合成语音并播放。

!!! tip "调试顺序"
    不要一开始就把所有模块接在一起。按照 **SenseVoice → LLM → CosyVoice → 摄像头 → 完整集成** 的顺序逐个验证，哪一步出错就只检查那一个模块。

## 实验完成检查

- [ ] 文本大模型 API 可以正常回答；
- [ ] 多模态模型或 BLIP 能处理一张本地图像；
- [ ] SenseVoice 能转写自己的音频；
- [ ] CosyVoice 能生成语音文件；
- [ ] 扩展实验中，至少完成一条“语音输入 → 模型回答”的完整链路。
