import base64,html,json,shutil,zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs'
s=json.loads((OUT/'summary.json').read_text())
m=json.loads((OUT/'manifest.json').read_text())
assert s['unfinished_api_calls']==0,'Run still in progress'
assert s['n_tasks']==25,'Expected all 25 test tasks'
pct=lambda x:f'{100*x:.1f}%'
interval=lambda a:f'{pct(a[0])}–{pct(a[1])}'
labels={'pass1':'Pass@1：第一轮成功率','pass_at3':'Pass@3：三次至少成功一次','pass_all3':'Pass^3：三次全部成功','gap':'一致性差距：Pass@3 − Pass^3'}
score_rows=''.join(f'<tr><td>{v}</td><td>{pct(s["scores"][k])}</td><td>{interval(s["wilson_95ci"].get(k,s["task_bootstrap_95ci"][k]))}</td></tr>' for k,v in labels.items())
subgroup_rows=''.join(f'<tr><td>{label}</td><td>{s["subgroups"][key]["n_tasks"]}</td><td>{pct(s["subgroups"][key]["pass_at3"])}</td><td>{pct(s["subgroups"][key]["pass_all3"])}</td></tr>' for key,label in [('internal','查询环境/偏好自行消歧'),('user','向用户询问消歧')])
c=s['cost_usd'];matched=s.get('historical_matched_tasks',{})
comparison=''
component_names={'r_actions_final':'最终状态不符','r_actions_intermediate':'中间操作不符','r_tool_subset':'缺少必要工具查询/动作','r_policy':'规则违反','r_tool_execution':'工具调用错误','r_user_end_conversation':'模拟用户判定消歧/对话失败'}
component_rows=''.join(f'<tr><td>{label}</td><td>{s["failed_components"].get(k,0)}</td></tr>' for k,label in component_names.items())
case_section=f'''<h2>失败类型与原始案例</h2><p>下表按单次试验统计；一次失败可能涉及多个分项，不能相加当作总失败数。</p><table><tr><th>评分分项</th><th>失败次数</th></tr>{component_rows}</table>
<ul><li><b>disambiguation_9，trial 1：</b>用户说“Can you turn on the beams?”，agent 直接问“Do you mean the low beams or the high beams?”，没有先查询环境。原题要求优先内部消歧，该轮被判 DISAMBIGUATION_ERROR；另外两轮成功。</li>
<li><b>disambiguation_29，trial 0：</b>在用户选择路线前已经修改导航并选取最快路线，随后才列出其他路线；同时没有按规则给出备选数量，出现动作和规则评分失败。</li>
<li><b>disambiguation_31，trial 0：</b>最终动作正确，但没有完整介绍备选路线，规则评分失败。完成主要任务与满足全部约束仍有区别。</li></ul>
<p class="note">这些案例是轨迹抽查，不是全量人工重标注。模拟用户本身也可能偏离脚本：例如 disambiguation_29 的脚本要求 agent 主动选路时结束对话，但该轮用户继续询问路线。保留官方评分，不人为修正分数；这也是解释结果时的限制。</p>'''
if matched:
    comp_rows=''.join(f'<tr><td>{labels[k]}</td><td>{pct(matched["luna"][k])}</td><td>{pct(matched["gpt5"][k])}</td><td>{100*matched["difference"][k]:+.1f} 个百分点</td></tr>' for k in ['pass1','pass_at3','pass_all3'])
    comparison=f'<h2>历史同题参考：{matched["n"]} 题</h2><p>仅保留任务定义完全一致且历史记录无运行错误的题目。双方均仅使用 trial ID 0、1、2；Pass@1 只看 trial 0，Pass@3 看前三轮是否至少成功一次，Pass^3 看是否全部成功。</p><table><tr><th>指标</th><th>Luna 本次</th><th>GPT-5 历史</th><th>差值</th></tr>{comp_rows}</table><p>这是历史参考，不是控制实验：代码、评分器版本、服务端模型及运行时间不同。即使任务定义一致，也不能把差值完全归因于 agent 模型升级。</p>'
    lo,hi=matched['difference_bootstrap_95ci']['pass_all3']
    comparison+=f'<p>三次全成功率差值的配对题目 bootstrap 95% 区间：{100*lo:+.1f} 至 {100*hi:+.1f} 个百分点。'+('区间包含零，当前样本不足以支持稳定提升的结论。' if lo<=0<=hi else '该区间仅描述当前样本的不确定性，不能消除历史比较的混杂因素。')+'</p>'
dist=s['success_distribution']
fig,ax=plt.subplots(figsize=(7.5,3.6),layout='constrained')
vals=[dist.get(str(i),0) for i in range(4)]
ax.bar(range(4),vals,color=['#a94b4b','#d6914f','#d9bb57','#237c67'])
ax.set(xticks=range(4),xlabel='Successful trials out of 3',ylabel='Number of tasks',title='GPT-6 Luna · Disambiguation test set')
ax.set_ylim(0,max(vals)+3)
for i,n in enumerate(vals):ax.text(i,n+.2,str(n),ha='center')
fig.savefig(OUT/'consistency.png',dpi=170)
plt.close(fig)
img=base64.b64encode((OUT/'consistency.png').read_bytes()).decode()
failed=sum(int(v) for k,v in dist.items() if int(k)<3)
mixed=sum(int(v) for k,v in dist.items() if int(k) in [1,2])
conclusion=f'本次 {s["n_tasks"]} 题、{s["n_trials"]} 次试验中，{dist.get("3",0)} 题三次全成功，{mixed} 题出现时成时败，{dist.get("0",0)} 题三次全失败。'
claims=[f'一致性：本次差距为 {100*s["scores"]["gap"]:.1f} 个百分点。差距必须与成功率一起解读，稳定失败不等于可靠。',
        f'消歧可靠性：本次 Pass^3 为 {pct(s["scores"]["pass_all3"])}，95% Wilson 区间为 {interval(s["wilson_95ci"]["pass_all3"])}。论文 GPT-5 的 36% / 68%（Pass^3 / Pass@3）来自不同的原始评测范围，不能直接作为同样本显著性检验。',
        '推理的因果效果：未设置 Luna reasoning=none 对照，不能据此判断开启推理带来多少提升。',
        '此页仅为首批消歧子报告；Base 和 Hallucination 的结果已纳入完整三类任务报告。']
text=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>CAR-bench 一致性复现实验</title>
<style>body{{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;color:#22313a;max-width:1000px;margin:40px auto;padding:0 24px}}h1{{font-size:28px}}h2{{font-size:21px;margin-top:32px}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:10px;border-bottom:1px solid #dce3e6;text-align:left}}th{{background:#edf3f2}}.lead{{padding:18px;background:#eaf4f0;border-left:4px solid #237c67}}.note{{color:#58666d}}img{{width:100%;max-width:760px}}code{{overflow-wrap:anywhere}}</style>
<h1>CAR-bench：GPT-6 Luna 消歧一致性实验</h1><p class="note">2026-10-19 · 原题 / 原工具环境 / 原评分逻辑 · 当前官方 test split</p>
<p class="lead">{conclusion}</p><p>本页已按作者前三轮算法修正。完整三类任务结果及六轮补充分析见 <a href="extension/comparison-report.html">完整报告</a>。下方费用仅为首批消歧实验费用，累计费用请看完整报告。</p>
<p class="note">运行审计：有 {s['infrastructure_retries']} 轮因本地费用账本文件锁中断，仅补跑该轮，未修改模型、题目或提示词。原始错误与替代轨迹保留在 infrastructure-errors；费用包含中断前已发生的调用。</p>
<h2>主要结果</h2><table><tr><th>指标</th><th>结果</th><th>95% 区间</th></tr>{score_rows}</table>
<p class="note">Pass@3 与 Pass^3 的区间采用题目层面的 Wilson 区间；其他区间采用题目重采样 10,000 次。区间不涵盖模拟用户和评分器系统误差，也不代表整个真实世界任务分布。</p>
<img src="data:image/png;base64,{img}" alt="各题三次试验成功次数分布">
<h2>两类消歧</h2><table><tr><th>作者题目标注</th><th>题数</th><th>Pass@3</th><th>Pass^3</th></tr>{subgroup_rows}</table><p class="note">子组很小，属于描述性分析，不用于断言某类任务普遍更难。</p>
<h2>论文结论在这里是否成立</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in claims)}</ul>
{comparison}
{case_section}
<h2>成本和控制</h2><table><tr><th>供应商</th><th>Token 用量估算费用</th><th>控制</th></tr><tr><td>OpenAI</td><td>${c['openai']:.6f}</td><td>CAR-bench 独立项目月度硬上限 $10；本地 $9.50 提前停机</td></tr><tr><td>Gemini</td><td>${c['gemini']:.6f}</td><td>本次程序本地 $4.50 提前停机，保留至 $5 的余量；不是 Google 账户级硬上限</td></tr></table><p>合计约 <b>${sum(c.values()):.4f}</b>，包括连通性测试。按返回 token 与已核对单价估算，最终以平台账单为准。运行完成时没有未结算请求。</p>
<h2>实验配置与限制</h2><ul><li>Agent：gpt-6-luna，reasoning=medium，Responses API；不额外修改提示词，不添加搜索或其他外部工具。</li><li>模拟用户：gemini-2.5-flash，thinking=low（作者代码配置）；评分：gemini-2.5-flash，作者原始评分提示及逻辑。</li><li>每题独立启动 3 次，固定任务选择顺序 seed=769；未固定云端采样随机数。最多同时运行 3 道题。</li><li>每次调用输出上限 8,192 token，截断或基础设施错误触发停止，不当作模型答错。当前结果全部为正常完成的试验。</li><li>代码版本 <code>{m['code_commit']}</code>；Hugging Face 数据版本 <code>{m['data_revision']}</code>。</li><li>采用当前官方代码，不是论文发布时的历史代码快照。任务定义审计发现 6 道 test 题相对历史记录发生变化。</li><li>仅三个重复，模拟用户和评分器也是随机模型；模型别名可能随服务更新变化。无独立人工标注全量复核。</li></ul>
<h2>检查原始证据</h2><p><a href="per-task-results.csv">逐题结果 CSV</a> · <a href="summary.json">指标与区间 JSON</a> · <a href="usage-ledger.json">逐请求费用</a> · <a href="failures.json">失败项</a> · <a href="baseline-task-audit.json">历史题目差异</a> · <a href="https://github.com/CAR-bench/car-bench">作者仓库</a></p></html>'''
(OUT/'report.html').write_text(text,encoding='utf-8')
readme='''CAR-bench Disambiguation consistency replication
Experiment date: 2026-10-19 Pacific/Auckland
Start with report.html. Raw trajectories and task snapshot are in outputs/.
The original benchmark repository is required at work/car-bench, commit ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b.
Install its dependencies plus the recorded dependency versions into an isolated Python environment.
The runner reads the already configured local .env.local for OPENAI_API_KEY and GEMINI_API_KEY.
No credentials or private encryption keys are included in this bundle.
Run: python work/experiment.py --tasks 25 --jobs 3
Completed task files are skipped. Do not run a second process simultaneously: the cost guard is thread-safe, not multi-process.
Analysis: python work/analyze_experiment.py, then python work/build_report.py
Costs include the connectivity probes. OpenAI project hard limit is $10/month; local experimental guards are $9.50 OpenAI and $4.50 Gemini.
The local Gemini guard controls only calls made through this runner, not unrelated Google account usage.
This is a current-code replication with a Responses API adapter, not an exact historical code reproduction.
'''
(OUT/'README.txt').write_text(readme,encoding='utf-8')
print('Corrected initial disambiguation subreport generated.')
