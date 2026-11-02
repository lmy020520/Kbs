"""R1 pipeline over an injected generation callback; tests use UNIT_ONLY fixtures."""
import json
from contracts import parse_json,validate_plan,validate_table,render_table,columns_for
from extraction import validate_extraction
from query import execute_plan

def shared_plan(question,raw):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'PLAN_INVALID','raw_response':raw,'validation':parsed}
    validated=validate_plan(parsed['value'])
    return {'status':validated['status'],'plan':parsed['value'],'validation':validated,'raw_response':raw,'information_boundary':'QUESTION_ONLY'}

def direct_table(raw,plan):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'TABLE_INVALID','raw_response':raw,'validation':parsed,'prediction':''}
    rendered=render_table(parsed['value'],plan)
    if rendered['status']!='RENDERED':return {'status':'TABLE_INVALID','raw_response':raw,'validation':rendered,'prediction':''}
    return {'status':'TABLE_VALID','table':parsed['value'],'prediction':rendered['text'],'validation':rendered['validation'],'raw_response':raw}

def batch_table(raw,plan,units):
    parsed=parse_json(raw)
    if parsed['status']!='JSON_VALID':return {'status':'EXTRACTION_INVALID','validation':parsed,'raw_response':raw,'join_completed':False,'prediction':''}
    validated=validate_extraction(parsed['value'],plan,units)
    if validated['status'] not in ('EXTRACTION_VALID','EXTRACTION_PARTIAL'):return {'status':validated['status'],'validation':validated,'raw_response':raw,'join_completed':False,'prediction':''}
    joined=execute_plan(validated['accepted'],plan)
    return {**joined,'extraction_validation':validated,'raw_response':raw,'extraction_complete':validated['rejected_count']==0}

def dump(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))

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
    if stage not in ('B0-R1','B1-Batch-R1'):raise ValueError('Unknown R1 stage')
    payload={'question':pack['question'],'query_plan':plan,'required_columns':columns_for(plan),'evidence_units':pack['evidence_units']}
    return prompts['direct' if stage=='B0-R1' else 'batch']+'\nVISIBLE_INPUT:\n'+dump(payload)
