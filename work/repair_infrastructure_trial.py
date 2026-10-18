"""Replay only the trial interrupted by a local ledger write failure."""
import json
import experiment as ex

task_id='disambiguation_47'
path=ex.OUT/'trajectories'/f'{task_id}.json'
old=json.loads(path.read_text())
bad=[r for r in old if 'error' in r.get('info',{})]
assert len(old)==3 and len(bad)==1 and bad[0]['trial']==1
assert 'usage-ledger.tmp' in bad[0]['info']['error']
assert "ix=reserve('gemini'" in bad[0]['info']['traceback']
archive=ex.OUT/'infrastructure-errors'
archive.mkdir(exist_ok=True)
(archive/'disambiguation_47_trial1.json').write_text(json.dumps(bad[0],indent=2),encoding='utf-8')
pending=[i for i,r in enumerate(ex.budget.rows) if r['status']=='reserved']
assert len(pending)==1 and ex.budget.rows[pending[0]]['provider']=='gemini'
row=ex.budget.rows[pending[0]]
row.update(status='not_sent',reserved_cost_usd=row['cost_usd'],cost_usd=0,
           reason='Reservation save failed before the API call; trace archived in infrastructure-errors.')
ex.budget.save()
args=ex.args_for(task_id);args.num_trials=1
newpath=archive/'replacement-trial.json'
assert not newpath.exists()
new=ex.benchmark.run(args,str(newpath),custom_agent_factory=lambda *a:ex.LunaAgent())
assert len(new)==1 and 'error' not in new[0].info
replacement=new[0].model_dump();replacement['trial']=1
fixed=[replacement if r['trial']==1 else r for r in old]
path.write_text(json.dumps(fixed,indent=2),encoding='utf-8')
status={'completed_trials':75,'infrastructure_retries':1,'task_id':task_id,'trial':1,
        'reason':'Transient Windows ledger rename denial, not an agent failure',
        'replacement_reward':replacement['reward'],'model_or_prompt_changes':False}
(ex.OUT/'run-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
if (ex.OUT/'stop.json').exists():(ex.OUT/'stop.json').rename(archive/'original-stop.json')
print('REPAIRED',status,flush=True)
