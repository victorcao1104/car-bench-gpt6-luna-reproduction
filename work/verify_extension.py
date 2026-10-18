from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent.parent
out=root/'outputs'; ext=out/'extension'
s=json.loads((ext/'summary.json').read_text())
expected={'base':50,'hallucination':50,'disambiguation':25}
for k,n in expected.items():
 d=s['categories'][k]
 assert d['primary_complete_tasks']==n and d['balanced_repeats']==6,(k,d['balanced_repeats'])
assert s['categories']['disambiguation']['valid_trials_all']==150
assert s['reserved_calls']==0
assert s['total_cost_including_prior']['openai']<9.5
assert s['total_cost_including_prior']['gemini']<9.5
old=json.loads((out/'usage-ledger.json').read_text());new=json.loads((ext/'usage-ledger.json').read_text())
assert old==new[:len(old)]
repo=root/'work/github-repo'
for p in (out/'trajectories').glob('*.json'):
 assert p.read_bytes()==(repo/'outputs/trajectories'/p.name).read_bytes()
assert json.loads((ext/'disambiguation-tasks.json').read_text())==json.loads((out/'test-tasks.json').read_text())
records={'checks':'125 tasks each have six valid repetitions; Disambiguation exactly 150 valid trials; original trajectories and ledger prefix unchanged; no unresolved requests; provider guards respected','categories':{k:{f:d[f] for f in ['available_tasks','valid_trials_all','balanced_repeats']} for k,d in s['categories'].items()},'costs_usd':s['total_cost_including_prior']}
(ext/'verification.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records,indent=2))
