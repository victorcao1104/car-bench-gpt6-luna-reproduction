import json
import math
import threading
import time
from functools import wraps
from datetime import datetime, timezone

class BudgetStop(BaseException): pass

def synchronized(fn):
    @wraps(fn)
    def wrapped(self,*args,**kwargs):
        with self.lock: return fn(self,*args,**kwargs)
    return wrapped

class Budget:
    def __init__(self,path,limits):
        self.lock=threading.RLock()
        self.path=path
        self.limits=limits
        self.rows=json.loads(path.read_text()) if path.exists() else []
    @synchronized
    def total(self,provider):
        return sum(r['cost_usd'] for r in self.rows if r['provider']==provider)
    @synchronized
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        # Windows may deny rename while an observer briefly reads the ledger.
        # Retry only the local commit, never the paid API request.
        for attempt in range(20):
            try:
                tmp.replace(self.path)
                break
            except PermissionError:
                if attempt==19: raise BudgetStop('Cannot persist budget ledger')
                time.sleep(.05)
    @synchronized
    def reserve(self,provider,cost):
        if not math.isfinite(cost) or cost<0: raise ValueError('Invalid cost')
        if self.total(provider)+cost>self.limits[provider]:
            raise BudgetStop('Budget guard stopped '+provider)
        self.rows.append(dict(provider=provider,cost_usd=cost,status='reserved',time=datetime.now(timezone.utc).isoformat()))
        self.save()
        return len(self.rows)-1
    @synchronized
    def settle(self,index,cost,usage):
        if not math.isfinite(cost) or cost<0: raise ValueError('Invalid cost')
        self.rows[index].update(cost_usd=cost,status='completed',usage=usage)
        self.save()
        if self.total(self.rows[index]['provider'])>self.limits[self.rows[index]['provider']]:
            raise BudgetStop('Cost exceeded conservative reservation')
