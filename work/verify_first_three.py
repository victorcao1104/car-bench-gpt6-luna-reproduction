"""Offline cross-check against the author's actual metric functions, without API imports."""
import ast, hashlib, json, math
from pathlib import Path
from typing import Dict
from collections import defaultdict
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs'; EXT=OUT/'extension'
summary=json.loads((EXT/'summary.json').read_text())
functions=['calculate_pass_power_k_scores','calculate_pass_at_k_scores']
namespaces=[]
for name in ['analyze_results.py','analyze_results_v2.py']:
    tree=ast.parse((ROOT/'work/car-bench'/name).read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions]
    assert len(nodes)==2
    ns={'Dict':Dict};exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),ns)
    namespaces.append(ns)

def check(records,expected):
    for ns in namespaces:
        at=ns[functions[1]](records,3);power=ns[functions[0]](records,3)
        actual={'pass1':at['Pass@1'],'pass_at3':at['Pass@3'],'pass_all3':power['Pass^3']}
        for key,value in actual.items():assert math.isclose(value,expected[key],abs_tol=1e-12),(key,value,expected)

pairs=json.loads((EXT/'historical-matched.json').read_text())
before=json.loads((ROOT/'work/correction-before/outputs/extension/summary.json').read_text())
counts={}
for kind,d in summary['categories'].items():
    groups=defaultdict(dict)
    if kind=='disambiguation':
        for p in (OUT/'trajectories').glob('*.json'):
            for r in json.loads(p.read_text()):groups[r['task_id']][r['trial']]=r
    for p in (EXT/'trials'/kind).glob('*.json'):
        r=json.loads(p.read_text())[0]
        if 'error' in r.get('info',{}):continue
        i=int(p.stem.rsplit('_r',1)[1]);assert i not in groups[r['task_id']]
        groups[r['task_id']][i]=r
    assert all(all(i in g for i in range(6)) for g in groups.values())
    check(groups,d['scores'])
    selected={p['task_id'] for p in pairs[kind]}
    check({k:v for k,v in groups.items() if k in selected},d['matched']['luna'])
    historical=defaultdict(dict)
    for r in json.loads((ROOT/d['historical_source']).read_text()):
        key=str(r['task_id']);assert r['trial'] not in historical[key]
        historical[key][r['trial']]=r
    check({k:historical[k.split('_')[-1]] for k in selected},d['matched']['gpt5'])
    assert d['balanced_scores']==before['categories'][kind]['balanced_scores']
    assert d['balanced_matched']==before['categories'][kind]['balanced_matched']
    assert d['matched_n']==before['categories'][kind]['matched_n']
    for p in pairs[kind]:
        check({p['task_id']:groups[p['task_id']]},p['luna'])
        check({p['task_id']:historical[p['task_id'].split('_')[-1]]},p['gpt5'])
    counts[kind]={'primary_tasks':len(groups),'primary_trials':3*len(groups),'matched_tasks':len(selected)}
assert summary['total_cost_including_prior']==before['total_cost_including_prior']
hashes=json.loads((ROOT/'work/correction-before/immutable-hashes.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
result={'status':'passed','author_functions_checked_in':['analyze_results.py','analyze_results_v2.py'],
 'used_trial_ids':[0,1,2],'pass1':'trial 0 only','categories':counts,
 'six_run_supplementary_results_unchanged':True,'raw_data_and_ledgers_unchanged':True,
 'immutable_file_count':len(hashes),'new_api_calls':0,'new_api_cost_usd':0,
 'total_cost_including_prior':summary['total_cost_including_prior']}
(EXT/'first-three-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(EXT/'immutable-data-sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
