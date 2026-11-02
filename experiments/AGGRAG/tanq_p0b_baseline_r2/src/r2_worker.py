"""Future R2 GPU worker: requires fresh external approval; never reads Gold."""
import argparse,sys,time,traceback
from pathlib import Path
from io_utils import *
from pipeline import *
from query import compile_plan
from schemas import plan_schema,table_schema,facts_schema,compile_regex

def work(a):
    auth=authorization(a.approval_file)
    if auth['status']!='AUTHORIZED':raise RuntimeError('GPU_NOT_AUTHORIZED')
    packs=verify_inputs(a.data_dir);run=Path(a.out);cfg=load(ROOT/'config/r2_config.json');prompts=load(ROOT/'config/prompts_r2.json')
    def phase(name,**kwargs):write(run/'WORKER_STATE.json',{'phase':name,'at_monotonic':time.monotonic(),**kwargs})
    phase('LOADING_MODEL')
    from r2_model import Backend
    model=Backend(a.model_dir,packs,prompts);write(run/'MODEL_ENVIRONMENT.json',model.environment)
    ledger={'version':cfg['version'],'approval_sha256':auth['sha256'],'calls':[]};write(run/'CALL_LEDGER.json',ledger)
    def call(pack,stage,prompt,schema):
        cap=cfg['max_new_tokens'][stage]
        schema_start=time.monotonic();compile_regex(schema);schema_seconds=time.monotonic()-schema_start
        if model.count(prompt)+cap+128>32768:raise RuntimeError('CONTEXT_OVERFLOW_NO_TRUNCATION')
        if len(ledger['calls'])>=9:raise RuntimeError('R2_CALL_BUDGET_EXHAUSTED')
        i=len(ledger['calls']);record={'index':i,'sample_id':pack['sample_id'],'stage':stage,'status':'RESERVED','reserved_at':time.time()};ledger['calls'].append(record);write(run/'CALL_LEDGER.json',ledger)
        raw={'call_index':i,'sample_id':pack['sample_id'],'stage':stage,'prompt':prompt,'status':'STARTED','model':cfg['model'],'revision':cfg['revision'],'seed':42,'decode':'greedy temperature0 top_p1 top_k-1 repetition_penalty1','max_new_tokens':cap,'json_schema':schema,'decoding_backend':'outlines:no-fallback','schema_preflight_seconds':schema_seconds}
        write(run/f'calls/{i:02d}.json',raw);phase('GENERATING',call_index=i,stage=stage)
        response,usage=model.generate(prompt,cap,schema);raw.update(status='RETURNED',response=response,usage=usage);write(run/f'calls/{i:02d}.json',raw);record.update(status='RETURNED',usage=usage);write(run/'CALL_LEDGER.json',ledger);phase('POSTPROCESSING')
        if usage['finish_reason']=='length':raise RuntimeError('OUTPUT_TRUNCATED_NO_RETRY')
        return response
    for pack in packs:
        sid=pack['sample_id'];raw=call(pack,'plan',make_prompt(prompts,'plan',pack),plan_schema());result=shared_plan(pack['question'],raw)
        if result.get('execution_allowed'):
            result['plan']=result['query']
            result['compiled']=compile_plan(result['plan'])
            combined=dump({'query_plan':result['plan'],'required_columns':columns_for(result['plan'])})
            if len(model.tokenizer.encode(combined,add_special_tokens=False))>1024:result['status']='PLAN_INVALID';result['reason']='PLAN_PAYLOAD_TOKEN_RESERVE_EXCEEDED'
        write(run/f'plans/{sid}.json',result)
        if not result.get('execution_allowed') or result['status']=='PLAN_INVALID':
            for arm in ('B0-R2','B1-Batch-R2'):write(run/f'predictions/{sid}_{arm}.json',{'sample_id':sid,'arm':arm,'status':'SKIPPED_UNVERIFIED_PLAN_TRACE','join_completed':False,'prediction':None})
            continue
        plan=result['plan']
        direct=direct_table(call(pack,'B0-R2',make_prompt(prompts,'B0-R2',pack,plan),table_schema(plan)),plan)
        write(run/f'predictions/{sid}_B0-R2.json',{'sample_id':sid,'arm':'B0-R2',**direct})
        structured=batch_table(call(pack,'B1-Batch-R2',make_prompt(prompts,'B1-Batch-R2',pack,plan),facts_schema(plan,pack['evidence_units'])),plan,pack['evidence_units'])
        write(run/f'predictions/{sid}_B1-Batch-R2.json',{'sample_id':sid,'arm':'B1-Batch-R2',**structured})
    phase('COMPLETED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--approval-file',required=True);p.add_argument('--data-dir',required=True);p.add_argument('--model-dir',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:work(a)
    except BaseException as e:write(Path(a.out)/'WORKER_FAILURE.json',{'error':str(e),'type':type(e).__name__,'traceback':traceback.format_exc()});sys.exit(2)
