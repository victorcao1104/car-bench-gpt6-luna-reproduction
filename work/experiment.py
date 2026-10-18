"""CAR-bench runner: original benchmark, Responses adapter, per-call spend guard."""
import argparse, copy, hashlib, json, os, random, sys, time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'work'
OUT=ROOT/'outputs'
OUT.mkdir(exist_ok=True)
os.environ['HF_HOME']=str(ROOT.parents[1]/'work'/'hf769')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
os.environ['LITELLM_LOCAL_MODEL_COST_MAP']='True'
os.environ['TIKTOKEN_CACHE_DIR']=str(WORK/'token-cache')
from dotenv import load_dotenv
load_dotenv(ROOT/'.env.local',override=True)
from budget import Budget, BudgetStop
DATA_REVISION='1fcf24ad802c42e04a0d8fe05b5ca0d481a4e7af'
import huggingface_hub, datasets
_snapshot_download=huggingface_hub.snapshot_download
_load_dataset=datasets.load_dataset
def pinned_snapshot(*a,**kw):
    return _snapshot_download(*a,**{**kw,'revision':DATA_REVISION})
def pinned_dataset(*a,**kw):
    return _load_dataset(*a,**{**kw,'revision':DATA_REVISION})
huggingface_hub.snapshot_download=pinned_snapshot
datasets.load_dataset=pinned_dataset
budget=Budget(OUT/'usage-ledger.json',{'openai':9.50,'gemini':4.50})
if not budget.rows:
    for provider,cost in [('openai',.0000034),('gemini',.0000434)]:
        ix=budget.reserve(provider,cost);budget.settle(ix,cost,{'role':'connectivity_check'})

import litellm
raw_completion=litellm.completion

class ExperimentStop(BaseException): pass
halt=threading.Event()

def reserve(provider,payload,maxout=8192):
    if halt.is_set(): raise ExperimentStop('Stopped after another request failed')
    # UTF-8 byte count is a deliberately loose upper estimate of text tokens;
    # double it and add framing/schema allowance. No cache discount assumed.
    n=2*len(json.dumps(payload,default=str,ensure_ascii=False).encode('utf-8'))+8192
    ri,ro=(.125,.5) if provider=='openai' else (.3,2.5)
    return budget.reserve(provider,(n*ri+maxout*ro)/1e6)

def safe_error(e):
    s=str(e)
    for k in ['OPENAI_API_KEY','GEMINI_API_KEY']:
        if os.environ.get(k): s=s.replace(os.environ[k],'[REDACTED]')
    return s[:1500]

def gemini_completion(*args,**kwargs):
    if kwargs.get('custom_llm_provider')!='gemini': raise ExperimentStop('Unexpected provider')
    kwargs.update(max_tokens=8192,num_retries=0,timeout=90)
    ix=reserve('gemini',kwargs)
    try: r=raw_completion(*args,**kwargs)
    except Exception as e:
        halt.set(); raise ExperimentStop(safe_error(e))
    u=r.usage.model_dump()
    # completion_tokens includes reasoning in LiteLLM Gemini normalization.
    cost=(u['prompt_tokens']*.3+u['completion_tokens']*2.5)/1e6
    budget.settle(ix,cost,u)
    r._hidden_params['response_cost']=cost
    if r.choices[0].finish_reason=='length': raise ExperimentStop('Gemini output truncated')
    return r

litellm.completion=gemini_completion
sys.path.insert(0,str(WORK/'car-bench'))
import run as benchmark
from car_bench.agents.base import Agent
from car_bench.types import AgentState
from openai import OpenAI
client=OpenAI(max_retries=0,timeout=90)

def convert_messages(messages):
    out=[]
    for m in messages:
        if m['role']=='tool':
            out.append({'type':'function_call_output','call_id':m['tool_call_id'],'output':m['content']})
        elif m['role'] in ['system','user']:
            out.append({'role':m['role'],'content':m['content']})
        else: raise ExperimentStop('Unexpected new message role '+m['role'])
    return out

class LunaAgent(Agent):
    def __init__(self): self.history=[]; self.seen=0
    def get_init_state(self,system_prompt,initial_observation):
        return AgentState(messages=[{'role':'system','content':system_prompt},{'role':'user','content':initial_observation}],start_time_s=time.time())
    def generate_next_message(self,state,tools_info):
        self.history.extend(convert_messages(state.messages[self.seen:]))
        tools=[]
        for t in tools_info:
            f=copy.deepcopy(t['function']);f.pop('cache_control',None)
            tools.append({'type':'function',**f,'strict':False})
        payload=dict(model='gpt-6-luna',input=self.history,tools=tools,
                     reasoning={'effort':'medium'},max_output_tokens=8192,store=False,
                     include=['reasoning.encrypted_content'])
        ix=reserve('openai',payload)
        start=time.time()
        try: r=client.responses.create(**payload)
        except Exception as e:
            halt.set(); raise ExperimentStop(safe_error(e))
        u=r.usage.model_dump()
        details=u.get('input_tokens_details') or {}
        cached=details.get('cached_tokens',0) or 0
        writes=details.get('cache_write_tokens',0) or 0
        cost=((u['input_tokens']-cached-writes)*.1+cached*.01+writes*.125+u['output_tokens']*.5)/1e6
        budget.settle(ix,cost,u)
        if r.status!='completed': raise ExperimentStop('OpenAI response status '+str(r.status))
        self.history.extend(x.model_dump(exclude_none=True) for x in r.output)
        calls=[{'id':x.call_id,'type':'function','function':{'name':x.name,'arguments':x.arguments}} for x in r.output if x.type=='function_call']
        message={'role':'assistant','content':r.output_text or None,'tool_calls':calls or None}
        state.messages.append(message)
        self.seen=len(state.messages)
        state.total_cost+=cost
        state.total_prompt_tokens+=u['input_tokens']
        state.total_completion_tokens+=u['output_tokens']
        state.latest_prompt_tokens=u['input_tokens']
        state.least_prompt_tokens=min(state.least_prompt_tokens,u['input_tokens'])
        state.total_llm_induced_latency_ms+=(time.time()-start)*1000
        return message,state

def args_for(task_id):
    return argparse.Namespace(env='car_voice_assistant',user_strategy='llm',
        user_model='gemini-2.5-flash',user_model_provider='gemini',
        policy_evaluator_strategy='llm',policy_evaluator_model='gemini-2.5-flash',policy_evaluator_model_provider='gemini',
        task_type='disambiguation',task_split='test',user_thinking=True,
        use_user_as_a_tool_tools=False,evaluate_policy=True,score_tool_execution_errors=True,score_policy_errors=True,
        task_id_filter=[task_id],num_tasks=-1,num_trials=3,shuffle=0,max_concurrency=1,
        planning_and_thinking_tool=True,agent_strategy='tool-calling',model='gpt-6-luna',model_provider='openai',
        remove_non_standard_fields_from_tools=False,thinking=True,reasoning_effort='medium',interleaved_thinking=False,temperature=1.)

def main():
    p=argparse.ArgumentParser();p.add_argument('--tasks',type=int,default=1);p.add_argument('--jobs',type=int,default=1);opts=p.parse_args()
    import car_bench.envs.car_voice_assistant.env as envmod
    tasks=envmod._load_tasks('disambiguation','test')
    # Freeze source task snapshot and use independent copies for each environment.
    snapshot=[t.model_dump() for t in tasks]
    snapfile=OUT/'test-tasks.json'
    if snapfile.exists() and json.loads(snapfile.read_text())!=snapshot: raise ExperimentStop('Dataset changed')
    snapfile.write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    original_loader=envmod._load_tasks
    def frozen_loader(task_type,task_split,**kw):
        if (task_type,task_split)!=('disambiguation','test'): return original_loader(task_type,task_split,**kw)
        return [t.model_copy(deep=True) for t in tasks]
    envmod._load_tasks=frozen_loader
    ids=[t.task_id for t in tasks];random.Random(769).shuffle(ids)
    manifest={'code_commit':'ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b','data_revision':DATA_REVISION,'task_order':ids,
        'task_sha256':hashlib.sha256(snapfile.read_bytes()).hexdigest(),'agent':'gpt-6-luna','reasoning_effort':'medium',
        'simulator':'gemini-2.5-flash','simulator_thinking':'low (official runner setting)',
        'judge':'gemini-2.5-flash','repetitions':3,'seed':769,'split':'test','max_output_tokens':8192,
        'budget_stop_usd':budget.limits,'note':'Current official dataset/code; not a historical snapshot of the paper.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    from car_bench.envs.car_voice_assistant.mock_data import car_va_data_manager
    car_va_data_manager.initialize()
    def execute_task(task_id):
        path=OUT/'trajectories'/f'{task_id}.json'
        if path.exists():
            old=json.loads(path.read_text())
            if len(old)==3 and all('error' not in x.get('info',{}) for x in old): return
            raise ExperimentStop('Incomplete existing task, requires review: '+task_id)
        results=benchmark.run(args_for(task_id),str(path),custom_agent_factory=lambda *a: LunaAgent())
        if any('error' in r.info for r in results): raise ExperimentStop('Infrastructure error recorded: '+task_id)
        print('PROGRESS',task_id,[r.reward for r in results],{k:round(budget.total(k),6) for k in budget.limits},flush=True)
    with ThreadPoolExecutor(max_workers=opts.jobs) as pool:
        list(pool.map(execute_task,ids[:opts.tasks]))
    print('FINISHED',flush=True)

if __name__=='__main__':
    try:main()
    except (BudgetStop,ExperimentStop) as e:
        (OUT/'stop.json').write_text(json.dumps({'reason':str(e)},indent=2),encoding='utf-8')
        print('STOP',str(e),flush=True);sys.exit(2)
