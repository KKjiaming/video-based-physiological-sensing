# 补充实验：公开接触PPG真值与视频可视化

2026-09-26。此前MIT实验只能证明推理管线能运行。本次继续寻找真实参考数据，已经完成
MPU-rPPG作者公开样本的两模型推理、接触PPG对比与视频展示；结果不支持声称测量准确。

## 可直接检查的结果

- [预测与真实接触PPG对比图](../results/mpu_gt_review/gt_comparison.png)
- 带原视频、实际ROI、预测及接触PPG的30秒视频 (local artifact: `results/mpu_gt_review/video_with_gt.mp4`)
- 视频预览 (local artifact: `results/mpu_gt_review/preview.jpg`)
- [原始接触PPG及设备心率质量检查图](../results/mpu_gt_review/reference_quality.png)
- [四个窗口的完整结果](../results/mpu_gt_review/comparison.json)
- 原MIT视频的双模型同步展示，无GT (local artifact: `results/mit_video_review/video_with_predictions.mp4`)

视频是离线分析，显示的心率来自完整30秒窗口，不是逐帧实时测量；波形显示也使用了完整片段的
归一化和双向滤波。没有添加虚构的生理热图、拟合时延、信号翻转或GT曲线。

## 来源与可核查的同步依据

作者论文：[Chen等，MPU-rPPG，Scientific Data](https://www.nature.com/articles/s41597-026-07310-3)。
[作者公开样本](https://figshare.com/articles/dataset/MPU-rPPG_Sample_Dataset/29377835)，
元数据保存于`../results/gt_search/mpu_metadata.json`。Figshare标注CC BY 4.0，发布说明同时要求研究用途、
引用和不向未经授权第三方再分发；本项目仅本地使用，不上传或发布数据，没有提交完整数据集申请。

选用文件ID 55553417（MP4，127,996,277字节）与邻列55553414（CSV，700,580字节）。
两文件原名分别Output.mp4和Output.csv。先选该公开MP4和相邻CSV，再检查帧数、计数和MD5；
没有根据预测效果选择样本。相邻配对加上完全匹配的行数提供配对依据，但公开条目没有独立受试者ID清单。

实测视频640×480、60Hz、44,548帧；CSV有44,548行，Count连续0–44,547，包含PPG、HR、SpO2。
全部视频PTS与Count/60的最大差为0.334微秒（时间戳输出舍入精度）。作者描述使用采集时间戳和
起始闪光对齐，再按最近视频帧重采样，声称约±8ms精度。**本项目没有独立验证传感器同步误差**，
公开CSV也没有绝对时间戳或校准偏移字段；采用发布方帧对齐和固定零偏移，不从输出拟合延迟。
核查见`../results/gt_search/mpu_timing_check.json`。计数匹配证明结构相容，不等于重新证明生理同步。

仅在本地生成开头121秒的30Hz无损FFV1输入，保留60Hz源视频中的0、2、4…帧。
抽查0、30、60、90、120秒像素与原视频完全一致，见`mpu_lossless_pixel_check.json`。
固定ROI为x=190,y=70,w=h=260，由源图像确定，不根据预测修改。
BigSmall再按已有PTS规则取25Hz；最大误差记录在它的summary中。

MTTS权重作者报告训练于AFRL；BigSmall权重来自BP4D+。它们与MPU是不同命名数据源，
但缺乏逐受试者训练清单，不宣称已完成绝对训练重叠排查。

## 固定评价及实际观察

在模型推理前冻结`../configs/mpu_sample_protocol.json`。取开头121秒确保两个模型截断时序块后
仍有120秒可评价。保留全部四个30秒非重叠窗口，剩余不足一窗不计。两方法从积分输出重新计算：
去趋势lambda=100、一阶Butterworth双向带通0.75–2.5Hz、Hann periodogram、无零填充。
接触PPG不积分，先按各模型时间网格插值，再采用同一预定处理。30秒谱格间距为2次/分。
模型输入采样率及训练目标仍不同，因此不作算法整体优劣排名。

| 窗口（秒） | 接触PPG谱峰HR | 设备HR中位数，仅辅助 | MTTS-CAN预测 | BigSmall预测 |
|---|---:|---:|---:|---:|
| 0–30 | 78 | 80 | 78 | 100 |
| 30–60 | 78 | 80 | 48 | 100 |
| 60–90 | 72 | 76 | 58 | 100 |
| 90–120 | 104 | 72 | 50 | 100 |

单位均为次/分。相对接触PPG谱峰的描述性误差：

| 方法 | MAE | RMSE | 平均偏差 |
|---|---:|---:|---:|
| MTTS-CAN | 24.50 | 31.67 | -24.50 |
| BigSmall | 19.00 | 21.02 | +17.00 |

这是真实数据计算结果，不是合成测试；也不是已验证可靠的基准性能。主要观察：

- 两方法的零时延波形相关均较低；MTTS第一窗频率相同不代表波形吻合或整个片段准确。
- BigSmall四窗都选择100/min，未跟随参考频率变化；需要进一步独立数据诊断，不能解释为可靠稳定。
- **最后一窗接触PPG谱峰104/min与设备HR中位数72/min明显不一致**。设备可能有平滑/滞后，
  PPG也可能有伪影，目前原因未确认；未在看见差异后排除该窗或调整频带。原始信号和两种参考均保留。
- 固定裁剪、面部朝向/运动、输入分辨率、域差异、采样和参考质量都可能影响结果，当前不能把误差归因于某一项。
- 只有一段视频；既不能推断整个数据集性能，也不能用19<24.5宣称BigSmall更优。
- 没有呼吸传感器真值，两模型呼吸输出保存但不评价，不从PPG派生“呼吸GT”。

## UBFC下载受阻与用户补充位置

更新：用户已上传subject3视频，并完成两模型GT实验，见[UBFC报告](ubfc_report.md)。以下保留下载阶段记录。

[UBFC作者主页](https://sites.google.com/view/ybenezeth/ubfcrppg)现在提供公开Drive目录。
subject1与subject3的GT已取得，但原视频均返回Google“Quota exceeded”；没有绕过配额、登录或使用非官方镜像。
`Agreement.xlsx`是作者公布的受试者共享/展示许可表，不是本项目代签的协议。subject1/3均允许共享与展示，
subject21/27的禁止展示限制保留在官方readme中，本项目未使用它们。

用户可尝试下载[官方subject3文件夹中的vid.avi](https://drive.google.com/drive/folders/1tJdI-E143hW0q0NHxmPPkLcr0UvZgeNz)，
大小应为1,659,925,096字节，放到：

```text
data/ubfc_subject3/vid.avi
```

ground_truth.txt已在同一目录。文件到位后仍须检查容器时间、标签时间和帧对应关系，再运行评价，
不能直接套用MPU的60Hz计数规则。UBFC只有脉搏参考，没有呼吸GT。

另查到DIL-RR、VitalVideos的双真值资源仍需签署申请；没有代注册、申请或接受协议。

## 已验证复跑命令

```bash
python3 scripts/fetch_mpu_sample.py
.venv/bin/python scripts/prepare_mpu_sample.py
.venv/bin/python scripts/infer_mtts.py --config configs/mtts_mpu_sample.json
.venv/bin/python scripts/infer_bigsmall.py --config configs/bigsmall_mpu_sample.json
.venv/bin/python scripts/evaluate_signals.py \
  --prediction-dir results/mtts_mpu_sample \
  --ground-truth data/mpu_sample/ground_truth.csv --gt-offset-s 0 \
  --sync-note 'Publisher frame alignment; verified Count/60 matches PTS; no fitted lag; clock calibration not independently verified' \
  --pulse-band-hz 0.75 2.5 --output results/mtts_mpu_evaluation
.venv/bin/python scripts/evaluate_signals.py \
  --prediction-dir results/bigsmall_mpu_sample \
  --ground-truth data/mpu_sample/ground_truth.csv --gt-offset-s 0 \
  --sync-note 'Publisher frame alignment; verified Count/60 matches PTS; no fitted lag; clock calibration not independently verified' \
  --pulse-band-hz 0.75 2.5 --output results/bigsmall_mpu_evaluation
.venv/bin/python scripts/review_mpu_results.py
.venv/bin/python scripts/render_video_review.py
```

不训练、不微调、不发布。下一步优先验证用户补充的官方UBFC视频，分辨参考质量问题与模型/输入适配问题；
呼吸准确性仍需要独立呼吸真值数据。
