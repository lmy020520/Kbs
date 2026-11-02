"""UNIT_ONLY controlled fixtures: tests are not real model outputs or TANQ performance."""
import unittest,sys,json,copy,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from schemas import *
from plan_audit import audit_plan
from pipeline import shared_plan,batch_table,direct_table
from extraction import validate_extraction
class R2(unittest.TestCase):
 def setUp(self):
  self.w=json.loads((ROOT/'fixtures/unit_world.json').read_text());self.p=self.w['plan'];self.u=self.w['units']
  q=self.w['question'];parts=[('Which ','syntax',''),('devices','entity_scope','/entity_type'),(' are ','syntax',''),('lab devices','condition','/filter/conditions/0'),(' and ','logic','/filter'),('owned by Owner-A','condition','/filter/conditions/1'),('? Give ','syntax',''),('color','output','/outputs/0'),(' and ','syntax',''),('mass','output','/outputs/1'),('.','syntax','')]
  start=0;units=[]
  for text,kind,target in parts:
   assert q[start:start+len(text)]==text
   units.append(dict(start=start,end=start+len(text),text=text,kind=kind,target=target));start+=len(text)
  self.e={'query':self.p,'question_units':units,'relations':[{'predicate':p['name'],'subject_role':'answer_entity','object_role':'value'} for p in self.p['predicates']],'unresolved':[]}
 def test_valid_trace_stays_semantically_unverified(self):
  r=audit_plan(self.w['question'],self.e);self.assertEqual(r['status'],'PLAN_UNVERIFIED');self.assertEqual(r['lexical_trace_status'],'PASS');self.assertTrue(r['execution_allowed'])
 def test_missing_explicit_constraint_blocks_execution(self):
  del self.e['question_units'][5];r=audit_plan(self.w['question'],self.e);self.assertFalse(r['execution_allowed']);self.assertEqual(r['status'],'PLAN_UNVERIFIED')
 def test_scope_cannot_hide_owner_condition(self):
  self.e['question_units'][5].update(kind='entity_scope',target='/entity_type');self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_syntax_cannot_hide_condition(self):
  self.e['question_units'][5].update(kind='syntax',target='');self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_and_or_trace_mismatch(self):
  self.p['filter']['op']='or';self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_missing_output_anchor(self):
  self.e['question_units'][7]['target']='/outputs/1';self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_invalid_span_no_repair(self):
  self.e['question_units'][1]['start']+=1;self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_literal_value_not_in_anchor(self):
  self.p['filter']['conditions'][1]['value']='Owner-X';self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_role_catalog_complete(self):
  self.e['relations'].pop();self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_wrong_relation_role(self):
  self.e['relations'][0]['subject_role']='named_writer';self.assertEqual(audit_plan(self.w['question'],self.e)['status'],'PLAN_INVALID')
 def test_explicit_uncertainty_blocks(self):
  self.e['unresolved']=['unclear entity scope'];self.assertFalse(audit_plan(self.w['question'],self.e)['execution_allowed'])
 def test_plan_sql_not_a_schema_field(self):
  self.e['sql']='DROP TABLE facts';self.assertEqual(audit_plan(self.w['question'],self.e)['status'],'PLAN_INVALID')
 def test_root_scalar_array_rejected(self):
  for v in [None,[],2,'x',True]:self.assertEqual(shared_plan(self.w['question'],json.dumps(v))['status'],'PLAN_INVALID')
 def test_all_schemas_compile_with_actual_pinned_cpu_compiler(self):
  for s in [plan_schema(),table_schema(self.p),facts_schema(self.p,self.u)]:self.assertTrue(compile_regex(s));re.compile(compile_regex(s))
 def test_guided_regex_width_and_envelope(self):
  schema=table_schema(self.p);rx=compile_regex(schema);valid={'columns':['entity','color','mass'],'rows':[['A','red',4]]}
  self.assertTrue(re.fullmatch(rx,json.dumps(valid)));self.assertFalse(validate_schema(valid,schema))
  for invalid in [dict(valid,rows=[['A','red']]),dict(valid,rows=[['A','red',4,'x']]),dict(valid,extra='x'),dict(valid,columns=['entity','mass','color']),dict(valid,rows=[{'entity':'A'}]),[valid],dict(valid,rows=[['A',{},4]])]:
   self.assertIsNone(re.fullmatch(rx,json.dumps(invalid)));self.assertTrue(validate_schema(invalid,schema))
 def test_guided_regex_facts_and_types(self):
  schema=facts_schema(self.p,self.u);rx=compile_regex(schema);v={'facts':self.w['facts']};self.assertTrue(re.fullmatch(rx,json.dumps(v)))
  for change in [{'extra':True},{'evidence_id':'NO_ID'},{'predicate':'unknown'},{'value':{}},{'entity_type':'writer'}]:
   invalid=copy.deepcopy(v);invalid['facts'][0].update(change);self.assertIsNone(re.fullmatch(rx,json.dumps(invalid)));self.assertTrue(validate_schema(invalid,schema))
 def test_guided_regex_requires_all_fields(self):
  v={'facts':[copy.deepcopy(self.w['facts'][0])]};del v['facts'][0]['quote'];self.assertIsNone(re.fullmatch(compile_regex(facts_schema(self.p,self.u)),json.dumps(v)))
 def test_schema_valid_does_not_certify_semantic_support(self):
  f=copy.deepcopy(self.w['facts'][0]);f['subject']='Device Z';f['value']='invented';r=validate_extraction({'facts':[f]},self.p,self.u)
  self.assertEqual(len(r['accepted']),1);self.assertEqual(r['checks'][0]['support_assessment']['status'],'SUBJECT_ATTRIBUTE_SUPPORT_UNVERIFIED');self.assertFalse(r['checks'][0]['support_assessment']['subject_literal_in_quote'])
 def test_every_rejected_candidate_retained_even_schema_invalid(self):
  f=copy.deepcopy(self.w['facts']);del f[0]['quote'];r=batch_table(json.dumps({'facts':f}),self.p,self.u)
  self.assertFalse(r['join_completed']);self.assertEqual(len(r['extraction_validation']['checks']),len(f))
 def test_empty_facts_not_fake_safe_success(self):
  r=batch_table('{"facts":[]}',self.p,self.u);self.assertTrue(r['join_completed']);self.assertIsNone(r['mechanical_acceptance_rate']);self.assertEqual(r['table']['rows'],[]);self.assertEqual(r['semantic_support'],'UNVERIFIED')
 def test_fence_still_invalid_no_old_output_repair(self):
  self.assertEqual(batch_table('```json\n{"facts":[]}\n```',self.p,self.u)['status'],'EXTRACTION_INVALID')
 def test_guidance_adapter_fixed_no_fallback(self):
  source=(ROOT/'src/r2_model.py').read_text();self.assertIn('guided_decoding=self.GuidedDecodingParams(json=schema,backend="outlines:no-fallback")',source)
  self.assertNotIn('trust_remote_code=True',source)
 def test_duplicate_evidence_id_does_not_silently_overwrite(self):
  from binding import bind_quote
  units=self.u+[copy.deepcopy(self.u[0])];self.assertEqual(bind_quote('UNIT-A','Device A is red.',units)['status'],'AMBIGUOUS_SOURCE')
 def test_no_gpu_import_during_cpu_tests(self):
  self.assertNotIn('vllm',sys.modules);self.assertNotIn('torch',sys.modules)
if __name__=='__main__':unittest.main(verbosity=2)
