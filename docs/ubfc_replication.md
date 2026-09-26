# 固定小样本扩展与独立敏感性分析

更新：subject1、4、5 的视频已由用户上传，已完成两模型推理与单独冻结的完全重复 GT 清理补充分支。新增结果、三段视频及严格/补充口径见 [新上传样本报告](ubfc_uploaded_replication.md)。下文保留最初冻结清单、下载受阻和原严格质量失败的历史记录，不代表当前仍缺视频。

原 subject3 协议、模型输出、评价结果及既有诊断均未改变，71 个既有文件的 SHA-256 校验通过。新增 主结果表 (local artifact: `results/ubfc_replication/primary_results.csv`) 与 窗函数敏感性分析表 (local artifact: `results/ubfc_replication/sensitivity_results.csv`) 分开保存；后者不进入主评价 MAE，不选择最接近设备 HR 的算法。

![Reference PPG spectral sensitivity: a single-recording case study](../results/ubfc_replication/subject3_reference_sensitivity_en.png)

左侧明确标出 88、102 bpm 两个候选峰：同样本 Hann 选择 88，矩形窗选择 102。右侧两种窗函数都选择 92 bpm，表现为相对稳定，但仍与设备 HR 中位数 105 不一致。这里比较的是相同 30 Hz 插值后的原始接触 PPG，无带通、无零填充；不是重算或替换模型主结果。英文展示版的每条曲线分别除以其在 45–150 bpm 范围内的峰值。该图用于比较峰的位置与相对形状，不能比较两种处理的绝对功率。它是单段录像的两个窗口，不能据此确定真实心率，也不能代表整个 UBFC 数据集。

原中文图采用每面板共享归一化尺度，仍保留为 原展示版本 (local artifact: `results/ubfc_replication/subject3_peaks_side_by_side.png`)。英文版只修改展示语言、说明与纵轴缩放，原 PSD、候选峰、设备值及主评价全部保持不变。

英文图可导出为 [PNG](../results/ubfc_replication/subject3_reference_sensitivity_en.png)、[PDF](../results/ubfc_replication/subject3_reference_sensitivity_en.pdf)、[SVG](../results/ubfc_replication/subject3_reference_sensitivity_en.svg)。

**事先固定的清单与判据**

[冻结协议](../configs/ubfc_replication_v1.json) 在本轮读取新增样本频谱或预测结果前保存，时间与 SHA-256 见 [protocol_lock.json](../results/ubfc_replication/protocol_lock.json)。按已存档官方 DATASET_2 目录中编号递增顺序，排除已分析 subject3，取 subject1、subject4、subject5。subject1 的 GT 先前已下载；其模型结果未用于选择。subject3 属于探索参照，不计入新增样本的重复验证统计。

每个新增样本检查固定 0,30)、[30,60) 秒，共计划 6 窗。窗口不足、质量检查失败或下载失败仍列在表内，不缩短窗口、不换受试者。主评价继续使用原采样规则、权重、去趋势 λ=100、一阶 0.75–2.5 Hz 双向滤波、30 秒 Hann 无零填充频谱。ROI 按首帧图像在推理和新增 GT 频谱检查之前固定；不根据模型输出调整。不搜索时延，不翻转信号，不训练。

单独的敏感性分析使用同一 30 Hz 原始插值 PPG 比较 Hann 与矩形窗。事先固定的描述性“竞争峰”标记为：Hann 搜索带内功率最大的两个内部局部峰，间隔至少 6 bpm，第二峰/第一峰功率比至少 0.5；另记录两窗函数主峰相差至少 4 bpm 的标记。阈值仅用于描述，不是验证过的质量标准，不用于排除窗口；连续功率比和完整频谱一并保存。它们是看过 subject3 后为新增样本固定的判据，不能称作对 subject3 的前瞻验证。

subject3 第一窗两峰比约 0.781，第二窗约 0.203，与图中的竞争/相对稳定关系一致；仍不能仅凭它判断生理真实 HR。

**当前扩展进度：已完成数据清单与输入检查，重复性验证尚未完成**

三个新增 GT 均已取得；三个视频都被官方 Google Drive 下载配额阻止，返回 `Quota exceeded`，响应已保存在 `results/ubfc_replication/`。没有替换样本或使用非官方镜像。尚未运行新增模型推理或查看新增 GT 频谱，不能声称竞争峰或模型表现已经在新增样本重复出现。

| 样本 | GT 点数 | GT 覆盖 / 秒 | 完全重复记录的零基索引 | 重复时间 / 秒 | 视频状态 |
|---|---:|---|---|---:|---|
| subject1 | 1547 | 0–52.691 | 494、495 | 16.750 | 下载配额限制 |
| subject4 | 1368 | 0–46.234 | 857、858 | 29.023 | 下载配额限制 |
| subject5 | 1550 | 0–52.368 | 19、20 | 0.670 | 下载配额限制 |

三个文件都各有一对时间戳相同且 PPG、HR 也完全相同的相邻记录，未通过冻结协议继承的“时间严格递增”检查。三个记录也都不足 60 秒，第二个固定窗口缺少完整参考覆盖。当前新增主评价为 **0/6 窗已评价**，不能将其记成零误差，也不能将 subject3 当成新增验证成功。完整原因和原文件哈希见 [sample_inventory.json (local artifact: `results/ubfc_replication/sample_inventory.json`)。

没有偷偷去重、加微小时间偏移或把短窗口凑成 30 秒。若后续进行完全重复记录的确定性去重，应另外固定并命名数据清理分支、保留原始失败记录和索引映射，不能覆盖本轮冻结协议或将其与严格主分析混为一谈。视频到位仍需要检查真实帧数、PTS 与 GT 对应，并处理这一质量问题，不能直接跳过检查计算模型指标。

**需要补充的视频及上传位置**

GT 已在各自目录中，只需要原始 `vid.avi`。以下是本次从官方目录核对的链接和字节数：

| 样本 | 官方视频 | 预期字节数 | 上传完整路径 |
|---|---|---:|---|
| subject1 | [下载/查看](https://drive.google.com/file/d/1qBlkbaB8y3-KlWC_A61KsY42Wjo66ss4/view) | 1425830568 | `data/ubfc_subject1/vid.avi` |
| subject4 | [下载/查看](https://drive.google.com/file/d/1w00W_8bNiKKLvZ-p3n3iESLG_gr9AOoz/view) | 1260858440 | `data/ubfc_subject4/vid.avi` |
| subject5 | [下载/查看](https://drive.google.com/file/d/1yGaYtOAGYzI4UOIN-XArEl88eRjRarTc/view) | 1428595464 | `data/ubfc_subject5/vid.avi` |

目录已创建，subject3 文件未动。下载失败是远端配额限制，不是操作审批被拒绝。

本轮复现命令：

```bash
.venv/bin/python scripts/plot_ubfc_peak_comparison.py
.venv/bin/python scripts/audit_ubfc_replication.py
```

`audit_ubfc_replication.py` 是本轮冻结时点的输入清单与表格生成脚本，不是推理入口；视频到位后须先完成首帧 ROI 固定与时间审计，再使用模型推理入口。主结果表中的 subject3 数值直接复制既有评价，未重算；新增行均保留未评价状态。
