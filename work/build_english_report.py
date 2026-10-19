"""Offline English edition of the corrected report. No model/API imports."""
from pathlib import Path
import base64,html,json
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/extension'
S=json.loads((OUT/'summary.json').read_text()); C=S['categories']
KINDS=['base','hallucination','disambiguation']
NAMES=['Base','Hallucination','Disambiguation']
METRICS=['pass1','pass_at3','pass_all3']
pct=lambda x:f'{100*x:.1f}%'
pp=lambda x:f'{100*x:+.1f}'
styles={k:ParagraphStyle(k,fontName='Helvetica-Bold' if k in ['h1','h2'] else 'Helvetica',fontSize=size,leading=lead,spaceAfter=7,keepWithNext=k in ['h1','h2']) for k,size,lead in [('h1',21,26),('h2',14,19),('p',9.5,13.5),('cell',8,10.5)]}
story=[];web=[]
def text(value,tag='p'):
    web.append(f'<{tag}>{html.escape(value)}</{tag}>')
    story.append(Paragraph(html.escape(value),styles[tag]))
def heading(value):text(value,'h2')
def page():story.append(PageBreak());web.append('<hr>')
def table(rows,widths=None):
    web.append('<table>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in r)+'</tr>' for r in rows)+'</table>')
    rows=[[Paragraph(html.escape(str(v)),styles['cell']) for v in r] for r in rows]
    t=Table(rows,colWidths=widths or [487/len(rows[0])]*len(rows[0]),repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf4f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dde5e5')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(KeepTogether([t,Spacer(1,8)]))
def figure(name,width=487):
    p=OUT/(name+'.png');w,h=ImageReader(str(p)).getSize()
    story.extend([Image(str(p),width=width,height=width*h/w),Spacer(1,9)])
    web.append(f'<img alt="{name}" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}">')
def link(label,url):
    web.append(f'<p><a href="{html.escape(url)}">{html.escape(label)}</a></p>')
    story.append(Paragraph(f'<link href="{html.escape(url)}" color="#237c67">{html.escape(label)}</link>',styles['p']))

text('CAR-bench: Success and Consistency Across Three Task Types','h1')
text('Corrected English report | 19 October 2026 | GPT-6 Luna, medium reasoning | Gemini 2.5 Flash user simulation and scoring')
heading('Primary results: the first three trials')
text('The current official test split contains 50 Base tasks, 50 Hallucination tasks and 25 Disambiguation tasks. Primary results use trial IDs 0, 1 and 2 for every task. Historical GPT-5 comparisons use the same three trial IDs. Trials are not selected according to their outcomes. Budget interruptions are not scored as model failures.')
text('Correction: the earlier report used a multi-run average for Pass@1 and five-run combinatorial estimates for historical GPT-5. This edition follows the first-trial/first-three-trial implementation in the authors\' analyze_results.py and analyze_results_v2.py. Six-run estimates are supplementary only. Recalculation and translation use saved data, with no new model API calls or API charges.')
table([['Task type','Tasks','Stored valid trials','Pass@1','Pass@3','Pass^3','Gap (pp)']]+[[NAMES[i],str(C[k]['primary_complete_tasks']),str(C[k]['valid_trials_all']),*[pct(C[k]['scores'][m]) for m in METRICS],f"{100*C[k]['scores']['gap']:.1f}"] for i,k in enumerate(KINDS)],[101,39,65,70,70,70,72])
text('Pass@1 is the proportion of tasks successful on the first trial. Pass@3 is the proportion with at least one success in the first three trials. Pass^3 is the proportion successful in all three. The consistency gap is Pass@3 minus Pass^3. A smaller gap alone is not better: a task that always fails also has a zero gap.')
text('There are 375 primary trials. All 125 tasks have six complete repetitions (750 balanced trials). The 834 stored valid trials also include 41 Base and 43 Hallucination trials from an incomplete seventh round. These 84 trials are excluded from primary and balanced supplementary estimates.')
figure('consistency-distribution')

page();heading('Paper Table 4: descriptive context only')
text('Purple bars reproduce the GPT-5 thinking values in the paper\'s Table 4. Green bars show Luna on the current test split. The evaluation populations differ. These aggregate bars are background context, not a matched-task comparison and not evidence of a causal model-upgrade effect.')
figure('paper-overview')
text('The paper reports k=3 metrics. Stored historical GPT-5 trajectories include five repetitions, but the primary analysis in this report takes only trial IDs 0, 1 and 2. It does not average every three-trial combination of the five historical runs.')
heading('Why the full sets are not identical')
text('The current official task snapshots differ from some task definitions stored with the historical results. A shared task ID is not sufficient to establish an identical task. The audit compares all current task fields except task_id against every available historical definition, including user scripts, personas, environment configuration, expected actions, missing elements and task annotations.')
text('Model-to-model comparison therefore uses only the identical-definition subset on the next page. It retains the original matching cohort: 48 Base, 45 Hallucination and 19 Disambiguation tasks. Other tasks are excluded because of definition differences or historical infrastructure errors. In Disambiguation, six current test tasks have changed definitions. No saved run of a changed task is relabelled as a historical-task run.')

page();heading('Historical comparison on identical task definitions')
text('Both models use trial IDs 0, 1 and 2. Included tasks have definitions matching all available historical repetitions and no historical infrastructure errors. Matching the task and the metric does not control historical code, model-service, simulator or judge conditions.')
figure('matched-comparison')
table([['Task type','Matched tasks','Luna Pass^3','GPT-5 Pass^3','Difference (pp)','Paired 95% CI (pp)']]+[[NAMES[i],C[k]['matched_n'],pct(C[k]['matched']['luna']['pass_all3']),pct(C[k]['matched']['gpt5']['pass_all3']),pp(C[k]['matched']['difference']['pass_all3']),' to '.join(pp(v) for v in C[k]['matched']['difference_bootstrap_95ci']['pass_all3'])] for i,k in enumerate(KINDS)],[96,51,73,73,77,117])
figure('matched-uncertainty',420)
text('Intervals use 10,000 paired task-bootstrap resamples with seed 769. Every Pass^3 difference interval includes zero. The present sample does not establish a clear improvement or deterioration; this is not evidence of equivalence. The intervals do not remove historical confounding.')

page();heading('What the results support')
for i,k in enumerate(KINDS):
    text(f"{NAMES[i]}: the first-three-trial consistency gap is {100*C[k]['scores']['gap']:.1f} percentage points. The matched historical Pass^3 difference interval crosses zero, so this sample does not support a clear direction of change.")
text('On the 19 matched Disambiguation tasks, Luna succeeds on all three trials for 8 tasks, compared with 9 for historical GPT-5 (42.1% versus 47.4%). Luna has a higher first-trial success rate (73.7% versus 57.9%) and higher Pass@3 (84.2% versus 78.9%). Thus, lower Pass^3 here does not imply worse performance on every metric or a generally inferior model.')
heading('Failure components')
figure('failure-components')
text('Components can overlap within a trial and must not be summed into an overall failure rate. The official code skips policy and final-state scoring for Hallucination tasks. These entries are N/A, not zero error. User termination labels such as HALLUCINATION_ERROR and OUT_OF_SCOPE are stored separately under end_keywords in summary.json. They are model-generated judgments, not independent human annotations.')

page();heading('Supplementary analysis: six-run combinations')
text('Luna supplementary estimates use all 20 three-trial subsets of six repetitions. Historical GPT-5 supplementary estimates use all 10 three-trial subsets of five repetitions. Mean success averages all available balanced runs and differs from primary Pass@1, which uses the first trial only. These estimates are not substituted for the primary first-three-trial comparison.')
table([['Task type','Runs','Mean success','Estimated Pass@3','Estimated Pass^3']]+[[NAMES[i],6,*[pct(C[k]['balanced_scores'][m]) for m in METRICS]] for i,k in enumerate(KINDS)],[113,44,110,110,110])
figure('balanced-matched-comparison')
text('For a task with c successes in n runs, the combinatorial estimates are Pass^3 = C(c,3) / C(n,3) and Pass@3 = 1 - C(n-c,3) / C(n,3). Estimates are averaged equally across tasks. Here C(a,3) is zero when a is less than 3. These are k=3 estimates, not the proportion successful in all six runs.')
table([['Matched task type','Luna Pass^3','GPT-5 Pass^3','Difference (pp)','Paired 95% CI (pp)']]+[[NAMES[i],pct(C[k]['balanced_matched']['luna']['pass_all3']),pct(C[k]['balanced_matched']['gpt5']['pass_all3']),pp(C[k]['balanced_matched']['difference']['pass_all3']),' to '.join(pp(v) for v in C[k]['balanced_matched']['difference_bootstrap_95ci']['pass_all3'])] for i,k in enumerate(KINDS)],[113,78,78,88,130])
text('The matched sample sizes remain 48, 45 and 19. All supplementary Pass^3 difference intervals also cross zero. Historical confounding remains.')

page();heading('Supplementary sensitivity to the number of runs')
figure('repeat-sensitivity')
text('The chart increases the number of balanced repetitions used for estimation from three to six while keeping k fixed at 3. Additional trials were scheduled in a fixed order, rather than selected after inspecting successes or failures. Base and Hallucination were stopped during round seven at the user\'s request. Disambiguation was subsequently completed through round six and stopped. Only the common first six runs enter balanced supplementary analysis.')
table([['Task type','Complete runs','Success in all six runs']]+[[NAMES[i],6,pct(C[k]['balanced_all_n_success'])] for i,k in enumerate(KINDS)])
text('Success in all six is a separate, stricter measure and cannot be directly compared with success in all five historical runs. The six-run combinatorial results are unchanged by the primary-metric correction.')

page();heading('Costs and stopping conditions')
cost=S['total_cost_including_prior']
table([['Provider','Cumulative estimated USD'],['OpenAI',f"${cost['openai']:.6f}"],['Gemini',f"${cost['gemini']:.6f}"],['Total',f'${sum(cost.values()):.6f}']],[240,247])
text(f"These totals include the original Disambiguation experiment. There are {S['reserved_calls']} pending request reservations. {S['uncertain_calls']} service-error or interrupted requests returned no usage data; their conservative reservation of ${S['uncertain_cost_reserved']:.6f} remains included. Estimates use token usage and recorded prices; provider billing is authoritative. The original and extension ledgers must not be added together: the extension ledger already contains the original ledger as its prefix.")
text('The local early-stop threshold was US$9.50 for OpenAI under the requested US$10 total budget. Gemini originally had a US$5 budget and a US$4.50 local threshold; the supplement initially used a US$4.98 threshold. Following the user\'s NZ$10 top-up authorization, the local threshold was raised conservatively to US$9.50. The supplement stopped on completion rather than spending the remaining balance. Local thresholds govern this runner, not unrelated account usage. Events and reservations are retained in events.jsonl and usage-ledger.json.')
heading('Scope and limitations')
text('Gemini returned temporary 503 errors during execution. Completed results were retained and interrupted trials resumed. Gemini concurrency was subsequently limited to two requests; temporary failures received up to three attempts with 20/40-second waits. Each failed request retained a maximum-cost reservation. Truncated Gemini requests could retry with a 16,384-token limit; normal Gemini and Luna requests remained capped at 8,192 tokens. Attempts were recorded separately. Models, tasks and scoring prompts were not changed by this recovery.')
text('This experiment uses current official tasks, tools and scoring code, a Luna agent and Gemini simulation/scoring. It is not an exact reconstruction of the historical environment. Hallucination tasks test responses to missing tools or information; failure can also reflect invalid tool use or task deviation and is not a direct fabrication-rate measurement. Category difficulty and composition differ, so category score differences do not identify a causal capability effect.')
text('No reasoning=none control was run. The experiment cannot isolate the effect of enabling reasoning or attribute differences solely to a model upgrade. Service randomness, user-simulator error and judge error remain. There was no full independent human relabelling.')
heading('Reproducibility and evidence')
text('Official code commit: ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b. Dataset: johanneskirmayr/car-bench-dataset, revision 1fcf24ad802c42e04a0d8fe05b5ca0d481a4e7af. The first-three metrics were checked against both author analysis implementations, at aggregate and matched-task levels. Hash checks confirm that original trajectories and cost ledgers were unchanged by the correction.')
text('Evidence files alongside this report: summary.json, per-task-results.csv, trial-index.csv, task-definition-audit.json, historical-matched.json, first-three-verification.json, immutable-data-sha256.json and metric-correction-audit.json. The correction audit labels previous values as superseded. PNG/SVG figures and raw trial files are included in the reproduction package.')
link('Reproduction repository (private; access required)','https://github.com/victorcao1104/car-bench-gpt6-luna-reproduction')
link('Official CAR-bench repository','https://github.com/CAR-bench/car-bench')
web.append('<p>'+ ' | '.join(f'<a href="{f}">{f}</a>' for f in ['summary.json','per-task-results.csv','task-definition-audit.json','first-three-verification.json','usage-ledger.json'])+'</p>')
web.append('<p>Recorded pricing references: <a href="https://developers.openai.com/api/docs/models/gpt-6-luna">OpenAI</a> and <a href="https://ai.google.dev/gemini-api/docs/pricing">Google</a>.</p>')
html_doc='<!doctype html><html lang="en"><meta charset="utf-8"><title>CAR-bench: Corrected English Report</title><style>body{font:16px/1.65 Arial,sans-serif;max-width:1100px;margin:32px auto;padding:0 24px;color:#22313a}h1{font-size:30px}h2{font-size:23px}table{width:100%;border-collapse:collapse;font-size:14px}td{padding:8px;border-bottom:1px solid #dde5e5}tr:first-child{background:#eaf4f0;font-weight:bold}img{width:100%}hr{border:0;border-top:1px solid #ddd;margin:30px 0}</style>'+''.join(web)+'</html>'
(OUT/'comparison-report-en.html').write_text(html_doc,encoding='utf8')
def footer(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#667777'))
    canvas.drawCentredString(A4[0]/2,24,f'CAR-bench | Corrected English report | 19 Oct 2026 | {doc.page}')
pdf=OUT/'CAR-bench_Corrected_First3_Report_EN.pdf'
SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=43,bottomMargin=44,title='CAR-bench: Corrected First-Three-Trial Report',author='CAR-bench reproduction').build(story,onFirstPage=footer,onLaterPages=footer)
print('Generated English HTML and PDF:',pdf.name)
