"""Scientific comparison figures and a self-contained Chinese report."""
import base64,html,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/extension'
METRICS=['pass1','pass_at3','pass_all3']
LABELS=['Pass@1','Pass@3','Pass^3']
KINDS=['base','hallucination','disambiguation']
NAMES={'base':'Base','hallucination':'Hallucination','disambiguation':'Disambiguation'}
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})

def save(fig,name):
    for ext in ['png','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)

def main():
    s=json.loads((OUT/'summary.json').read_text());cats=s['categories']
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for ax,k in zip(axes,KINDS):
        d=cats[k];x=np.arange(3);a=[d['scores'][m]*100 for m in METRICS];b=[d['paper_gpt5'][m]*100 for m in METRICS]
        ax.bar(x-.18,a,.36,label='GPT-6 Luna (current test)',color='#287f77')
        ax.bar(x+.18,b,.36,label='GPT-5 (paper Table 4)',color='#9a839d')
        for xx,ys in [(x-.18,a),(x+.18,b)]:
            for px,y in zip(xx,ys):ax.text(px,y+1,f'{y:.1f}',ha='center',fontsize=9)
        ax.set(xticks=x,xticklabels=LABELS,ylim=(0,105),title=f'{NAMES[k]} (Luna n={d["primary_complete_tasks"]})',ylabel='Success (%)')
    axes[0].legend(fontsize=9,loc='upper left')
    fig.suptitle('Historical overview - different evaluation sets; not a controlled comparison',fontsize=13)
    save(fig,'paper-overview')
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for ax,k in zip(axes,KINDS):
        d=cats[k];x=np.arange(3)
        if not d['matched_n']:ax.text(.5,.5,'No identical tasks',ha='center');continue
        for delta,label,color in [(-.18,'luna','#287f77'),(.18,'gpt5','#9a839d')]:
            ys=[100*d['matched'][label][m] for m in METRICS]
            ax.bar(x+delta,ys,.36,label='GPT-6 Luna' if label=='luna' else 'Historical GPT-5',color=color)
            for px,y in zip(x+delta,ys):ax.text(px,y+1,f'{y:.1f}',ha='center',fontsize=9)
        ax.set(xticks=x,xticklabels=LABELS,ylim=(0,105),title=f'{NAMES[k]} (matched n={d["matched_n"]})',ylabel='Success (%)')
    axes[0].legend(fontsize=9,loc='upper left')
    fig.suptitle('Both models: first 3 trials - identical tasks, historical confounds remain',fontsize=13)
    save(fig,'matched-comparison')
    fig,axes=plt.subplots(1,3,figsize=(13,4.1),layout='constrained')
    for ax,k in zip(axes,KINDS):
        d=cats[k];v=[d['success_distribution'].get(str(i),0) for i in range(4)]
        ax.bar(range(4),v,color=['#b75d63','#d99e55','#c6bc68','#287f77'])
        for i,n in enumerate(v):ax.text(i,n+.25,str(n),ha='center')
        ax.set(xticks=range(4),ylim=(0,max(v)+4),title=NAMES[k],xlabel='Successes in first 3 trials',ylabel='Tasks')
    fig.suptitle('Observed repeatability: first 3 repetitions, all model failures retained')
    save(fig,'consistency-distribution')
    fig,ax=plt.subplots(figsize=(8.5,4.1),layout='constrained')
    ys=np.arange(3)
    for i,k in enumerate(KINDS):
        if not cats[k]['matched_n']:continue
        d=cats[k]['matched'];v=d['difference']['pass_all3']*100;lo,hi=[x*100 for x in d['difference_bootstrap_95ci']['pass_all3']]
        ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',capsize=5,color='#287f77')
        ax.text(hi+1,i,f'{v:+.1f} pp',va='center',fontsize=10)
    ax.axvline(0,color='#777777',ls='--',lw=1)
    ax.set(yticks=ys,yticklabels=[NAMES[k] for k in KINDS],xlabel='Luna minus historical GPT-5 (percentage points)',title='Matched Pass^3 difference with paired task bootstrap 95% CI')
    ax.margins(x=.3,y=.3);save(fig,'matched-uncertainty')
    failkeys=['r_policy','r_actions_final','r_tool_execution','r_user_end_conversation']
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained');x=np.arange(len(failkeys))
    for i,k in enumerate(KINDS):
        d=cats[k];values=[float('nan') if k=='hallucination' and f in ['r_policy','r_actions_final'] else 100*d['failure_components'].get(f,0)/d['primary_trials'] for f in failkeys]
        ax.bar(x+(i-1)*.24,values,.24,label=NAMES[k])
        if k=='hallucination':
            for j in [0,1]:ax.text(x[j],.5,'N/A',ha='center',fontsize=9,color='#777777')
    ax.set(xticks=x,xticklabels=['Policy','Final state','Tool execution','User termination'],ylabel='Primary trials with failure (%)',title='Failure components overlap; these rates must not be added')
    ax.legend(loc='upper left');save(fig,'failure-components')
    fig,ax=plt.subplots(figsize=(8,4.1),layout='constrained')
    for k in KINDS:
        profile=cats[k].get('repeat_sensitivity',{})
        xs=sorted(map(int,profile));ys=[100*profile[str(n)]['pass_all3'] for n in xs]
        ax.plot(xs,ys,marker='o',label=NAMES[k])
    ax.set(xlabel='Repetitions per task used for estimation',ylabel='Estimated Pass^3 (%)',title='Supplementary repeatability estimate (k stays fixed at 3)',ylim=(0,100))
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True));ax.legend();save(fig,'repeat-sensitivity')
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for ax,k in zip(axes,KINDS):
        d=cats[k];m=d.get('balanced_matched');x=np.arange(3)
        if not m:continue
        for delta,label,color in [(-.18,'luna','#287f77'),(.18,'gpt5','#9a839d')]:
            ys=[100*m[label][metric] for metric in METRICS]
            ax.bar(x+delta,ys,.36,label=f'Luna ({d["balanced_repeats"]} repeats)' if label=='luna' else 'Historical GPT-5 (5)',color=color)
            for px,y in zip(x+delta,ys):ax.text(px,y+1,f'{y:.1f}',ha='center',fontsize=9)
        ax.set(xticks=x,xticklabels=['Mean success','Pass@3','Pass^3'],ylim=(0,110),title=f'{NAMES[k]} (matched n={d["matched_n"]})',ylabel='Success (%)')
        ax.legend(fontsize=8,loc='upper left')
    fig.suptitle('All balanced repetitions; k=3 combinatorial estimates, historical confounds remain',fontsize=12)
    save(fig,'balanced-matched-comparison')
    imgs=lambda name:f'<img src="data:image/png;base64,{base64.b64encode((OUT/(name+".png")).read_bytes()).decode()}" alt="{name}">'
    fmt=lambda v:f'{v*100:.1f}%'
    rows=''.join(f'<tr><td>{NAMES[k]}</td><td>{cats[k]["primary_complete_tasks"]}/{cats[k]["available_tasks"]}</td><td>{cats[k]["valid_trials_all"]}</td>'+''.join(f'<td>{fmt(cats[k]["scores"][m])}</td>' for m in METRICS)+f'<td>{100*cats[k]["scores"]["gap"]:.1f} pp</td></tr>' for k in KINDS)
    matchrows=''
    for k in KINDS:
        d=cats[k]
        if d['matched_n']:
            m=d['matched'];lo,hi=m['difference_bootstrap_95ci']['pass_all3']
            matchrows+=f'<tr><td>{NAMES[k]}</td><td>{d["matched_n"]}</td><td>{fmt(m["luna"]["pass_all3"])}</td><td>{fmt(m["gpt5"]["pass_all3"])}</td><td>{100*m["difference"]["pass_all3"]:+.1f} pp</td><td>{100*lo:+.1f} 至 {100*hi:+.1f} pp</td></tr>'
    extras=''.join(f'<li>{NAMES[k]}：所有题共同完成 {cats[k]["balanced_repeats"]} 次重复。'+('利用这些重复估计三次全成功率为 '+fmt(cats[k]['balanced_scores']['pass_all3'])+'。' if cats[k]['balanced_scores'] else '未形成覆盖全题的同次数额外重复。')+'</li>' for k in KINDS)
    extra_match=''
    for k in KINDS:
        d=cats[k];m=d.get('balanced_matched')
        if m:
            lo,hi=m['difference_bootstrap_95ci']['pass_all3']
            extra_match+=f'<li>{NAMES[k]} 的 {d["matched_n"]} 道历史同题：使用前 {d["balanced_repeats"]} 次重复估计的 Pass^3 为 {fmt(m["luna"]["pass_all3"])}，历史 GPT-5 为 {fmt(m["gpt5"]["pass_all3"])}，差值 {100*m["difference"]["pass_all3"]:+.1f} pp，配对 95% 区间 {100*lo:+.1f} 至 {100*hi:+.1f} pp。此项为补充分析，历史混杂限制同样适用。</li>'
    exactrows=''.join(f'<tr><td>{NAMES[k]}</td><td>{cats[k]["balanced_repeats"]}</td><td>{fmt(cats[k].get("balanced_all_n_success",0))}</td></tr>' for k in KINDS)
    c=s['total_cost_including_prior'];stoptext='Base 与 Hallucination 保留六轮及部分第七轮，按用户要求停止追加。Disambiguation 在追加充值授权后补至六轮并停止。运行期间的预算保护、服务错误、受控重启及费用预留详见 events.jsonl 和 usage-ledger.json。' if cats['disambiguation']['balanced_repeats']==6 else 'Disambiguation 补跑进行中；运行事件详见 events.jsonl。'
    interpretations=[]
    for k in KINDS:
        d=cats[k];sentence=f'{NAMES[k]}：前三轮的一致性差距为 {100*d["scores"]["gap"]:.1f} 个百分点。'
        if d['matched_n']:
            m=d['matched'];lo,hi=m['difference_bootstrap_95ci']['pass_all3']
            sentence+=('同题历史比较中三次全成功率更高，配对区间不跨零；仍不能完全归因于模型变化。' if lo>0 else '同题历史比较中三次全成功率更低，配对区间不跨零；仍不能完全归因于模型变化。' if hi<0 else '同题历史比较的差值区间跨零，当前样本未支持明确改善或下降。')
        interpretations.append('<li>'+sentence+'</li>')
    body=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>CAR-bench 三类任务对比</title><style>body{{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;max-width:1100px;margin:32px auto;padding:0 24px;color:#22313a}}h1{{font-size:28px}}h2{{font-size:21px;margin-top:32px}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:9px;border-bottom:1px solid #dde5e5;text-align:left}}th{{background:#edf4f1}}img{{width:100%;height:auto}}.note{{color:#58666d;font-size:14px}}.lead{{padding:16px;background:#eaf4f0}}</style>
<h1>CAR-bench：三类任务的成功率与一致性</h1><p class="note">2026-10-19 · GPT-6 Luna medium · Gemini 2.5 Flash 模拟用户与评分 · 固定官方代码和数据版本</p>
<p class="lead">新增 Base 与 Hallucination 各 50 道 test 题；Disambiguation 沿用已完成的 25 题。主结果统一使用 Luna 与历史 GPT-5 的第 1、2、3 轮（trial ID 0、1、2），不按成功与否挑选。额外试验仅列入补充分析。预算中断不计为模型失败。</p>
<h2>本次结果</h2><p>算法修正：此前 Pass@1 使用多轮平均，历史 GPT-5 对照使用五轮组合。现在主结果全部采用作者的前三轮算法。六轮组合估计独立保留；本次只读取已保存轨迹，没有新增 API 请求或费用。作者源码固定于 ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b。</p><table><tr><th>类别</th><th>完成三轮/全题数</th><th>全部有效试验</th><th>Pass@1</th><th>Pass@3</th><th>Pass^3</th><th>一致性差距</th></tr>{rows}</table>
<p>Pass@1 是第一轮的成功题目比例；Pass@3 是三次至少成功一次；Pass^3 是三次全部成功。差距为 Pass@3 − Pass^3；稳定失败也会使差距变小，所以必须同时看成功率。</p>
{imgs('consistency-distribution')}
<h2>与论文原表比较：描述性概览</h2><p>紫色为论文 Table 4 的 GPT-5 thinking 数值，绿色为本次当前 test split。评测题目范围不同，此图不能作为模型提升的因果证据。</p>{imgs('paper-overview')}
<h2>只比较题目定义相同的历史记录</h2><p>逐题检查用户脚本、persona、环境配置、预期动作、缺失项和任务标注。仅保留所有历史重复定义均与当前一致、且没有运行错误的题。双方均只取 trial ID 0、1、2，采用作者 analyze_results_v2.py（以及旧版 analyze_results.py）的首次/前三次算法。保留原来的同题筛选集合，避免改变样本造成额外差异。</p>{imgs('matched-comparison')}
<table><tr><th>类别</th><th>同题数</th><th>Luna Pass^3</th><th>GPT-5 Pass^3</th><th>差值</th><th>配对95%区间</th></tr>{matchrows}</table>{imgs('matched-uncertainty')}
<p class="note">置信区间来自按题目配对重采样 10,000 次，不能消除历史代码、模型服务和评分器差异。区间跨零时，不支持方向明确的改善或退步结论。</p>
<h2>这些结果支持什么结论</h2><ul>{''.join(interpretations)}</ul>
<h2>失败原因分布</h2>{imgs('failure-components')}<p>图中各分项可在同一次试验重叠，不能相加当作总失败率。官方代码跳过 Hallucination 的规则与状态目标评分，这两项标为 N/A，不表示零错误。模拟用户终止标记（例如 HALLUCINATION_ERROR、OUT_OF_SCOPE）单独保存在 summary.json 的 end_keywords 字段；它们属于模型评判结果，不是独立人工标注。</p>
<h2>补充分析：六轮组合估计</h2><p>这里 Luna 使用六轮的全部 20 种三次组合；历史 GPT-5 使用五轮的全部 10 种三次组合。图中的 Mean success 是全部轮次平均单次成功率，与正文只看第一轮的 Pass@1 不同。这些补充估计不作为与论文主结果的直接对照。</p><ul>{extras}</ul>{imgs('balanced-matched-comparison')}{imgs('repeat-sensitivity')}<ul>{extra_match}</ul><table><tr><th>类别</th><th>共同完整轮次 n</th><th>n 次全部成功（不可直接与历史五轮比较）</th></tr>{exactrows}</table><p>额外试验按固定顺序均衡推进，未根据是否成功选择重跑。Base 和 Hallucination 在用户要求下停止第七轮，保留部分第七轮数据；Disambiguation 随后仅补至第六轮，或在预算保护触发时停止。不同题额外完成次数可能因此不一致；主结果始终保留前三次，补充结果只使用所有题共同完成的前 n 次，按组合公式估计 k=3 指标：对 n 次中成功 c 次的题，Pass^3 = C(c,3)/C(n,3)，Pass@3 = 1 − C(n−c,3)/C(n,3)，再对题目等权平均。</p>
<h2>费用及停止原因</h2><p>含前次消歧实验的累计估算：OpenAI ${c['openai']:.6f}，Gemini ${c['gemini']:.6f}，合计 ${sum(c.values()):.6f}。仍在进行的请求预留数：{s['reserved_calls']}；有 {s['uncertain_calls']} 次服务异常或进程中断没有返回用量，已按 ${s['uncertain_cost_reserved']:.6f} 保守预留计入上述费用。本地提前停机线为 OpenAI $9.50、Gemini 充值授权后 $9.50（此前 $4.50；补跑开始时 $4.98），OpenAI 仍受 $10 总预算约束；Gemini 原预算 $5，用户随后追加 NZ$10，本地仅增加按 US$5 计算的额度并保留余量。</p><p>{html.escape(stoptext)}</p>
<h2>解释范围</h2><ul><li>运行中出现 Gemini 503 服务错误。保留已完成结果，恢复被中断的试验；随后将 Gemini 同时请求限制为 2，并对临时服务错误最多尝试 3 次、间隔 20/40 秒。每个失败请求仍保留最大费用预留。另外曾出现 Gemini 输出截断，之后仅对截断的 Gemini 请求允许 16,384 token 上限重试，正常请求仍为 8,192；Luna 上限保持 8,192。每次尝试单独计费并保留记录，模型、任务和评分提示未改变。</li><li>本次使用当前官方任务、工具与评分代码，并使用 Luna agent 和 Gemini 模拟用户/评分器；这不是对论文历史环境的逐字重建。</li><li>Hallucination 任务考察能否识别并说明缺失工具或信息，评分也受无效工具调用和偏离任务影响，失败率不等同于直接观察到的编造率；需结合轨迹和失败分项解释。</li><li>三类题目的难度和构成不同，类别分数差异不能单独证明某种能力的因果影响。</li><li>未增加 reasoning=none 对照，不能归因于推理开关。服务端随机性与模拟用户/评分器误差仍存在。</li></ul>
<h2>证据与下载</h2><p><a href="per-task-results.csv">逐题结果</a> · <a href="summary.json">完整指标</a> · <a href="task-definition-audit.json">题目差异审计</a> · <a href="usage-ledger.json">累计费用</a> · <a href="https://github.com/CAR-bench/car-bench">作者仓库</a></p><p class="note">价格来源：<a href="https://developers.openai.com/api/docs/models/gpt-6-luna">OpenAI</a> / <a href="https://ai.google.dev/gemini-api/docs/pricing">Google</a>。费用由返回 token 估算，最终以供应商账单为准。PNG 与 SVG 图表和原始试验文件随复现资料保存。</p></html>'''
    (OUT/'comparison-report.html').write_text(body,encoding='utf-8')
    print('Created seven comparison charts (PNG + SVG) and comparison-report.html')

if __name__=='__main__':main()
