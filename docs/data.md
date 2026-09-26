# 数据来源、访问与限制

## 已获取的小样本

- 项目：Wu, Rubinstein, Shih, Guttag, Durand, Freeman. *Eulerian Video Magnification for Revealing Subtle Changes in the World*. ACM TOG / SIGGRAPH 2012.
- 发布方：[MIT CSAIL作者页面](https://people.csail.mit.edu/mrub/evm/)。
- 原始视频：[face.mp4](https://people.csail.mit.edu/mrub/evm/video/face.mp4)，不是经过颜色放大后的结果视频。
- 下载前HEAD检查：Content-Length=1,639,646，实际文件大小一致。
- 时间元数据：results/mit_face_ffprobe.json；实际PTS在每次推理结果中保存。
- 许可依据：作者公开提供source视频，页面要求使用代码或视频时引用论文；只做本地非商业研究演示并保留署名。
- 页面单独的软件发布协议适用于代码/可执行程序，本项目没有下载它们、点击同意或代签协议。
- 没有同步真值，不能评价准确性。下载与裁剪均为本地处理，没有向外部服务上传视频。

## 同步真值候选调查

| 来源 | 信号/访问状态 | 本阶段处理 |
|---|---|---|
| [COHFACE官方记录](https://zenodo.org/records/4081054) | 视频+BVP+呼吸；文件restricted，机构常任人员签署EULA | 未注册、未申请、未下载；完整大小未公开，不能编造 |
| [LGI-PPGI作者仓库](https://github.com/partofthestars/LGI-PPGI-DB) | 视频+PPG/HR，CC BY 4.0；作者说下载不可用；旧单包4.21–7.57GB | 没有呼吸真值，未下载大包 |
| [Idiap COHFACE读取接口](https://github.com/bioidiap/bob.db.cohface) | README明确不包含原始数据，只有读取与协议代码 | 元数据调查，不把软件许可证当作数据授权 |

COHFACE适合下一阶段双任务评价，但必须由用户自行获得合法授权。
有授权后仅选一个60秒视频及对应BVP、呼吸记录进行流程验证，再扩大固定测试集。
作者称MTTS-CAN权重训练于AFRL；该说明不包含逐受试者清单，因此不作绝对零重叠保证。

## 不可作出的推论

视频中出现面部、模型能输出数字、谱中出现峰值，都不能证明该数字是准确的生理测量。
本样本压缩和短时长可能影响rPPG与呼吸估计；没有真值不能区分生理变化和模型/压缩/运动伪影。


## 后续找到的真实PPG公开样本

MPU-rPPG作者Figshare样本已下载一段128MB视频与0.7MB接触PPG文件，完成逐帧计数/时间核查、
两模型推理与描述性评价。存在参考质量疑点，详见[GT补充报告](gt_followup.md)。
UBFC subject1/3的GT可下载，视频触发Google配额；subject3随后由用户上传，已完成实测，见[UBFC报告](ubfc_report.md)。没有呼吸GT。
