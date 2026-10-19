"""Offline analysis; never imports the API runner."""
import json, math, csv, hashlib, html
from pathlib import Path
from collections import defaultdict,Counter
from analyze_experiment import scores,paper_scores,first_three,average,bootstrap
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs';EXT=OUT/'extension'
KINDS=['base','hallucination','disambiguation']
PAPER={'base':{'pass1':.76,'pass_at3':.88,'pass_all3':.66},
       'hallucination':{'pass1':.74,'pass_at3':.82,'pass_all3':.60},
       'disambiguation':{'pass1':.46,'pass_at3':.68,'pass_all3':.36}}

def main():
    summary={};audit=[];csvrows=[];trialrows=[];failures=[];matched_details={}
    for kind in KINDS:
        source=OUT/'test-tasks.json' if kind=='disambiguation' else EXT/(kind+'-tasks.json')
        tasks={t['task_id']:t for t in json.loads(source.read_text())}
        groups=defaultdict(dict)
        trialfiles={}
        if kind=='disambiguation':
            for p in (OUT/'trajectories').glob('*.json'):
                for r in json.loads(p.read_text()):
                    groups[r['task_id']][r['trial']]=r;trialfiles[(r['task_id'],r['trial'])]=str(p.relative_to(OUT)).replace('\\','/')
        if True:
            for p in (EXT/'trials'/kind).glob('*.json'):
                data=json.loads(p.read_text());assert len(data)==1
                r=data[0];repeat=int(p.stem.rsplit('_r',1)[1])
                if 'error' in r.get('info',{}):continue
                groups[r['task_id']][repeat]=r
                trialfiles[(r['task_id'],repeat)]=str(p.relative_to(OUT)).replace('\\','/')
        for task_id,rs in groups.items():
            for repeat,r in sorted(rs.items()):trialrows.append({'kind':kind,'task_id':task_id,'repeat_zero_based':repeat,'primary':repeat<3,'reward':r['reward'],'path_relative_to_outputs':trialfiles[(task_id,repeat)]})
        primary={k:[v[i] for i in range(3)] for k,v in groups.items() if all(i in v for i in range(3))}
        primary_scores=[];components=Counter();endwords=Counter()
        for task_id,rs in primary.items():
            values=[int(r['reward']==1) for r in rs];sc=paper_scores(values);sc['gap']=sc['pass_at3']-sc['pass_all3']
            primary_scores.append(sc)
            csvrows.append({'kind':kind,'task_id':task_id,'primary_successes':sum(values),'valid_repetitions':len(groups[task_id]),**sc})
            for i,r in enumerate(rs):
                info=r['info'].get('reward_info',{}).get('info',{})
                for k,v in info.items():
                    if k.startswith('r_') and isinstance(v,(int,float)) and v==0:components[k]+=1
                endwords[str(info.get('end_conversation_keyword'))]+=1
                if r['reward']!=1:failures.append({'kind':kind,'task_id':task_id,'repeat':i,'reward':r['reward'],'details':info})
        if not primary:continue
        historical_path=next(p for p in (ROOT/'work/car-bench/results'/kind).rglob('*.json') if 'gpt-5-thinking' in str(p))
        hist=defaultdict(list)
        for r in json.loads(historical_path.read_text()):hist[str(r['task_id'])].append(r)
        pairs=[]
        for task_id,task in tasks.items():
            old=hist.get(task_id.split('_')[-1],[])
            oldtasks=[r['info']['task'] for r in old if 'task' in r.get('info',{})]
            fields=set(task)-{'task_id'}
            differences=sorted(f for f in fields if not oldtasks or any(t.get(f)!=task.get(f) for t in oldtasks))
            eligible=bool(oldtasks) and not differences and len(old)>=3 and not any('error' in r.get('info',{}) for r in old)
            audit.append({'kind':kind,'task_id':task_id,'different_fields':differences,'historical_trials':len(old),'eligible':eligible})
            if eligible and task_id in primary:
                ns=paper_scores([int(r['reward']==1) for r in primary[task_id]])
                os=paper_scores(first_three(old))
                pairs.append({'task_id':task_id,'used_trial_ids':[0,1,2],'luna':ns,'gpt5':os,'gpt5_combinatorial_supplement':scores([int(r['reward']==1) for r in old]),'difference':{k:ns[k]-os[k] for k in ns}})
        common=min(len(v) for v in groups.values()) if len(groups)==len(tasks) else 0
        balanced=[]
        if common>=3:
            for v in groups.values():
                if all(i in v for i in range(common)):balanced.append(scores([int(v[i]['reward']==1) for i in range(common)]))
        record={'available_tasks':len(tasks),'primary_complete_tasks':len(primary),'primary_trials':len(primary)*3,
            'valid_trials_all':sum(map(len,groups.values())),'scores':average(primary_scores),
            'bootstrap_95ci':bootstrap(primary_scores),'success_distribution':dict(Counter(sum(r['reward']==1 for r in rs) for rs in primary.values())),
            'failure_components':dict(components),'end_keywords':dict(endwords),'paper_gpt5':PAPER[kind],
            'matched_n':len(pairs),'excluded_definition_or_infrastructure':len(tasks)-sum(a['eligible'] for a in audit if a['kind']==kind),
            'historical_source':str(historical_path.relative_to(ROOT)).replace('\\','/'),
            'historical_sha256':hashlib.sha256(historical_path.read_bytes()).hexdigest(),
            'balanced_repeats':common,'balanced_scores':average(balanced) if len(balanced)==len(tasks) else None}
        if pairs:
            record['matched']={label:average([p[label] for p in pairs]) for label in ['luna','gpt5','difference']}
            record['matched']['difference_bootstrap_95ci']=bootstrap([p['difference'] for p in pairs])
        record['repeat_sensitivity']={}
        if len(balanced)==len(tasks):
            for n in range(3,common+1):
                record['repeat_sensitivity'][str(n)]=average([scores([int(v[i]['reward']==1) for i in range(n)]) for v in groups.values()])
            if pairs:
                extra=[]
                for p in pairs:
                    ns=scores([int(groups[p['task_id']][i]['reward']==1) for i in range(common)])
                    old_supp=p['gpt5_combinatorial_supplement']
                    extra.append({'luna':ns,'gpt5':old_supp,'difference':{k:ns[k]-old_supp[k] for k in ns}})
                record['balanced_matched']={label:average([p[label] for p in extra]) for label in ['luna','gpt5','difference']}
                record['balanced_matched']['difference_bootstrap_95ci']=bootstrap([p['difference'] for p in extra])
        if common>=3 and len(balanced)==len(tasks):
            counts=[sum(v[i]['reward']==1 for i in range(common)) for v in groups.values()]
            record['balanced_success_distribution']=dict(Counter(counts))
            record['balanced_all_n_success']=sum(c==common for c in counts)/len(counts)
        summary[kind]=record;matched_details[kind]=pairs
    ledger=json.loads((EXT/'usage-ledger.json').read_text())
    costs={k:sum(r['cost_usd'] for r in ledger if r['provider']==k) for k in ['openai','gemini']}
    events=[json.loads(line) for line in (EXT/'events.jsonl').read_text().splitlines()]
    result={'categories':summary,'total_cost_including_prior':costs,'reserved_calls':sum(r['status']=='reserved' for r in ledger),
       'completed_usage_cost':{k:sum(r['cost_usd'] for r in ledger if r['provider']==k and r['status']=='completed') for k in ['openai','gemini']},
       'uncertain_calls':sum(r['status']=='uncertain' for r in ledger),
       'uncertain_cost_reserved':sum(r['cost_usd'] for r in ledger if r['status']=='uncertain'),
       'stops':[e for e in events if e['state'] in ['budget_stop','interrupted','user_stop']],
       'primary_trial_ids':[0,1,2],
       'primary_method':'Both models: Pass@1=trial 0 success; Pass@3=any success in trials 0,1,2; Pass^3=all three successful. Matches author analyze_results.py and analyze_results_v2.py.',
       'supplementary_method':'Luna six-run and historical GPT-5 five-run combination estimates only. Supplementary pass1 means average per-run success, not primary first-trial Pass@1.',
       'note':'Offline recalculation only. No API calls. Original task matching cohort retained. No causal model improvement claim.'}
    for name,data in [('summary.json',result),('task-definition-audit.json',audit),('historical-matched.json',matched_details),('failures.json',failures)]:
        (EXT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (EXT/'per-task-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    with (EXT/'trial-index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(trialrows[0]));w.writeheader();w.writerows(trialrows)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
