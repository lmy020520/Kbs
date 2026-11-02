import unittest,json,sys,copy,sqlite3,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from contracts import *
from binding import bind_quote
from extraction import validate_extraction
from query import compile_plan,execute_plan
from pipeline import shared_plan,direct_table,batch_table,make_prompt
class R2Tests(unittest.TestCase):
 def setUp(self):
  self.world=json.loads((ROOT/'fixtures/unit_world.json').read_text());self.plan=copy.deepcopy(self.world['plan']);self.units=copy.deepcopy(self.world['units']);self.facts=copy.deepcopy(self.world['facts'])
 def accepted(self,facts=None):return validate_extraction({'facts':self.facts if facts is None else facts},self.plan,self.units)['accepted']
 def test_plan_valid(self):self.assertEqual(validate_plan(self.plan)['status'],'PLAN_VALID_STRUCTURAL')
 def test_plan_root_types_total(self):
  for x in (None,[],[{}],'text',5,True):self.assertEqual(validate_plan(x)['status'],'PLAN_INVALID')
 def test_batch_list_rejected_without_coercion(self):self.assertEqual(validate_extraction(self.facts,self.plan,self.units)['status'],'EXTRACTION_INVALID')
 def test_batch_scalar_types(self):
  for x in (None,3,'facts',True):self.assertEqual(validate_extraction(x,self.plan,self.units)['status'],'EXTRACTION_INVALID')
 def test_strict_json_no_fence_repair(self):self.assertEqual(parse_json('```json\n{}\n```')['status'],'JSON_INVALID')
 def test_duplicate_json_keys_rejected(self):self.assertEqual(parse_json('{"facts":[],"facts":[]}')['status'],'JSON_INVALID')
 def test_nonfinite_json_rejected(self):self.assertEqual(parse_json('{"x":NaN}')['status'],'JSON_INVALID')
 def test_missing_quote_preserved(self):
  f=self.facts[0];del f['quote'];r=validate_extraction({'facts':[f]},self.plan,self.units);self.assertEqual(r['checks'][0]['raw'],f);self.assertIn('MISSING_QUOTE',r['checks'][0]['errors'])
 def test_dict_id_does_not_crash(self):
  f=self.facts[0];f['evidence_id']={};r=validate_extraction({'facts':[f]},self.plan,self.units);self.assertFalse(r['accepted']);self.assertEqual(r['checks'][0]['binding']['status'],'INVALID_EVIDENCE_ID')
 def test_unknown_id(self):self.assertEqual(bind_quote('NO_ID','Device A is red.',self.units)['status'],'INVALID_EVIDENCE_ID')
 def test_exact_binding(self):self.assertEqual(bind_quote('UNIT-A','Device A is red.',self.units)['status'],'EXACT_SOURCE_MATCH')
 def test_same_page_other_chunk(self):self.assertEqual(bind_quote('UNIT-A-OTHER','Device A is red.',self.units)['status'],'SAME_PAGE_OTHER_CHUNK')
 def test_cross_page(self):
  r=bind_quote('UNIT-B','Device A is red.',self.units);self.assertEqual(r['status'],'DIFFERENT_PAGE_MATCH');self.assertFalse(r['strict_accepted']);self.assertFalse(r['automatically_rebound'])
 def test_quote_missing(self):self.assertEqual(bind_quote('UNIT-A',None,self.units)['status'],'MISSING_QUOTE')
 def test_quote_not_found(self):self.assertEqual(bind_quote('UNIT-A','not provided',self.units)['status'],'QUOTE_NOT_FOUND')
 def test_quote_ambiguous_other_sources(self):
  self.units.append({'evidence_id':'UNIT-C','source':{'found_in_url':'https://unit.invalid/wiki/C','proof_text':'Device A is red.'}})
  self.assertEqual(bind_quote('UNIT-B','Device A is red.',self.units)['status'],'AMBIGUOUS_SOURCE')
 def test_declared_match_resolves_duplicate_text(self):
  self.units.append({'evidence_id':'UNIT-C','source':{'proof_text':'Device A is red.'}})
  self.assertEqual(bind_quote('UNIT-A','Device A is red.',self.units)['status'],'EXACT_SOURCE_MATCH')
 def test_quote_is_case_sensitive(self):self.assertEqual(bind_quote('UNIT-A','device a is red.',self.units)['status'],'QUOTE_NOT_FOUND')
 def test_and_requires_all_conditions(self):
  r=execute_plan(self.accepted(),self.plan);self.assertEqual(r['status'],'JOIN_COMPLETED');self.assertEqual(r['table']['rows'],[['Device A','red','4']])
 def test_and_same_attribute_distinct_rows(self):
  self.plan['filter']={'op':'and','conditions':[{'predicate':'class','operator':'eq','value':'lab'},{'predicate':'class','operator':'eq','value':'field'}]}
  self.assertEqual(execute_plan(self.accepted(),self.plan)['table']['rows'],[])
  f={**self.facts[0],'value':'field','raw_index':9};facts=self.accepted()+[f]
  self.assertEqual(len(execute_plan(facts,self.plan)['table']['rows']),1)
 def test_or_allows_either(self):
  self.plan['filter']={'op':'or','conditions':[{'predicate':'color','operator':'eq','value':'red'},{'predicate':'color','operator':'eq','value':'blue'}]}
  self.assertEqual(len(execute_plan(self.accepted(),self.plan)['table']['rows']),2)
 def test_filters_not_joined_across_subjects(self):
  fs=[f for f in self.facts if f['predicate']!='owner'];f={**self.facts[1],'subject':'Device B'};fs.append(f)
  self.assertEqual(execute_plan(self.accepted(fs),self.plan)['table']['rows'],[])
 def test_wrong_subject_role_rejected(self):
  self.facts[0]['entity_type']='person';r=validate_extraction({'facts':self.facts},self.plan,self.units);self.assertIn('WRONG_SUBJECT_ROLE',r['checks'][0]['errors'])
 def test_storage_column_predicate_rejected(self):
  self.plan['predicates'][0]['name']='subject_key';self.assertEqual(validate_plan(self.plan)['status'],'PLAN_INVALID')
 def test_raw_sql_rejected_not_repaired(self):
  self.plan['sql']='SELECT * FROM relation_facts';self.assertEqual(compile_plan(self.plan)['status'],'PLAN_INVALID')
 def test_undeclared_filter_rejected(self):
  self.plan['filter']['conditions'][0]['predicate']='unknown';self.assertEqual(compile_plan(self.plan)['status'],'PLAN_INVALID')
 def test_unsupported_operator_rejected(self):
  self.plan['filter']['conditions'][0]['operator']='DROP TABLE';self.assertEqual(compile_plan(self.plan)['status'],'PLAN_INVALID')
 def test_parameterization_keeps_literals_out_of_sql(self):
  injection="x' OR 1=1 --";self.plan['filter']['conditions'][0]['value']=injection;r=compile_plan(self.plan);self.assertNotIn(injection,r['sql']);self.assertIn(norm(injection),r['parameters']);self.assertEqual(execute_plan(self.accepted(),self.plan)['table']['rows'],[])
 def test_program_only_actual_relation(self):
  c=compile_plan(self.plan);self.assertIn('FROM facts',c['sql']);self.assertNotIn('relation_facts',c['sql'])
 def test_empty_candidates_valid_empty_table(self):
  r=execute_plan([],self.plan);self.assertTrue(r['join_completed']);self.assertEqual(r['table']['rows'],[])
 def test_no_conditions_supported(self):
  self.plan['filter']={'op':'and','conditions':[]};self.assertEqual(len(execute_plan(self.accepted(),self.plan)['table']['rows']),2)
 def test_empty_or_invalid(self):
  self.plan['filter']={'op':'or','conditions':[]};self.assertEqual(validate_plan(self.plan)['status'],'PLAN_INVALID')
 def test_numeric_filter_and_missing_value(self):
  self.plan['filter']={'predicate':'mass','operator':'le','value':4};r=execute_plan(self.accepted(),self.plan);self.assertEqual(len(r['table']['rows']),1)
 def test_numeric_strings_not_coerced(self):
  self.facts[3]['value']='4 kg';r=validate_extraction({'facts':self.facts},self.plan,self.units);self.assertIn('VALUE_TYPE_INVALID_NO_COERCION',r['checks'][3]['errors'])
 def test_bool_and_huge_number_rejected(self):
  for v in (True,float('nan'),float('inf'),10**1000):
   self.plan['filter']={'predicate':'mass','operator':'le','value':v};self.assertEqual(validate_plan(self.plan)['status'],'PLAN_INVALID')
 def test_entity_surface_aliases_normalized(self):self.assertEqual(norm(' ＤＥＶＩＣＥ_A '),norm('device a'))
 def test_unverified_semantic_alias_not_invented(self):self.assertNotEqual(norm('NYC'),norm('New York City'))
 def test_duplicate_table_entities_invalid(self):
  t={'columns':['entity','color','mass'],'rows':[['Device A','red',4],['DEVICE_A','red',4]]};self.assertEqual(validate_table(t,self.plan)['status'],'TABLE_INVALID')
 def test_ragged_table_invalid(self):self.assertEqual(validate_table({'columns':['entity','color','mass'],'rows':[['A','red']]},self.plan)['status'],'TABLE_INVALID')
 def test_long_table_invalid(self):
  r=validate_table({'columns':['entity','attribute','value'],'rows':[['A','color','red']]},self.plan);self.assertEqual(r['status'],'TABLE_INVALID');self.assertIn('LONG_FORM',r['errors'][0]['reason'])
 def test_explicit_null_missing_cell(self):
  t={'columns':['entity','color','mass'],'rows':[['A','red',None]]};r=render_table(t,self.plan);self.assertEqual(r['status'],'RENDERED');self.assertEqual(r['text'],'entity | color | mass\nA | red | ')
 def test_table_cell_delimiter_rejected(self):self.assertEqual(validate_table({'columns':['entity','color','mass'],'rows':[['A','red | blue',3]]},self.plan)['status'],'TABLE_INVALID')
 def test_generic_columns_not_substituted(self):self.assertEqual(validate_table({'columns':['entity','attribute'],'rows':[['A','red']]},self.plan)['status'],'TABLE_INVALID')
 def test_invalid_plan_not_used_for_table(self):self.assertEqual(validate_table({},None)['status'],'PLAN_INVALID')
 def test_single_value_conflict_explicit(self):
  fs=self.accepted();fs.append({**fs[2],'value':'green','raw_index':10});r=execute_plan(fs,self.plan);self.assertEqual(r['status'],'JOIN_PARTIAL');self.assertEqual(len(r['conflicts']),1);self.assertEqual(r['table']['rows'],[])
 def test_all_rejections_retained(self):
  fs=[None,[],{},{'subject':'A'}];r=validate_extraction({'facts':fs},self.plan,self.units);self.assertEqual([c['raw'] for c in r['checks']],fs)
 def test_pipeline_works_on_fixture_only(self):
  raw=json.dumps({'facts':self.facts});r=batch_table(raw,self.plan,self.units);self.assertEqual(r['status'],'JOIN_COMPLETED');self.assertTrue(r['extraction_complete'])
 def test_zero_implicit_schema_conversion(self):self.assertEqual(batch_table(json.dumps(self.facts),self.plan,self.units)['status'],'EXTRACTION_INVALID')
 def test_direct_same_required_columns(self):
  result=direct_table(json.dumps({'columns':['entity','color','mass'],'rows':[]}),self.plan);self.assertEqual(result['status'],'TABLE_VALID')
 def test_owning_entity_attributes_remain_attached(self):
  self.plan['filter']={'op':'and','conditions':[]};r=execute_plan(self.accepted(),self.plan);b=next(row for row in r['table']['rows'] if row[0]=='Device B');self.assertEqual(b,['Device B','blue',None])
class IsolationTests(unittest.TestCase):
 def test_gpu_budget_not_inherited(self):
  from io_utils import authorization
  self.assertEqual(authorization(None)['status'],'GPU_NOT_AUTHORIZED')
 def test_raw_sql_and_table_columns_not_model_fields(self):
  p=json.loads((ROOT/'fixtures/unit_world.json').read_text())['plan'];p['table']='relation_facts'
  self.assertEqual(validate_plan(p)['status'],'PLAN_INVALID')
 def test_plan_prompt_is_question_only(self):
  w=json.loads((ROOT/'fixtures/unit_world.json').read_text());prompts=json.loads((ROOT/'config/prompts_r2.json').read_text());pack={'sample_id':'UNIT','question':w['question'],'evidence_units':w['units']}
  prompt=make_prompt(prompts,'plan',pack)
  self.assertNotIn('Device A is red.',prompt)
 def test_both_arms_same_visible_evidence_and_plan(self):
  w=json.loads((ROOT/'fixtures/unit_world.json').read_text());prompts=json.loads((ROOT/'config/prompts_r2.json').read_text());pack={'sample_id':'UNIT','question':w['question'],'evidence_units':w['units']}
  a=json.loads(make_prompt(prompts,'B0-R2',pack,w['plan']).split('VISIBLE_INPUT:\n')[1]);b=json.loads(make_prompt(prompts,'B1-Batch-R2',pack,w['plan']).split('VISIBLE_INPUT:\n')[1]);self.assertEqual(a,b)
 def test_gold_metadata_blocked(self):
  w=json.loads((ROOT/'fixtures/unit_world.json').read_text());prompts=json.loads((ROOT/'config/prompts_r2.json').read_text());w['units'][0]['source']['filter_pass']=True;pack={'sample_id':'UNIT','question':w['question'],'evidence_units':w['units']}
  with self.assertRaises(ValueError):make_prompt(prompts,'plan',pack)
 def test_not_hardcoded_to_consumed_cases(self):
  for p in (ROOT/'src').glob('*.py'):
   s=p.read_text()
   for case in ('469__','800__','595__'):self.assertNotIn(case,s)
 def test_columns_must_derive_from_plan_not_reference(self):
  w=json.loads((ROOT/'fixtures/unit_world.json').read_text());p=w['plan'];p['outputs'][0]['column']='unrelated column'
  self.assertEqual(validate_plan(p)['status'],'PLAN_INVALID')
class EntryPointTests(unittest.TestCase):
 def test_gpu_entry_without_new_approval_stops_cleanly(self):
  import subprocess,os
  r=subprocess.run([sys.executable,str(ROOT/'scripts/run_server_r2.py')],capture_output=True,text=True,timeout=10,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':''})
  self.assertEqual(r.returncode,2,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'GPU_NOT_AUTHORIZED')
 def test_false_template_cannot_authorize_gpu(self):
  from io_utils import authorization
  self.assertEqual(authorization(ROOT/'config/approval_template.json')['status'],'GPU_NOT_AUTHORIZED')
class ReportingTests(unittest.TestCase):
 def test_failed_or_empty_run_reports_no_fake_metrics(self):
  import tempfile
  from reporting import report
  with tempfile.TemporaryDirectory() as d:
   report(d);r=json.loads((Path(d)/'RUN_SUMMARY.json').read_text());self.assertEqual(r['returned_calls'],0);self.assertIsNone(r['engineering']['semantic_support_rate']);self.assertEqual(r['official_RMS']['status'],'NOT_SCORED')
if __name__=='__main__':unittest.main(verbosity=2)
