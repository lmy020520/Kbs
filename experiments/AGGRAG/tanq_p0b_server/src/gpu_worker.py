"""Private prediction worker. It never opens evaluation/reference files."""
import argparse,sys,os,time,traceback
from pathlib import Path
from common import *
from baselines import dump,table,verified_facts,readonly_join
from quote_locations import locate

def run(a):
 cfg=load(ROOT/'config/server_config.json');run=Path(a.run_dir)
 def phase(name,**more):write(run/'WORKER_STATE.json',{'phase':name,'at_monotonic':time.monotonic(),**more})
 phase('PREFLIGHT')
 from preflight import check
 environment,packs,tok=check(a.data_dir,a.model_dir)
 write(run/'MODEL_ENVIRONMENT.json',environment)
 phase('LOADING_MODEL')
 import torch
 from vllm import LLM,SamplingParams
 if torch.cuda.device_count()!=1:raise RuntimeError('SERVER_MODEL_BLOCKED: exactly one visible GPU required')
 name=torch.cuda.get_device_name(0);cap=torch.cuda.get_device_capability(0)
 if '3090' not in name or cap!=(8,6):raise RuntimeError('SERVER_MODEL_BLOCKED: selected device is not authorized RTX3090 SM86')
 llm=LLM(model=a.model_dir,tokenizer=a.model_dir,trust_remote_code=False,dtype=cfg['dtype'],quantization=cfg['quantization'],tensor_parallel_size=1,max_model_len=32768,max_num_seqs=1,gpu_memory_utilization=cfg['gpu_memory_utilization'],enforce_eager=True,enable_prefix_caching=False,enable_chunked_prefill=True,max_num_batched_tokens=2048,seed=42,disable_log_stats=True,generation_config='vllm')
 ec=llm.llm_engine;model_len=ec.model_config.max_model_len
 blocks=ec.cache_config.num_gpu_blocks;block_size=ec.cache_config.block_size;kv_capacity=blocks*block_size
 if model_len!=32768 or kv_capacity<32768:raise RuntimeError('SERVER_MODEL_BLOCKED: engine did not provide native32K capacity')
 environment.update(torch_cuda=torch.version.cuda,GPU_name=name,GPU_capability=cap,max_model_len_effective=model_len,KV_capacity_tokens=kv_capacity,engine='vLLM V0; AWQ; chunked prefill2048; eager; TP1',model_loaded=True,full32768_generated_probe=False,context_note='Engine config and allocated KV capacity validated; no synthetic generation outside nine-call budget')
 write(run/'MODEL_ENVIRONMENT.json',environment)
 write(run/'GPU_LOAD_MEMORY.json',{'torch_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'torch_peak_reserved_bytes':torch.cuda.max_memory_reserved(),'scope':'current process only; supervisor separately samples total device memory'})
 prompts=load(ROOT/'config/prompts.json');batch=load(ROOT/'config/B1_BATCH_PREREGISTRATION.json');budget=CallBudget(run/'CALL_LEDGER.json',9)
 def call(p,stage,prompt,max_new):
  input_ids=tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True)
  if len(input_ids)+max_new>32768:raise RuntimeError('CONTEXT_OVERFLOW: no truncation, no replacement model')
  index=budget.reserve(p['sample_id'],stage)
  record={'call_index':index,'sample_id':p['sample_id'],'stage':stage,'prompt':prompt,'input_tokens':len(input_ids),'model':cfg['model'],'revision':cfg['revision'],'seed':42,'sampling':'greedy temperature=0 top_p=1 top_k=-1 repetition_penalty=1 generation_config=vllm','max_new_tokens':max_new,'status':'STARTED'}
  write(run/f'calls/{index:02d}.json',record)
  torch.cuda.reset_peak_memory_stats();phase('GENERATING',call_index=index,sample_id=p['sample_id'],stage=stage)
  t=time.monotonic();result=llm.generate([{'prompt_token_ids':input_ids}],SamplingParams(temperature=0.0,top_p=1.0,top_k=-1,repetition_penalty=1.0,max_tokens=max_new,seed=42,n=1),use_tqdm=False)[0]
  out=result.outputs[0];usage={'input_tokens':len(result.prompt_token_ids),'output_tokens':len(out.token_ids),'seconds':time.monotonic()-t,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
  if usage['input_tokens']!=len(input_ids):raise RuntimeError('Backend input-token mismatch; possible truncation')
  record.update(status='RETURNED',response=out.text,finish_reason=out.finish_reason,usage=usage);write(run/f'calls/{index:02d}.json',record);budget.finish(index,usage);phase('POSTPROCESSING',call_index=index)
  if out.finish_reason=='length':raise RuntimeError('OUTPUT_TRUNCATED: stop entire run; no continuation/retry')
  return out.text
 for p in packs:
  result={'sample_id':p['sample_id'],'arm':'B0','status':'NOT_RUN'}
  raw=call(p,'B0',prompts['B0']+'\n'+dump({'question':p['question'],'evidence_units':p['evidence_units']}),4096)
  try:
   obj=json.loads(raw);result.update(status='SUCCESS',table=obj,prediction=table(obj))
  except Exception as e:result.update(status='FORMAT_ERROR',error=str(e),prediction='')
  write(run/f"predictions/{p['sample_id']}_B0.json",result)
  result={'sample_id':p['sample_id'],'arm':'B1-Batch','status':'NOT_RUN'}
  raw=call(p,'plan',prompts['B1_plan_question_only']+'\nQuestion: '+p['question'],4096)
  try:
   plan=json.loads(raw)
   if set(plan)!={'predicates','sql'} or not isinstance(plan['predicates'],list) or not all(isinstance(x,str) for x in plan['predicates']) or not isinstance(plan['sql'],str):raise ValueError('Invalid plan schema')
   if len(tok.encode(dump(plan['predicates']),add_special_tokens=False))>1024:raise RuntimeError('Predicate token reserve exceeded; no silent repacking')
  except RuntimeError:
   raise
  except Exception as e:
   result.update(status='PLAN_FORMAT_ERROR',error=str(e),prediction='');write(run/f"predictions/{p['sample_id']}_B1-Batch.json",result);continue
  prompt=batch['prompt']+'\n'+dump({'question':p['question'],'predicates':plan['predicates'],'evidence_units':p['evidence_units']})
  if len(tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))+8192+128>32768:raise RuntimeError('Actual batch prompt exceeds frozen safety budget')
  raw=call(p,'batch',prompt,8192)
  try:
   obj=json.loads(raw)
   if set(obj)!={'facts'} or not isinstance(obj['facts'],list):raise ValueError('Batch extraction schema invalid')
   by_id={u['evidence_id']:u for u in p['evidence_units']};valid=[];rejected=[];quote_checks=[]
   for f in obj['facts']:
    if not isinstance(f,dict) or set(f)!={'subject','predicate','object','quote','evidence_id'} or f.get('evidence_id') not in by_id:rejected.append({'fact':f,'reason':'SCHEMA_OR_UNKNOWN_EVIDENCE_ID'});continue
    clean={k:v for k,v in f.items() if k!='evidence_id'};v,r=verified_facts([clean],by_id[f['evidence_id']]);valid.extend(v);rejected.extend(r)
    locations=locate(by_id[f['evidence_id']],f.get('quote'));quote_checks.append({'evidence_id':f['evidence_id'],'quote':f.get('quote'),'locations':locations,'literal_status':'PASS' if locations else 'FAIL','multiple_matches':len(locations)>1,'semantic_support':'UNVERIFIED'})
   joined=readonly_join(valid,plan['sql']);render=table(joined)
   result.update(status='SUCCESS' if not rejected else 'SUCCESS_WITH_QUOTE_REJECTIONS',table=joined,prediction=render,plan=plan,normalized_facts=valid,quote_rejections=rejected,quote_location_checks=quote_checks,semantic_support='UNVERIFIED')
  except Exception as e:result.update(status='FORMAT_OR_JOIN_ERROR',error=str(e),prediction='',plan=plan)
  write(run/f"predictions/{p['sample_id']}_B1-Batch.json",result)
 phase('COMPLETED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--model-dir',required=True);p.add_argument('--run-dir',required=True);a=p.parse_args()
 try:run(a)
 except BaseException as e:
  write(Path(a.run_dir)/'WORKER_FAILURE.json',{'type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc()});sys.exit(2)
