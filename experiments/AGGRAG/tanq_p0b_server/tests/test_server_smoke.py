"""CPU-only failure-injection fixtures. No fake LLM performance or production predictions."""
import unittest,tempfile,json,sys,subprocess,os,time,ast,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
from baselines import norm,table,readonly_join,verified_facts
from supervision import watch
from reporting import report
class ServerSmokeTests(unittest.TestCase):
 def test_freeze_ids_order(self):
  m=load(ROOT/'config/private_data_manifest.json');s=load(ROOT/'config/smoke_freeze.json')
  self.assertEqual(m['sample_order'],[x['sample_id'] for x in s['samples']]);self.assertEqual(len(m['sample_order']),3)
 def test_prompt_contract_not_regenerated(self):
  a=load(ROOT/'config/B1_BATCH_PREREGISTRATION.json');self.assertEqual(a['max_context_tokens'],32768);self.assertEqual(a['max_new_tokens_per_batch'],8192);self.assertEqual(a['real_model_runs'],0)
 def test_no_data_files_in_code(self):
  self.assertEqual(list(ROOT.rglob('*.safetensors')),[])
  self.assertFalse(any(p.is_file() for p in (ROOT/'private').glob('*')))
 def test_missing_private_data_stops(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,'SERVER_DATA_BLOCKED'):verify_inputs(d)
 def test_changed_source_sha_stops(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'inputs';p.mkdir();(p/'source_only.jsonl').write_text('{}\n')
   with self.assertRaisesRegex(RuntimeError,'SHA mismatch'):verify_inputs(d)
 def test_budget_persists_and_blocks_tenth(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger';b=CallBudget(p)
   for i in range(9):self.assertEqual(b.reserve('UNIT_ONLY',str(i)),i)
   with self.assertRaises(RuntimeError):CallBudget(p).reserve('UNIT_ONLY','10')
 def test_failed_call_consumes_budget(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger';CallBudget(p,1).reserve('UNIT_ONLY','before-error')
   with self.assertRaises(RuntimeError):CallBudget(p,1).reserve('UNIT_ONLY','retry')
 def test_wall_timeout_kills_owned_group(self):
  with tempfile.TemporaryDirectory() as d:
   proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
   r=watch(proc,Path(d)/'missing-state',wall_seconds=.15,generation_seconds=100)
   self.assertEqual(r['stop_reason'],'TOTAL_WALL_TIMEOUT');self.assertIsNotNone(proc.poll())
 def test_single_generation_timeout_kills(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d)/'state';write(state,{'phase':'GENERATING','at_monotonic':time.monotonic()-2})
   proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
   r=watch(proc,state,wall_seconds=10,generation_seconds=1)
   self.assertEqual(r['stop_reason'],'GENERATION_TIMEOUT')
 def test_prediction_freeze_tamper_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'predictions').mkdir();f=p/'predictions/x.json';write(f,{'fixture':'UNIT_ONLY'})
   write(p/'PREDICTIONS_FROZEN.json',{'files':prediction_manifest(p)});verify_prediction_freeze(p);write(f,{'changed':True})
   with self.assertRaises(RuntimeError):verify_prediction_freeze(p)
 def test_predictor_never_reads_gold(self):
  for name in ('gpu_worker.py','preflight.py','baselines.py'):
   source=(ROOT/'src'/name).read_text();self.assertNotIn('reference.jsonl',source);self.assertNotIn('answer_table',source.replace("'answer_table',",'')) if name!='baselines.py' else None
 def test_score_verifies_prediction_before_gold(self):
  s=(ROOT/'scripts/score.py').read_text();self.assertLess(s.index('verify_prediction_freeze(run)'),s.index("refs=rows(gold)"))
 def test_missing_model_clear_block(self):
  from preflight import inspect_model
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,'SERVER_MODEL_BLOCKED'):inspect_model(d)
 def test_json_shape_rejected(self):
  with self.assertRaises(ValueError):table({'columns':['entity','value'],'rows':[['X']]})
 def test_wrong_quote_not_verified(self):
  good,bad=verified_facts([{'subject':'UNIT','predicate':'v','object':'1','quote':'wrong quote'}],{'evidence_id':'UNIT','source':{'proof_text':'right quote'}})
  self.assertEqual(good,[]);self.assertEqual(len(bad),1)
 def test_join_uses_subject_key(self):
  f=[{'subject':'Example A','predicate':'color','object':'red','evidence_id':'UNIT'},{'subject':'Example B','predicate':'mass','object':'1','evidence_id':'UNIT'}]
  self.assertEqual(readonly_join(f,"SELECT a.subject AS entity,b.object AS value FROM facts a JOIN facts b ON a.subject_key=b.subject_key WHERE a.predicate_key='color' AND b.predicate_key='mass'")['rows'],[])
 def test_sql_writes_blocked(self):
  with self.assertRaises(ValueError):readonly_join([],"DELETE FROM facts")
 def test_empty_result_report_does_not_claim_success(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);write(p/'MODEL_ENVIRONMENT.json',{'model_loaded':False});write(p/'DATA_FAILURE.json',{'error':'UNIT_ONLY'})
   self.assertEqual(report(p),'SERVER_DATA_BLOCKED');self.assertEqual(load(p/'RUN_SUMMARY.json')['returned_calls'],0)
 def test_reserved_output_limits(self):
  cfg=load(ROOT/'config/server_config.json');self.assertEqual(cfg['max_calls'],9);self.assertEqual(cfg['wall_seconds'],7200);self.assertEqual(cfg['generation_seconds'],1200);self.assertEqual(cfg['tensor_parallel_size'],1)
class QuoteLocationTests(unittest.TestCase):
 def test_exact_coordinates(self):
  from quote_locations import locate
  r=locate({'source':{'proof_text':'prefix UNIT suffix'}},'UNIT')
  self.assertEqual(r[0]['json_pointer'],'/source/proof_text');self.assertEqual((r[0]['start_char'],r[0]['end_char']),(7,11))
 def test_repeated_quote_preserves_ambiguity(self):
  from quote_locations import locate
  self.assertEqual(len(locate({'source':{'proof_text':'UNIT UNIT'}},'UNIT')),2)
 def test_url_is_not_factual_quote(self):
  from quote_locations import locate
  self.assertEqual(locate({'source':{'found_in_url':'UNIT','proof_text':'other'}},'UNIT'),[])
if __name__=='__main__':unittest.main(verbosity=2)
