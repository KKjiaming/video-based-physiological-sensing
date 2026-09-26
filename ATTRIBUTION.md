# 原作者贡献与本项目贡献

- **MTTS-CAN模型、预训练参数和原始推理方法**：Xin Liu, Josh Fromm, Shwetak Patel, Daniel McDuff. *Multi-Task Temporal Shift Attention Networks for On-Device Contactless Vitals Measurement*, NeurIPS 2020. 官方仓库：https://github.com/xliucs/MTTS-CAN 。MIT License，Copyright (c) 2020 Xin Liu；完整许可证保留在[licenses/MTTS-CAN-LICENSE.txt](licenses/MTTS-CAN-LICENSE.txt)。
- **BigSmall模型及相关论文**：Girish Narayanswamy, Yujia Liu, Yuzhe Yang, Chengqian Ma, Xin Liu, Daniel McDuff, Shwetak Patel. *BigSmall: Efficient Multi-Task Learning for Disparate Spatial and Temporal Physiological Measurements*, WACV 2024. https://github.com/girishvn/BigSmall 。MIT许可证，完整原文保留在[licenses/BigSmall-LICENSE.txt](licenses/BigSmall-LICENSE.txt)；核查见docs/methods.md。
- **rPPG-Toolbox**：官方维护者及论文作者的模型、数据加载器、评价工具与发布权重。https://github.com/ubicomplab/rPPG-Toolbox 。Responsible AI Source Code License v1.1，完整原文保留在[licenses/rPPG-Toolbox-LICENSE.txt](licenses/rPPG-Toolbox-LICENSE.txt)。不把工具箱单任务TS-CAN称为MTTS-CAN。
- **演示视频**：Hao-Yu Wu, Michael Rubinstein, Eugene Shih, John Guttag, Frédo Durand, William T. Freeman. *Eulerian Video Magnification for Revealing Subtle Changes in the World*, ACM Transactions on Graphics 31(4), 2012. https://people.csail.mit.edu/mrub/evm/ 。使用作者提供的原始视频，进行了裁剪、缩放和信号预测，未做颜色放大。

本项目新增工作：环境与版本审计、预训练权重和结构核对、兼容性适配、可重复本地推理脚本、
时间与预处理记录、信号后处理、频率估计、结果可视化及限制分析。
这些是申请者可检查和进一步复核的复现工程与分析材料，不是原始模型发明、数据采集贡献，
也不是完整复现论文训练结果。本阶段没有训练或微调。

新增数据：Chen等，*MPU-rPPG: A Comprehensive and High-Fidelity Dataset for Remote Photoplethysmography Across Diverse Conditions and Demographics*, Scientific Data, 2026；作者Figshare记录10.6084/m9.figshare.29377835。数据归原作者，本项目新增固定样本推理、GT对比和本地视频展示。
UBFC检索材料与标签：S. Bobbia, R. Macwan, Y. Benezeth, A. Mansouri, J. Dubois, *Unsupervised skin tissue segmentation for remote photoplethysmography*, Pattern Recognition Letters；subject3视频随后由用户上传并用于推理；使用官方接触PPG标签，未发布原始数据。

公开仓库保留以上第三方许可证原文及来源配置，不打包第三方仓库、权重或数据。尚未为本项目自身新增顶层 LICENSE；这些第三方声明不等于给整个项目统一指定许可证。
