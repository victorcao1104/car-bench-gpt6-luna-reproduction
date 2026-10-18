"""Test the actual transport function in isolation, with no provider calls."""
import ast,json,tempfile,threading,types,unittest
from pathlib import Path
from budget import Budget,BudgetStop

class Stop(BaseException):pass
class Response:
    def __init__(self,length=False):
        self.usage=types.SimpleNamespace(model_dump=lambda:{'prompt_tokens':100,'completion_tokens':10})
        self.choices=[types.SimpleNamespace(finish_reason='length' if length else 'stop')]
        self._hidden_params={}
    def model_dump_json(self,**kw):return '{}'

class TransportTests(unittest.TestCase):
    def setup_function(self,d,call,limit=10):
        budget=Budget(Path(d)/'ledger.json',{'gemini':limit})
        ex=types.SimpleNamespace(budget=budget,raw_completion=call,safe_error=str,halt=threading.Event(),ExperimentStop=Stop)
        def reserve(provider,payload,maxout):return budget.reserve(provider,maxout*2.5/1e6+.01)
        ex.reserve=reserve
        node=next(n for n in ast.parse((Path(__file__).parent/'extend_experiment.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='resilient_gemini')
        events=[];ns={'ex':ex,'gemini_slots':threading.Semaphore(2),'OUT':Path(d),'event':lambda **x:events.append(x),'time':types.SimpleNamespace(sleep=lambda _:None)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'real_transport','exec'),ns)
        return ns['resilient_gemini'],budget,events
    def test_503_keeps_first_attempt_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def call(**kw):
                calls.append(kw)
                if len(calls)==1:raise RuntimeError('503 ServiceUnavailableError')
                return Response()
            fn,b,events=self.setup_function(d,call)
            fn(custom_llm_provider='gemini')
            self.assertEqual(len(calls),2)
            self.assertEqual([r['status'] for r in b.rows],['uncertain','completed'])
            self.assertGreater(b.total('gemini'),.03)
    def test_no_call_if_reservation_exceeds_cap(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[];fn,b,events=self.setup_function(d,lambda **kw:calls.append(kw),limit=.001)
            with self.assertRaises(BudgetStop):fn(custom_llm_provider='gemini')
            self.assertEqual(calls,[])
    def test_truncation_uses_larger_reserved_output_budget(self):
        with tempfile.TemporaryDirectory() as d:
            limits=[];reservations=[]
            def call(**kw):
                limits.append(kw['max_tokens']);reservations.append(b.rows[-1]['cost_usd'])
                return Response(length=len(limits)==1)
            fn,b,events=self.setup_function(d,call)
            fn(custom_llm_provider='gemini')
            self.assertEqual(limits,[8192,16384])
            self.assertGreater(reservations[1],reservations[0])
            self.assertTrue(all(r['status']=='completed' for r in b.rows))
            self.assertEqual(events[0]['state'],'truncated_simulator_response')

if __name__=='__main__':unittest.main()
