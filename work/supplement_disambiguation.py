"""Balanced Base/Hallucination extension; shared cumulative budget, one trial per file."""
import json, random, shutil, threading, traceback, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import experiment as ex
from budget import Budget, BudgetStop

OUT=ex.OUT/'extension'
OUT.mkdir(exist_ok=True)
ledger=OUT/'usage-ledger.json'
if not ledger.exists():shutil.copy2(ex.OUT/'usage-ledger.json',ledger)
ex.budget=Budget(ledger,{'openai':9.5,'gemini':9.5})
lock=threading.RLock()
event_path=OUT/'events.jsonl'

def event(**data):
    with lock:
        with event_path.open('a',encoding='utf-8') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
    print('EVENT',json.dumps(data,ensure_ascii=False),flush=True)

gemini_slots=threading.Semaphore(2)
def resilient_gemini(*args,**kwargs):
    """Transport-only retries. Each attempt reserves its own worst-case cost."""
    assert kwargs.get('custom_llm_provider')=='gemini'
    kwargs.update(max_tokens=8192,num_retries=0,timeout=90)
    for attempt in range(3):
        with gemini_slots:
            ix=ex.reserve('gemini',kwargs,maxout=kwargs['max_tokens'])
            try:r=ex.raw_completion(*args,**kwargs)
            except Exception as e:
                message=ex.safe_error(e)
                transient=('503' in message or 'ServiceUnavailableError' in message or '429' in message) and 'quota' not in message.lower()
                if transient:
                    with ex.budget.lock:
                        ex.budget.rows[ix].update(status='uncertain',reason='Transient service failure; full reservation retained',error=message)
                        ex.budget.save()
                    event(state='transient_api_error',provider='gemini',ledger_index=ix,attempt=attempt,error=message)
                if not transient or attempt==2:
                    ex.halt.set();raise ex.ExperimentStop(message)
            else:
                usage=r.usage.model_dump()
                cost=(usage['prompt_tokens']*.3+usage['completion_tokens']*2.5)/1e6
                ex.budget.settle(ix,cost,usage);r._hidden_params['response_cost']=cost
                if r.choices[0].finish_reason=='length':
                    dest=OUT/'infrastructure-errors'/f'truncated-response-{ix}.json';dest.parent.mkdir(exist_ok=True)
                    dest.write_text(r.model_dump_json(indent=2),encoding='utf-8')
                    event(state='truncated_simulator_response',ledger_index=ix,attempt=attempt,usage=usage)
                    if attempt==2:raise ex.ExperimentStop('Gemini output repeatedly truncated')
                    kwargs['max_tokens']=16384
                    continue
                return r
        time.sleep(20*(attempt+1))
ex.litellm.completion=resilient_gemini

def main():
    import car_bench.envs.car_voice_assistant.env as envmod
    from car_bench.types import Task
    from car_bench.envs.car_voice_assistant.mock_data import car_va_data_manager
    tasks={}
    for kind in ['disambiguation']:
        data=json.loads((ex.OUT/'test-tasks.json').read_text())
        tasks[kind]=[Task(**t) for t in data]
        p=OUT/(kind+'-tasks.json')
        if p.exists():assert json.loads(p.read_text())==data
        else:p.write_text(json.dumps(data,indent=2),encoding='utf-8')
    original=envmod._load_tasks
    def frozen(kind,split,**kw):
        if kind in tasks and split=='test':return [t.model_copy(deep=True) for t in tasks[kind]]
        return original(kind,split,**kw)
    envmod._load_tasks=frozen
    ids={k:[t.task_id for t in ts] for k,ts in tasks.items()}
    for j,k in enumerate(ids):random.Random(769+j).shuffle(ids[k])
    order=[(k,ids[k][i]) for i in range(max(map(len,ids.values()))) for k in ids if i<len(ids[k])]
    manifest={'task_order':order,'primary_repeats':3,'extra_repeats':'Disambiguation only, repeats 3,4,5 (zero-based); stop after six total repeats or budget guard',
       'code_commit':'ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b','data_revision':ex.DATA_REVISION,
       'agent':'gpt-6-luna','reasoning':'medium','simulator':'gemini-2.5-flash','user_thinking':True,
       'judge':'gemini-2.5-flash','split':'test','jobs':6,'gemini_concurrency_after_503':2,'transport_retry_attempts':3,'transport_retry_backoff_seconds':[20,40], 'gemini_truncation_fallback_max_tokens':16384,'seed':769,'budget_limits':ex.budget.limits,
       'prior_spend':{'openai':.102828915,'gemini':.5964163},
       'analysis':'Primary comparison uses first 3 completed repetitions per task; extra repetitions analyzed separately. Budget-stopped trials excluded, model failures retained.'}
    (OUT/'disambiguation-supplement-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    car_va_data_manager.initialize()
    def one(kind,task_id,repeat):
        if ex.halt.is_set():return False
        p=OUT/'trials'/kind/f'{task_id}_r{repeat}.json'
        if p.exists():
            old=json.loads(p.read_text());assert len(old)==1 and 'error' not in old[0]['info']
            return True
        args=ex.args_for(task_id);args.task_type=kind;args.num_trials=1
        event(state='started',kind=kind,task_id=task_id,repeat=repeat)
        agents=[]
        def factory(*a):
            agent=ex.LunaAgent();agents.append(agent);return agent
        try:
            res=ex.benchmark.run(args,str(p),custom_agent_factory=factory)
            assert len(res)==1
            if 'error' in res[0].info:raise ex.ExperimentStop('Infrastructure error in '+str(p))
            event(state='completed',kind=kind,task_id=task_id,repeat=repeat,reward=res[0].reward,
                  cost={k:ex.budget.total(k) for k in ex.budget.limits})
            return True
        except BaseException as e:
            ex.halt.set()
            if agents:
                folder=OUT/'interrupted-traces';folder.mkdir(exist_ok=True)
                history=[{k:v for k,v in message.items() if k!='encrypted_content'} for message in agents[0].history]
                (folder/f'{task_id}_r{repeat}_{time.time_ns()}.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
            event(state='budget_stop' if isinstance(e,BudgetStop) else 'interrupted',kind=kind,task_id=task_id,
                  repeat=repeat,error=ex.safe_error(e),exception=type(e).__name__)
            return False
    def block(entry,repeats):
        for repeat in repeats:
            if not one(*entry,repeat):break
    with ThreadPoolExecutor(max_workers=6) as pool:
        for repeat in range(3,6):
            if ex.halt.is_set():break
            event(state='disambiguation_supplement_sweep',repeat=repeat)
            list(pool.map(lambda item:block(item,[repeat]),order))
    event(state='finished',cost={k:ex.budget.total(k) for k in ex.budget.limits},
          unresolved_reservations=sum(r['status']=='reserved' for r in ex.budget.rows))

if __name__=='__main__':main()
