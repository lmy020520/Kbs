"""Schema-checked R2 traditional baseline. No repair and no evaluation-reference access."""
import json
from contracts import parse_json,columns_for,render_table
from extraction import validate_extraction
from query import execute_plan
from plan_audit import audit_plan
from schemas import table_schema,facts_schema,validate_schema

def dump(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def shared_plan(question,raw):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'PLAN_INVALID','execution_allowed':False,'validation':parsed,'raw_response':raw}
    audit=audit_plan(question,parsed['value'])
    return {**audit,'envelope':parsed['value'],'raw_response':raw,'information_boundary':'QUESTION_ONLY'}
def direct_table(raw,plan):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'TABLE_INVALID','validation':parsed,'raw_response':raw,'prediction':''}
    errors=validate_schema(parsed['value'],table_schema(plan))
    if errors:return {'status':'TABLE_INVALID','errors':errors,'raw_response':raw,'prediction':''}
    rendered=render_table(parsed['value'],plan)
    if rendered['status']!='RENDERED':return {'status':'TABLE_INVALID','validation':rendered,'raw_response':raw,'prediction':''}
    return {'status':'TABLE_VALID','table':parsed['value'],'prediction':rendered['text'],'validation':rendered['validation'],'raw_response':raw,'semantic_support':'UNVERIFIED'}
def batch_table(raw,plan,units):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'EXTRACTION_INVALID','validation':parsed,'raw_response':raw,'join_completed':False,'prediction':''}
    errors=validate_schema(parsed['value'],facts_schema(plan,units))
    if errors:
        # Retain per-candidate reasons even when the global schema fails. No Join on invalid envelope.
        diagnostic=validate_extraction(parsed['value'],plan,units)
        return {'status':'EXTRACTION_INVALID','schema_errors':errors,'extraction_validation':diagnostic,'raw_response':raw,'join_completed':False,'prediction':''}
    valid=validate_extraction(parsed['value'],plan,units)
    if valid['status'] not in ('EXTRACTION_VALID','EXTRACTION_PARTIAL'):return {**valid,'join_completed':False,'raw_response':raw}
    joined=execute_plan(valid['accepted'],plan)
    return {**joined,'raw_response':raw,'extraction_validation':valid,'candidate_count':valid['candidate_count'],'accepted_count':len(valid['accepted']),'mechanical_acceptance_rate':len(valid['accepted'])/valid['candidate_count'] if valid['candidate_count'] else None,'semantic_support':'UNVERIFIED','semantic_verified_candidates':0,'extraction_complete':valid['rejected_count']==0}
def make_prompt(prompts,stage,pack,plan=None):
    if set(pack)!={'sample_id','question','evidence_units'}:raise ValueError('INPUT_INVALID_FIELDS')
    forbidden={'answer_table','answer_list','filter_pass','extension_entity','init_answer_wikidata_id','extension_wikidata_id','eval_result','pid','extension_property_id','init_answer_wikipedia_id','init_answer_composed','question_properties','extended_types'}
    def check(x):
        if isinstance(x,dict):
            if set(x)&forbidden:raise ValueError('FORBIDDEN_PREDICTION_INPUT_METADATA')
            for v in x.values():check(v)
        elif isinstance(x,list):
            for v in x:check(v)
    check(pack)
    if stage=='plan':return prompts['plan']+'\nQUESTION:\n'+pack['question']
    if stage not in ('B0-R2','B1-Batch-R2'):raise ValueError('Unknown R2 stage')
    return prompts['direct' if stage=='B0-R2' else 'batch']+'\nVISIBLE_INPUT:\n'+dump({'question':pack['question'],'query_plan':plan,'required_columns':columns_for(plan),'evidence_units':pack['evidence_units']})
