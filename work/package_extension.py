"""Prepare the private repository update and a reproducibility download."""
import hashlib,json,shutil,zipfile,re
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parent.parent
REPO=ROOT/'work/github-repo';EXT=ROOT/'outputs/extension'
s=json.loads((EXT/'summary.json').read_text())
assert s['reserved_calls']==0,'Unresolved API charges require review'
assert any(e['state'] in ['budget_stop','user_stop'] for e in s['stops']),'Expected budget-limited completion'
shutil.copytree(EXT,REPO/'outputs/extension',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.zip'))
for name in ['extend_experiment.py','supplement_disambiguation.py','analyze_extension.py','plot_extension.py','package_extension.py','pdf_extension.py','verify_extension.py','test_extension_transport.py']:
    shutil.copy2(ROOT/'work'/name,REPO/'work'/name)
for kind in ['base','hallucination']:
    # Runner consumes this frozen snapshot before writing the output snapshot.
    shutil.copy2(ROOT/'work'/f'{kind}-tasks.json',REPO/'work'/f'{kind}-tasks.json')
    p=next(p for p in (ROOT/'work/car-bench/results'/kind).rglob('*.json') if 'gpt-5-thinking' in str(p))
    dest=REPO/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
provenance_path=REPO/'evidence/provenance.json'
provenance=json.loads(provenance_path.read_text())
provenance['vendored_tracked_paths']=sorted(set(provenance['vendored_tracked_paths']) | {str(p.relative_to(REPO/'work/car-bench')).replace('\\','/') for p in (REPO/'work/car-bench/results').rglob('*.json')})
provenance['omitted']='Other historical model result files and Git history. Included GPT-5 Base, Hallucination and Disambiguation historical results used in comparisons.'
provenance_path.write_text(json.dumps(provenance,indent=2),encoding='utf-8')
shutil.copy2(ROOT/'work/extension-run.log',REPO/'evidence/extension-run.log')
for p in (ROOT/'work').glob('disambiguation-supplement*.log'):shutil.copy2(p,REPO/'evidence'/p.name)
for p in (ROOT/'work').glob('final-*-tests.log'):shutil.copy2(p,REPO/'evidence'/p.name)
pdf=ROOT/'outputs/CAR-bench_GPT6-Luna_完整实验报告.pdf'
if pdf.exists():shutil.copy2(pdf,REPO/'outputs'/pdf.name)
readme=(REPO/'README.md').read_text(encoding='utf-8').split('\n## 三类任务扩展实验')[0]
readme=readme.replace('# CAR-bench：GPT-6 Luna 消歧一致性复现','# CAR-bench：GPT-6 Luna 三类任务复现')
if '## 首批：Disambiguation' not in readme:
    readme=readme.replace('2026-10-19 完成。','> 最新扩展：[三类任务对比报告](outputs/extension/comparison-report.html) · [扩展实验数据与图表](outputs/extension/)\n\n## 首批：Disambiguation\n\n2026-10-19 完成。',1)
rows='\n'.join(f'| {k} | {v["primary_complete_tasks"]}/{v["available_tasks"]} | {v["valid_trials_all"]} | {100*v["scores"]["pass1"]:.1f}% | {100*v["scores"]["pass_at3"]:.1f}% | {100*v["scores"]["pass_all3"]:.1f}% |' for k,v in s['categories'].items())
c=s['total_cost_including_prior']
balanced_rows='\n'.join(f'| {k} | {v["balanced_repeats"]} | {100*v["balanced_scores"]["pass1"]:.1f}% | {100*v["balanced_scores"]["pass_at3"]:.1f}% | {100*v["balanced_scores"]["pass_all3"]:.1f}% |' for k,v in s['categories'].items())
readme+=f'''
## 三类任务扩展实验

新增 Base 与 Hallucination，仍使用原模型与固定数据版本，累计预算包含前次 Disambiguation。先每题三次，再均衡增加重复。用户在第七轮要求停止 Base/Hallucination，随后要求将 Disambiguation 补至六轮，仍受总预算保护。用户后续追加 Gemini NZ$10；程序保守增加 US$5 额度，累计本地停止线调整为 US$9.50，完成补跑即停止，不继续耗尽充值。预算中断不作为模型失败。

| 类别 | 完成三轮/总题数 | 全部有效试验 | Pass@1 | Pass@3 | Pass^3 |
|---|---:|---:|---:|---:|---:|
{rows}

表中主指标仅使用前三次；额外重复在补充结果中单独报告。累计估算费用：OpenAI ${c['openai']:.6f}，Gemini ${c['gemini']:.6f}。其中 {s['uncertain_calls']} 次服务异常或进程中断未返回用量，保留 ${s['uncertain_cost_reserved']:.6f} 最坏情况费用预留，未将其视为免费。

六轮对齐补充结果（k=3 的组合估计）：

| 类别 | 完整轮次 | Pass@1 | Pass@3 | Pass^3 |
|---|---:|---:|---:|---:|
{balanced_rows}

[PDF 报告](outputs/extension/CAR-bench_三类任务六轮对比报告.pdf) · [完整对比报告](outputs/extension/comparison-report.html) · [详细汇总与区间](outputs/extension/summary.json) · [逐题结果](outputs/extension/per-task-results.csv) · [题目定义审计](outputs/extension/task-definition-audit.json) · [停止事件](outputs/extension/events.jsonl)

![历史同题对比](outputs/extension/matched-comparison.png)

![一致性分布](outputs/extension/consistency-distribution.png)

其他图表（PNG/SVG）位于 `outputs/extension/`。论文表格概览与同题历史对照分开展示；历史代码/模拟用户/评分器未完全控制，不能把差异完全归因于模型升级。Hallucination 任务失败率不等同于直接观测到的编造率。

无需密钥的重新分析：`python work/analyze_extension.py`，然后 `python work/plot_extension.py`。付费扩展入口是 `python work/extend_experiment.py`，使用已有凭据，继承之前费用账本；请先阅读源代码中的停止条件。它不会自动设置平台预算，且不得与其他实验进程同时运行。

`outputs/usage-ledger.json` 是前次消歧实验账本；`outputs/extension/usage-ledger.json` 包含其完整前缀及新增调用，累计费用以扩展账本为准，不要把两个账本相加。原始报告保持历史结果，新结论以扩展报告为准。
'''
(REPO/'README.md').write_text(readme,encoding='utf-8')
paths=sorted(p for p in REPO.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.suffix!='.zip' and p.name!='checksums.sha256')
secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env.local').items() if k.endswith('API_KEY') and v]
for p in paths:
    b=p.read_bytes()
    assert not any(v in b for v in secrets),p.relative_to(REPO)
    assert not re.search(rb'(?:sk-proj-[A-Za-z0-9_-]{40,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',b),p.relative_to(REPO)
checksum=REPO/'evidence/checksums.sha256'
checksum.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in paths),encoding='utf-8')
with zipfile.ZipFile(EXT/'CAR-bench_three-task-reproduction.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in paths+[checksum]:z.write(p,p.relative_to(REPO).as_posix())
print('Prepared repository and ZIP; secret scan clean; file count',len(paths)+1)
