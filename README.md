[English report (PDF)](outputs/extension/CAR-bench_Corrected_First3_Report_EN.pdf) | [English report (HTML)](outputs/extension/comparison-report-en.html) | [Latest slides: safety insight and links](outputs/CAR_bench_presentation_safety_insight.pptx)

# CAR-bench：GPT-6 Luna 三类任务复现（前三轮算法修正版）

2026-10-19 离线重算。主结果与历史 GPT-5 均取 trial ID 0、1、2。Pass@1 仅看 trial 0，Pass@3 看前三轮任意成功，Pass^3 看前三轮全部成功。直接用作者 analyze_results.py 和 analyze_results_v2.py 中的函数交叉核验。此前多轮平均与组合结果仅保留为补充分析。

## 三类任务扩展实验

新增 Base 与 Hallucination，仍使用原模型与固定数据版本，累计预算包含前次 Disambiguation。先每题三次，再均衡增加重复。用户在第七轮要求停止 Base/Hallucination，随后要求将 Disambiguation 补至六轮，仍受总预算保护。用户后续追加 Gemini NZ$10；程序保守增加 US$5 额度，累计本地停止线调整为 US$9.50，完成补跑即停止，不继续耗尽充值。预算中断不作为模型失败。

| 类别 | 完成三轮/总题数 | 全部有效试验 | Pass@1 | Pass@3 | Pass^3 |
|---|---:|---:|---:|---:|---:|
| base | 50/50 | 341 | 76.0% | 84.0% | 58.0% |
| hallucination | 50/50 | 343 | 66.0% | 78.0% | 50.0% |
| disambiguation | 25/25 | 150 | 68.0% | 80.0% | 40.0% |

表中主指标仅使用前三次；额外重复在补充结果中单独报告。累计估算费用：OpenAI $0.930797，Gemini $4.989678。其中 3 次服务异常或进程中断未返回用量，保留 $0.078386 最坏情况费用预留，未将其视为免费。

六轮对齐补充结果（k=3 的组合估计）：

| 类别 | 完整轮次 | 平均单次成功率 | 组合 Pass@3 | 组合 Pass^3 |
|---|---:|---:|---:|---:|
| base | 6 | 75.3% | 87.1% | 61.5% |
| hallucination | 6 | 66.0% | 77.3% | 53.3% |
| disambiguation | 6 | 56.7% | 75.8% | 37.8% |

[PDF 报告](outputs/extension/CAR-bench_前三轮算法修正版报告.pdf) · [完整对比报告](outputs/extension/comparison-report.html) · [详细汇总与区间](outputs/extension/summary.json) · [逐题结果](outputs/extension/per-task-results.csv) · [题目定义审计](outputs/extension/task-definition-audit.json) · [停止事件](outputs/extension/events.jsonl)

![历史同题对比](outputs/extension/matched-comparison.png)

![一致性分布](outputs/extension/consistency-distribution.png)

其他图表（PNG/SVG）位于 `outputs/extension/`。论文表格概览与同题历史对照分开展示；历史代码/模拟用户/评分器未完全控制，不能把差异完全归因于模型升级。Hallucination 任务失败率不等同于直接观测到的编造率。

无需密钥的重新分析：`python work/analyze_extension.py`，然后 `python work/plot_extension.py`。付费扩展入口是 `python work/extend_experiment.py`，使用已有凭据，继承之前费用账本；请先阅读源代码中的停止条件。它不会自动设置平台预算，且不得与其他实验进程同时运行。

`outputs/usage-ledger.json` 是前次消歧实验账本；`outputs/extension/usage-ledger.json` 包含其完整前缀及新增调用，累计费用以扩展账本为准，不要把两个账本相加。首批消歧子报告也已修正。完整结果以扩展报告为准。

[修正版 slides](outputs/CAR_bench_presentation_corrected_first3.pptx) · [作者算法核验](outputs/extension/first-three-verification.json)

本次新增 API 调用和费用均为零。所有原始轨迹与费用账本哈希保持不变。执行 `python work/verify_first_three.py` 可离线检查。
