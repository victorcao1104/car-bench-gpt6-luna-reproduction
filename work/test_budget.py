import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path
from budget import Budget, BudgetStop

class BudgetTests(unittest.TestCase):
    def test_transient_windows_reader_lock_retries_local_write(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'tmp') as d:
            b=Budget(Path(d)/'ledger.json',{'gemini':1})
            original=Path.replace
            calls=[]
            def replace(path,target):
                calls.append(1)
                if len(calls)==1:raise PermissionError('Temporary Windows reader lock')
                return original(path,target)
            with patch.object(Path,'replace',replace):b.reserve('gemini',.1)
            self.assertEqual(len(calls),2)
            self.assertAlmostEqual(Budget(b.path,b.limits).total('gemini'),.1)
    def test_concurrent_reservations_never_overspend(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'tmp') as d:
            b=Budget(Path(d)/'ledger.json',{'gemini':1})
            def attempt(_):
                try: b.reserve('gemini',.1); return True
                except BudgetStop: return False
            with ThreadPoolExecutor(max_workers=4) as pool:
                successes=list(pool.map(attempt,range(20)))
            self.assertLessEqual(sum(successes),10)
            self.assertLessEqual(b.total('gemini'),1)
    def test_restart_counts_reserved_calls_and_provider_limits(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'tmp') as d:
            p=Path(d)/'ledger.json'
            b=Budget(p, {'openai':1., 'gemini':.5})
            i=b.reserve('gemini',.4)
            with self.assertRaises(BudgetStop): b.reserve('gemini',.11)
            b.settle(i,.1, {'tokens':10})
            b=Budget(p, {'openai':1.,'gemini':.5})
            b.reserve('gemini',.3)
            b.reserve('openai',.9)
            with self.assertRaises(BudgetStop): b.reserve('openai',.2)
            self.assertAlmostEqual(b.total('gemini'),.4)
    def test_bad_cost_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'tmp') as d:
            b=Budget(Path(d)/'ledger.json',{'gemini':1})
            for value in [-1,float('nan'),float('inf')]:
                with self.assertRaises(ValueError): b.reserve('gemini',value)

if __name__=='__main__': unittest.main()
