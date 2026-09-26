# 官方代码与权重核查

## MTTS-CAN

- 仓库：https://github.com/xliucs/MTTS-CAN
- 固定commit：`89ffe818e1701ebcc156d4193657258e506eb781`
- 权重：仓库根目录 `mtts_can.hdf5`，校验和及大小见configs/sources.json。
- 许可证：MIT，Copyright (c) 2020 Xin Liu，完整原文留在第三方仓库。
- 训练来源：[issue #5](https://github.com/xliucs/MTTS-CAN/issues/5) 中作者xliucs答复AFRL，明确答复不是MMSE-HR/UBFC。
  权重哈希没有逐受试者训练清单，因此本项目不作完全可审计的训练重叠证明。
- 历史不匹配风险：[issue #13](https://github.com/xliucs/MTTS-CAN/issues/13) 作者提及Hybrid-CAN权重。
  当前本地文件内的序列化模型结构实际为4个TSM、10个卷积层、两个128维Dense分支与两个标量输出。
  不能把历史issue的结论直接套到当前文件；最终以层名和张量逐项匹配、保存模型图对照和前向检查为准。

### 结构与输入

实际调用 `MTTS_CAN(10,32,64,(36,36,3))`。
两个NHWC张量 `(N,36,36,3)`，分别为归一化RGB帧差和标准化RGB外观。
时间维折叠在批维中，N和每批大小必须为10的倍数。TSM在每10帧内按通道分组做前后移位及补零。
外观支路生成注意力掩码，运动支路应用掩码，之后共用特征进入两个回归头。
默认演示采样率30Hz；模型没有接收采样率输入，改变视频帧率会改变其时间语义。

官方 `inference_preprocess.py` 没有检测或跟踪人脸。它中心裁剪、缩放、无条件顺时针旋转90°，
由README提醒用户自行检查方向。它采集时间戳但没有返回它们，也没有自动重采样。
本项目补充保存PTS和输入检查，具体适配见protocol.md。

**训练/推理代码差异**：`data_generator.py` 的MTTS_CAN分支会把外观帧在10帧块内求均值并重复；
`predict_vitals.py` 则直接使用逐帧外观输入。本阶段采用作者实际推理脚本的逐帧方式，
没有自行加入平均，不宣称完全重现训练数据管线。

### 输出和后处理

`output_1`是脉搏，`output_2`是呼吸，各为 `(N,1)`；数据生成器对应`dysub`和`drsub`。
官方预测脚本对两者分别cumsum，再Tarvainen去趋势、Butterworth带通。
因此网络输出按差分信号处理，不是HR/RR数值，也不是已校准物理单位波形。
仓库没有提供原始生理标签生成的完整可执行数据流程，不能额外推断其物理幅值标定。
最终波形单位为arbitrary units；频率×60分别为beats/min与breaths/min。

论文描述二阶Butterworth，而当前官方预测脚本调用butter(1,...)；本项目固定采用实际代码的一阶带通原型，明确不将其称为论文评价协议的完整复现。

本项目仅对私有Keras导入作兼容替换，保留官方结构与预训练参数；无训练、无部分权重加载。
严格加载、逐层映射和随机前向记录在results/mtts_audit.json；私有Keras版本仅形状匹配却装错4个卷积层，判定无效。公开Keras版本每层匹配，且与权重内保存的模型图重建结果完全一致（results/mtts_serialized_graph_check.json）。随机输入不算生理实验。
稀疏去趋势与官方稠密公式的数值等价检查见results/signal_math_check.json。

## BigSmall

原仓库commit `0e6c391c26ed66519340c8b9e85689f827518a42`，MIT许可证。
推荐Toolbox固定commit `b7500b848f84ad7f86e277b4612563b69f4f88f9`，
Responsible AI Source Code License v1.1，**不是MIT**。许可证原文各自保留。

两者均公开3个BP4D+多任务折的权重，每个8,580,229字节，本项目仅获取Fold/Split1：

- 原仓库：`code/pretrained_models/BP4D_BigSmall_Multitask_Clip3_Split1_Epoch4.pth`
- Toolbox：`final_model_release/BP4D_BigSmall_Multitask_Fold1.pth`

两个文件SHA256不同，不能仅凭文件名认定参数相同；实际张量和前向对照由
`results/bigsmall_audit.json`记录。Toolbox权重引入于
[728a73e](https://github.com/ubicomplab/rPPG-Toolbox/commit/728a73e6f4179634962d7c7a76df298edf4831d4)，
提交日期2023-06-07，作者说明核验过论文结果。该说明不等于本项目重现了论文指标。
当前版本与原仓库模型分别为`BigSmall`和`BigSmallSlowFastWTSM`。
实际CPU审计均严格加载成功，32个state_dict张量、2,142,478个参数，三路输出均为有限值。
两份权重最大张量绝对差0.57825446，同一随机输入的输出最大绝对差2.57646441；
这是参数与软件行为核查，不是生理准确性对比。

### 实际输入输出

两路NCHW输入：`(N,3,144,144)`外观，`(N,3,9,9)`运动；N为3的整数倍。
默认25Hz。大支路只取每3帧中的首帧，卷积后重复特征3次；小支路使用环绕时间移位WTSM。
源码中重复次数硬编码为3，不能随意改frame_depth。

Toolbox预处理先把RGB帧缩放至144×144，以全视频均值和标准差标准化大输入；
小输入是在144×144上先作相邻帧归一化差分、除以差分标准差、尾部补零，再缩小至9×9。
**不能把先缩小再差分当作同一实现**。该模型不需要MTTS-CAN的90°旋转。
BP4D读取器包含针对原数据几何的底部方形裁剪；配置关闭人脸检测。
本项目MIT演示另用已固定的面部ROI并明确记录，不宣称完整复现BP4D预处理。

返回顺序是 `au_out,bvp_out,resp_out`，形状分别`(N,12),(N,1),(N,1)`。
AU是logits，本项目只保留原始值，不做表情或心理状态解释。另两头是按差分标签学习的输出，
需cumsum、去趋势和滤波后估计频率，不是直接输出HR/RR。

### 训练来源和任务边界

原仓库README和Split1配置以及Toolbox训练器均使用BP4D+ AU标注子集的3折划分。
训练脉搏标签名为`pos_env_norm_bvp`：POS生成伪PPG，使用接触HR约束滤波频带，
再以Hilbert幅度包络归一化。它不是未经处理的接触PPG真值；呼吸标签为`resp_wave`，
来自`Resp_Volts.txt`，两者还作差分标准化。
Toolbox测试脉搏参考使用`bp_wave`；其BP波形仅用来提取节律，不代表模型会测量血压。
权重缺少详细逐样本训练日志，不能宣称已审计所有训练重叠或泛化。

仅加载模型类与官方checkpoint，`load_state_dict(strict=True)`、逐key检查、`eval()`、
`torch.inference_mode()`；剥离DataParallel的module.前缀前检查所有key均具有该前缀。
不执行训练器或训练入口。当前官方YAML默认train_and_test，本项目**不运行该命令**。
Toolbox CPU训练器还存在num_of_gpu=0导致base_len=0的问题，独立模型推理包装避免依赖它。

### 本地演示协议

先完成MTTS-CAN流程，再运行BigSmall Fold1。同一个MIT原始视频通过源PTS最近邻映射为25Hz，
保留目标时刻、源帧编号和实际源PTS；该重采样本身可能影响预测。
采用Toolbox当前实际后处理：lambda100，一阶Butterworth，HR频带0.6–3.3Hz，
RR频带0.13–0.5Hz，filtfilt；矩形窗periodogram、无额外去均值、FFT补零到下个2次幂。
补零只加密频率网格，不提高10秒记录的真实分辨率。
这与MTTS-CAN的频带和Hann谱协议不同，分别展示，不排名。

### 与TS-CAN的区别

当前Toolbox的`TS_CAN.py`确实同时定义单输出`TSCAN`和一个双任务`MTTS_CAN`类。
发布目录中的PURE/UBFC等`*_TSCAN.pth`不能因此当作MTTS-CAN双任务权重；
本项目没有用这些单任务权重替代呼吸输出。实际双任务MTTS验证使用xliucs原始HDF5。
