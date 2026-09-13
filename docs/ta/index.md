# 助教手册：总览

助教的目标不是替学生完成实验，而是保证实验环境、代码、仿真器和实机设备处于**可完成实验**的状态，并能快速判断学生卡在哪一层。

## 先记住四层排查法

```text
环境层：Python / CUDA / ROS / 依赖是否正确？
    ↓
输入层：图像 / 深度 / 音频 / 关节状态是否正常？
    ↓
模型层：API / checkpoint / 推理输出是否正常？
    ↓
执行层：仿真器 / 机器人是否真正执行了正确动作？
```

学生报错时先判断属于哪一层，再处理；不要从头重装整个环境。

## 各实验助教关注点

| 实验 | 课前必须确认 | 学生最容易卡住 |
|---|---|---|
| 人机对话 | API Key 流程、SenseVoice demo | Key、模型下载、CUDA/torchaudio |
| AnyGrasp | SDK、License、checkpoint、GPU | MinkowskiEngine、坐标系、License |
| ALFWorld | `alfworld-download` 完成 | 资源未下载、渲染环境 |
| ALFRED | 数据 / checkpoint | 路径配置、环境 reset 卡住 |
| AI2THOR | 课程 demo + Key | AI2THOR 启动、动作不合法、模型提前 done |
| VirtualHome | Unity 可执行程序 | 本机路径、Windows 依赖、脚本动作无效 |
| 方块重排/汉诺塔 | 相机、机械臂、夹爪、视觉和抓取链路 | 坐标系、逆解、碰撞、规划格式 |
| iGibson | GPU、资产、场景启动 | 驱动/CUDA、资产下载 |
| ACT 仿真 | 采集、可视化、训练、eval 各跑一次 | MuJoCo/dm_control、数据路径 |
| cobot-magic | CAN、ROS、3 路相机、主从臂 | USB/CAN 映射、ROS 节点、相机话题 |

## 原则

1. **每次实验至少保留一台“已验证机器”**，不要课前统一升级环境；
2. 实机实验前先跑传感器和单动作，再跑完整任务；
3. 大模型规划必须经过动作合法性检查后才能进入执行层；
4. 所有实机问题优先保证人和设备安全，不以“继续跑完”为目标。
