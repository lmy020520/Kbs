"""Synthetic CPU-only fixtures. Not model predictions or benchmark performance."""
import unittest,tempfile,json,hashlib,math,sys,copy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import contract as c
from score_and_report import check_prediction_freeze
from run_supervised import inventory
class ThresholdTests(unittest.TestCase):
 def test_equal_passes(self):self.assertEqual(c.predict_first_error([.5,1,.6]),-1)
 def test_first_index_zero(self):self.assertEqual(c.predict_first_error([0,.9]),0)
 def test_no_rounding(self):self.assertEqual(c.predict_first_error([.50000000001,.49999999999]),1)
 def test_first_not_minimum(self):self.assertEqual(c.predict_first_error([.7,.49,.01]),1)
 def test_all_invalid_values(self):
  for v in [None,True,float('nan'),float('inf'),float('-inf'),-1,1.00001,'abc',{},[]]:
   with self.subTest(v=repr(v)),self.assertRaises(c.ContractError):c.predict_first_error([.7,v])
 def test_later_invalid_not_hidden_by_early_error(self):
  with self.assertRaises(c.ContractError):c.predict_first_error([.1,float('nan')])
 def test_empty(self):
  with self.assertRaises(c.ContractError):c.predict_first_error([])
 def test_missing_score_count(self):
  with self.assertRaises(c.ContractError):c.validate_scores([.5],2)
class SafetyTests(unittest.TestCase):
 def test_duplicate_forward_denied(self):
  with tempfile.TemporaryDirectory() as t:
   l=c.Ledger(Path(t)/'ledger');l.reserve('fixture',3)
   with self.assertRaises(c.ContractError):l.reserve('fixture',3)
   self.assertEqual(len((Path(t)/'ledger').read_text().splitlines()),1)
 def test_max20_forward(self):
  with tempfile.TemporaryDirectory() as t:
   l=c.Ledger(Path(t)/'ledger')
   for i in range(20):l.reserve(str(i),1)
   with self.assertRaises(c.ContractError):l.reserve('extra',1)
 def test_max112_step_scores(self):
  with tempfile.TemporaryDirectory() as t:
   l=c.Ledger(Path(t)/'ledger');l.reserve('fixture',112)
   with self.assertRaises(c.ContractError):l.reserve('extra',1)
 def test_exclusive_authorization(self):
  with tempfile.TemporaryDirectory() as t:
   a=c.AuthorizationLock(Path(t)/'used');a.acquire('fixture')
   with self.assertRaises(FileExistsError):a.acquire('fixture')
 def test_mutated_budget_rejected(self):
  a=c.load(ROOT/'config/authorization.json');c.check_authorization(a)
  for k,v in [('threshold',.49),('max_trajectories',21),('worker_watchdog_seconds',7200),('automatic_retry',True),('planned_GPU_count',8)]:
   z=copy.deepcopy(a);z[k]=v
   with self.subTest(k=k),self.assertRaises(c.ContractError):c.check_authorization(z)
 def test_missing_freeze_before_any_reference_read(self):
  with tempfile.TemporaryDirectory() as t,self.assertRaises(FileNotFoundError):check_prediction_freeze(Path(t))
 def test_modified_prediction_detected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);c.save(p/'SUPERVISION.json',{'worker_has_ended':True});c.save(p/'PREDICTIONS_PRIVATE.json',[])
   c.save(p/'PREDICTION_FREEZE.json',{'worker_has_ended':True,'files':{'PREDICTIONS_PRIVATE.json':c.sha(p/'PREDICTIONS_PRIVATE.json')}})
   check_prediction_freeze(p);c.save(p/'PREDICTIONS_PRIVATE.json',[{'fixture':'tampered'}])
   with self.assertRaises(c.ContractError):check_prediction_freeze(p)
 def test_gpu_inventory_no_auto_switch(self):
  with patch('subprocess.check_output',return_value='0, uuid, NVIDIA GeForce RTX 3090, 24576, 23000, 1000, 550\n'):self.assertEqual(inventory(0)['physical_index'],'0')
  with patch('subprocess.check_output',return_value='0, uuid, NVIDIA GeForce RTX 3090, 24576, 18000, 6000, 550\n'),self.assertRaises(c.ResourceError):inventory(0)
 def test_complete_snapshot_required(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'file').write_bytes(b'fixture');m={'files':[{'filename':'file','bytes':7,'sha256':c.sha(p/'file')}]};self.assertEqual(len(c.verify_model(p,m)),1);(p/'file').write_bytes(b'changed')
   with self.assertRaises(c.ContractError):c.verify_model(p,m)
class MetricTests(unittest.TestCase):
 def test_harmonic_not_binary_f1(self):
  p=[{'id':str(i),'status':'SUCCESS','pred_first_error_fixed_05':v} for i,v in enumerate([0,-1,-1,-1])];r=[{'id':str(i),'published_first_error':v} for i,v in enumerate([0,1,-1,-1])]
  m=c.fixed_metrics(p,r);self.assertAlmostEqual(m['processbench_style_harmonic_F1'],2/3);self.assertEqual(m['first_error_accuracy_full_denominator'],.75)
 def test_failures_remain_denominator(self):
  p=[{'id':'a','status':'NOT_RUN','pred_first_error_fixed_05':None}];r=[{'id':'a','published_first_error':-1}];m=c.fixed_metrics(p,r);self.assertEqual(m['N'],1);self.assertEqual(m['valid'],0);self.assertIsNone(m['processbench_style_harmonic_F1'])
class GoldIsolationTests(unittest.TestCase):
 def fixture(self,base):
  root=base/'code';data=base/'data';(root/'config').mkdir(parents=True);(data/'inputs').mkdir(parents=True);(data/'evaluation').mkdir();src=[];exp=[];cases=[]
  for i in range(20):
   n=6 if i<12 else 5;tokens=500 if i<19 else 728;s={'id':'synthetic-'+str(i),'subset':'fixture','problem':'CPU fixture only','steps':['synthetic step']*n};e={'id':s['id'],'prompt':'fixture','input_token_ids':[1]*tokens};src.append(s);exp.append(e);cases.append({'id':s['id'],'subset':'fixture','steps':n,'visible_record_sha256':c.obj_sha(s),'expected_prompt_sha256':hashlib.sha256(b'fixture').hexdigest(),'expected_input_tokens':tokens})
  c.save(data/'inputs/source_only.json',src);c.save(data/'inputs/expected_cpu.json',exp);c.save(root/'config/sample_freeze.json',{'cases':cases});c.save(root/'config/authorization.json',c.load(ROOT/'config/authorization.json'));c.save(root/'config/data_manifest.json',{'source_only_sha256':c.sha(data/'inputs/source_only.json'),'expected_cpu_sha256':c.sha(data/'inputs/expected_cpu.json'),'reference_sha256_FOR_SCORER_ONLY':'DELIBERATELY_NOT_READ'})
  (data/'evaluation/reference.json').write_text('DO NOT READ BEFORE FREEZE');return root,data
 def test_predictor_does_not_open_reference(self):
  with tempfile.TemporaryDirectory() as t:
   root,data=self.fixture(Path(t));original=Path.open
   def guarded(p,*args,**kwargs):
    if p.name=='reference.json':raise AssertionError('Gold leaked')
    return original(p,*args,**kwargs)
   with patch.object(Path,'open',guarded):src,e=c.verify_inputs(data,root);self.assertEqual(len(src),20)
 def test_gold_field_rejected_even_if_hash_updated(self):
  with tempfile.TemporaryDirectory() as t:
   root,data=self.fixture(Path(t));src=c.load(data/'inputs/source_only.json');src[0]['label']=1;c.save(data/'inputs/source_only.json',src);m=c.load(root/'config/data_manifest.json');m['source_only_sha256']=c.sha(data/'inputs/source_only.json');c.save(root/'config/data_manifest.json',m)
   with self.assertRaises(c.ContractError):c.verify_inputs(data,root)
 def test_order_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root,data=self.fixture(Path(t));src=c.load(data/'inputs/source_only.json');src[0],src[1]=src[1],src[0];c.save(data/'inputs/source_only.json',src);m=c.load(root/'config/data_manifest.json');m['source_only_sha256']=c.sha(data/'inputs/source_only.json');c.save(root/'config/data_manifest.json',m)
   with self.assertRaises(c.ContractError):c.verify_inputs(data,root)
if __name__=='__main__':unittest.main()
