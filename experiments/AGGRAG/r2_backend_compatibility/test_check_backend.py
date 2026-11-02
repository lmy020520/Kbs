"""UNIT_ONLY harness tests; no backend initialization and no model calls."""
import unittest,sys,tempfile,subprocess,json,ast,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent;CODE=ROOT.parent/'tanq_p0b_baseline_r2'
spec=importlib.util.spec_from_file_location('compat_check',ROOT/'check_backend.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Checks(unittest.TestCase):
 def test_original_schema_hash_unchanged(self):
  import hashlib
  self.assertEqual(hashlib.sha256(m.schema_text(m.original_schema(CODE)).encode()).hexdigest(),m.SCHEMA_SHA)
 def test_full_constraint_inventory(self):
  s=m.original_schema(CODE);self.assertEqual(set(s['properties']),{'query','question_units','relations','unresolved'});self.assertIn('minItems',s['properties']['question_units']);self.assertEqual(s['properties']['relations']['items']['properties']['subject_role']['enum'],['answer_entity'])
 def test_missing_log_stops_without_worker(self):
  with tempfile.TemporaryDirectory() as d:
   r=subprocess.run([sys.executable,str(ROOT/'check_backend.py'),'--code',str(CODE),'--out',d,'--original-log',str(Path(d)/'absent'),'--model','NO_MODEL'],capture_output=True,text=True,timeout=10)
   self.assertEqual(r.returncode,0,r.stderr);record=json.loads((Path(d)/'attempt_01/RESULT.json').read_text());self.assertEqual(record['status'],'INSUFFICIENT_EVIDENCE');self.assertFalse(record['attempt_started']);self.assertFalse((Path(d)/'attempt_01/COMPATIBILITY.log').exists())
 def test_attempt_three_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   r=subprocess.run([sys.executable,str(ROOT/'check_backend.py'),'--code',str(CODE),'--out',d,'--original-log','NONE','--model','NONE','--attempt','3'],capture_output=True,text=True,timeout=10)
   self.assertNotEqual(r.returncode,0);self.assertFalse((Path(d)/'attempt_03').exists())
 def test_no_inference_or_model_loader_calls(self):
  tree=ast.parse((ROOT/'check_backend.py').read_text())
  self.assertFalse(any(isinstance(n,ast.Call) and getattr(n.func,'id',getattr(n.func,'attr','')) in {'LLM','generate','chat','AutoModelForCausalLM'} for n in ast.walk(tree)))
 def test_explicit_timeout_and_no_retry(self):
  src=(ROOT/'check_backend.py').read_text();self.assertIn('p.wait(timeout=120)',src);self.assertIn('CUDA_VISIBLE_DEVICES',src);self.assertNotIn('while ',src)
if __name__=='__main__':unittest.main(verbosity=2)
