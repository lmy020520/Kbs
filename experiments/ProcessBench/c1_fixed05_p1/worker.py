"""One full-trajectory forward each; no reference-file access. User-server GPU only."""
import argparse,time,traceback,sys,os,inspect,math
from pathlib import Path
from contract import *
from preflight import check
ROOT=Path(__file__).resolve().parent

def main(a):
 out=Path(a.out);src,exp=verify_inputs(a.data,ROOT);auth=load(ROOT/'config/authorization.json');ledger=Ledger(out/'FORWARD_LEDGER.jsonl');pred=[];actual_hooks=0;fatal=None;stage='CPU_PREFLIGHT';model=None;torch=None;start=time.monotonic()
 save(out/'WORKER_STATE.json',{'stage':stage,'reference_opened':False,'utc':utc()})
 try:
  receipt=check(Path(a.data),Path(a.model));save(out/'RUNTIME_INPUT_AND_MODEL_SHA.json',receipt)
  import torch as torch_module
  torch=torch_module
  if torch.cuda.device_count()!=1:raise ResourceError('Exactly one explicitly selected GPU required; no automatic2/8-card switch')
  from transformers import AutoModel
  torch.manual_seed(42);torch.cuda.reset_peak_memory_stats(0);stage='MODEL_LOAD';save(out/'WORKER_STATE.json',{'stage':stage,'reference_opened':False,'utc':utc()})
  # Fixed public custom model code was SHA verified by check() before this execution.
  model=AutoModel.from_pretrained(a.model,local_files_only=True,trust_remote_code=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=False).eval()
  loaded=Path(inspect.getfile(type(model)));wanted=next(x for x in load(ROOT/'config/model_manifest.json')['files'] if x['filename']=='modeling_qwen2_rm.py')
  if sha(loaded)!=wanted['sha256']:raise ContractError('LOADED_CUSTOM_MODEL_CODE_SHA_MISMATCH')
  if getattr(model,'num_labels',None)!=2:raise ContractError('Unexpected model head')
  model=model.to('cuda:0');model.requires_grad_(False)
  save(out/'MODEL_ENVIRONMENT.json',{'model':'Qwen/Qwen2.5-Math-PRM-7B','revision':'0610740060112df12585d00a1c5f4624d2f59051','versions':receipt['versions'],'python':sys.version,'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'torch_cuda':torch.version.cuda,'GPU_name':torch.cuda.get_device_name(0),'dtype':str(next(model.parameters()).dtype),'attention_implementation':getattr(model.config,'_attn_implementation',None),'use_cache':False,'loader':'Official fixed local AutoModel custom code; CPU load then explicit one-GPU transfer, no accelerate/offload/quantization','loaded_custom_code_sha256':sha(loaded),'loaded_custom_code_path':str(loaded),'threshold':.5,'threshold_origin':'PROJECT_PREREGISTRATION','batch_size':1,'extra_model_warmup':False,'GPU_memory_total':torch.cuda.get_device_properties(0).total_memory})
  def count_forward(module,args,kwargs):
   nonlocal actual_hooks
   actual_hooks+=1
   if actual_hooks>len(ledger.ids) or actual_hooks>20:raise ContractError('UNRESERVED_OR_EXTRA_MODEL_FORWARD')
  model.register_forward_pre_hook(count_forward,with_kwargs=True)
  for s,e in zip(src,exp):
   stage='FORWARD';current=s['id'];save(out/'WORKER_STATE.json',{'stage':stage,'current_id':current,'reserved_before':len(ledger.ids),'reference_opened':False,'utc':utc()})
   ids=e['input_token_ids'];positions=[x['scoring_marker_token_index'] for x in e['steps']]
   # All input IDs/step mapping already proved equal to actual AutoTokenizer before model load.
   inputs=torch.tensor([ids],dtype=torch.long,device='cuda:0');ledger.reserve(current,len(s['steps']));torch.cuda.synchronize();t=time.perf_counter()
   with torch.inference_mode():
    result=model(input_ids=inputs,use_cache=False,return_dict=True)
    if tuple(result.logits.shape)!=(1,len(ids),2):raise ContractError('Unexpected logits shape')
    # Keep author model-card softmax dtype; do not pre-round or replace with FP32-derived decisions.
    probabilities=torch.nn.functional.softmax(result.logits,dim=-1)
    marker_logits=result.logits[0,positions,:].detach().cpu().tolist();pairs=probabilities[0,positions,:].detach().cpu().tolist();scores=[x[1] for x in pairs]
   torch.cuda.synchronize();elapsed=time.perf_counter()-t
   bad=any(not math.isfinite(v) for row in marker_logits+pairs for v in row)
   if bad:
    save(out/'INVALID_SCORE_RAW.json',{'id':current,'logits_repr':repr(marker_logits),'probabilities_repr':repr(pairs),'status':'INVALID_NONFINITE_SCORE'})
    raise ContractError('Nonfinite logits/probabilities')
   validate_scores(scores,len(s['steps']));prediction=predict_first_error(scores)
   record={'id':current,'subset':s['subset'],'problem':s['problem'],'steps':s['steps'],'prompt':e['prompt'],'actual_input_token_ids':ids,'actual_input_tokens':len(ids),'scoring_token_id':151651,'scoring_token_positions':positions,'per_step_cpu_mapping':e['steps'],'raw_class_logits':marker_logits,'raw_class_probabilities':pairs,'step_scores':scores,'logits_dtype':str(result.logits.dtype),'probability_dtype':str(probabilities.dtype),'pred_first_error_fixed_05':prediction,'threshold':.5,'threshold_origin':'PROJECT_PREREGISTRATION','status':'SUCCESS','formal_forward_calls':1,'seconds_with_GPU_synchronization':elapsed,'GPU_max_allocated_bytes_cumulative':torch.cuda.max_memory_allocated(0),'GPU_max_reserved_bytes_cumulative':torch.cuda.max_memory_reserved(0)}
   append(out/'RAW_TRAJECTORY_SCORES_PRIVATE.jsonl',record);pred.append({'id':current,'subset':s['subset'],'status':'SUCCESS','step_scores':scores,'pred_first_error_fixed_05':prediction,'seconds':elapsed,'input_tokens':len(ids)});save(out/'PREDICTIONS_PRIVATE.json',pred)
   del inputs,result,probabilities
 except Exception as ex:
  traceback.print_exc();fatal={'stage':stage,'id':locals().get('current'),'error_type':type(ex).__name__,'error':str(ex),'automatic_retry':False,'actual_root_forward_attempts':actual_hooks};save(out/'WORKER_FAILURE.json',fatal)
 finally:
  done={x['id'] for x in pred}
  for s in src:
   if s['id'] not in done:pred.append({'id':s['id'],'subset':s['subset'],'status':'FAILED' if fatal and fatal.get('id')==s['id'] else 'NOT_RUN','step_scores':None,'pred_first_error_fixed_05':None,'reason':fatal})
  by={p['id']:p for p in pred};save(out/'PREDICTIONS_PRIVATE.json',[by[x['id']] for x in src]);save(out/'WORKER_SUMMARY.json',{'successful':len(done),'fixed_denominator':20,'returned_step_scores':sum(len(x['step_scores']) for x in pred if x['status']=='SUCCESS'),'actual_root_forward_attempts':actual_hooks,'reserved_trajectories':len(ledger.ids),'reserved_steps':ledger.steps,'wall_seconds':time.monotonic()-start,'reference_opened':False,'fatal':fatal,'paid_API_CNY':0,'new_generation_calls':0})
  if torch is not None and torch.cuda.is_initialized():save(out/'GPU_PROCESS_MEMORY.json',{'max_allocated_bytes':torch.cuda.max_memory_allocated(0),'max_reserved_bytes':torch.cuda.max_memory_reserved(0),'scope':'current torch process; includes model transfer and scoring; allocator values not total device memory'})
 return 0 if fatal is None else 2

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.exit(main(a))
