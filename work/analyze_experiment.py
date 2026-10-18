import csv, html, importlib.metadata, json, math, random
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs'

def scores(values,k=3):
    n=len(values);c=sum(values)
    choose=lambda a,b: math.comb(a,b) if a>=b else 0
    return {'pass1':c/n,'pass_at3':1-choose(n-c,k)/choose(n,k),'pass_all3':choose(c,k)/choose(n,k)}

def average(rows):
    return {k:sum(r[k] for r in rows)/len(rows) for k in rows[0]}

def wilson(p,n):
    z=1.95996398454
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-half,center+half]

def bootstrap(rows):
    rng=random.Random(769); out=defaultdict(list)
    for _ in range(10000):
        sample=[rng.choice(rows) for i in rows]
        for k,v in average(sample).items():out[k].append(v)
    return {k:[sorted(v)[250],sorted(v)[9749]] for k,v in out.items()}

def main():
    versions=sorted((d.metadata['Name']+'=='+d.version) for d in importlib.metadata.distributions())
    (ROOT/'work/dependency-versions.txt').write_text('\n'.join(versions),encoding='utf-8')
    rows=[]; grouped={}; failures=[]; components=Counter()
    for path in sorted((OUT/'trajectories').glob('*.json')):
        r=json.loads(path.read_text(encoding='utf-8'))
        if len(r)!=3 or {x['trial'] for x in r}!={0,1,2}:continue
        if any('error' in x['info'] for x in r):raise ValueError('Infrastructure errors: '+path.stem)
        values=[int(x['reward']==1) for x in sorted(r,key=lambda x:x['trial'])]
        grouped[path.stem]=r
        s=scores(values);s['gap']=s['pass_at3']-s['pass_all3']
        rows.append({'task_id':path.stem,'successes':sum(values),'trials':3,**s})
        for x in r:
            ri=x['info'].get('reward_info',{}).get('info',{})
            for k,v in ri.items():
                if k.startswith('r_') and isinstance(v,(int,float)) and v==0:components[k]+=1
            if x['reward']!=1:
                failures.append({'task_id':path.stem,'trial':x['trial'],'reward_details':ri})
    metric_rows=[{k:r[k] for k in ['pass1','pass_at3','pass_all3','gap']} for r in rows]
    summary={'n_tasks':len(rows),'n_trials':len(rows)*3,'scores':average(metric_rows),
             'task_bootstrap_95ci':bootstrap(metric_rows),'success_distribution':dict(Counter(r['successes'] for r in rows)),
             'failed_components':dict(components)}
    summary['wilson_95ci']={k:wilson(summary['scores'][k],len(rows)) for k in ['pass_at3','pass_all3','gap']}
    tasks={t['task_id']:t for t in json.loads((OUT/'test-tasks.json').read_text())}
    summary['subgroups']={}
    for group,field in [('internal','disambiguation_element_internal'),('user','disambiguation_element_user')]:
        subset=[r for r in rows if tasks[r['task_id']].get(field)]
        if subset:summary['subgroups'][group]={'n_tasks':len(subset),**average([{k:r[k] for k in ['pass1','pass_at3','pass_all3','gap']} for r in subset])}
    ledger=json.loads((OUT/'usage-ledger.json').read_text())
    summary['cost_usd']={k:sum(r['cost_usd'] for r in ledger if r['provider']==k) for k in ['openai','gemini']}
    summary['unfinished_api_calls']=sum(r['status']=='reserved' for r in ledger)
    summary['infrastructure_retries']=json.loads((OUT/'run-status.json').read_text()).get('infrastructure_retries',0) if (OUT/'run-status.json').exists() else 0
    audit=json.loads((OUT/'baseline-task-audit.json').read_text())
    eligible={r['task_id']:r['baseline_id'] for r in audit if not r['different_fields']}
    source=next(p for p in (ROOT/'work/car-bench/results/disambiguation').rglob('*.json') if 'gpt-5-thinking' in str(p))
    baseline=json.loads(source.read_text())
    pairs=[];excluded=[]
    for task_id,old_id in eligible.items():
        if task_id not in grouped:continue
        old=[r for r in baseline if str(r['task_id'])==old_id]
        if len(old)!=5 or any('error' in r.get('info',{}) for r in old):
            excluded.append(task_id);continue
        newscore=scores([int(r['reward']==1) for r in grouped[task_id]])
        oldscore=scores([int(r['reward']==1) for r in old])
        pairs.append({'task_id':task_id,'luna':newscore,'gpt5':oldscore,'difference':{k:newscore[k]-oldscore[k] for k in newscore}})
    if pairs:
        summary['historical_matched_tasks']={'n':len(pairs),'luna':average([p['luna'] for p in pairs]),
            'gpt5':average([p['gpt5'] for p in pairs]),'difference':average([p['difference'] for p in pairs]),
            'difference_bootstrap_95ci':bootstrap([p['difference'] for p in pairs]),
            'excluded_infrastructure_tasks':excluded,'baseline_n_trials':5,
            'method':'Historical GPT-5: average over all 10 triplets among 5 repeats. Identical task definitions, but historical code/models/judges not controlled.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (OUT/'failures.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
    (OUT/'historical-comparison.json').write_text(json.dumps(pairs,indent=2),encoding='utf-8')
    with (OUT/'per-task-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
