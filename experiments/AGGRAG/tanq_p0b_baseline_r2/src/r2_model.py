"""Fixed optional GPU backend; not imported by offline validators/tests."""
import os,sys,importlib.metadata as metadata
from io_utils import *
def inspect_model(folder):
 folder=Path(folder);receipt=load(folder/'AGGRAG_MODEL_RECEIPT.json');cfg=load(ROOT/'config/r2_config.json')
 if receipt['model']!=cfg['model'] or receipt['revision']!=cfg['revision']:raise RuntimeError('MODEL_INVALID: revision/repository mismatch')
 for name,digest in receipt['files'].items():
  f=folder/name
  if not f.resolve().is_relative_to(folder.resolve()) or not f.is_file() or sha(f)!=digest:raise RuntimeError('MODEL_INVALID: file SHA mismatch')
 config=load(folder/'config.json')
 if config.get('quantization_config',{}).get('quant_method')!='awq' or config.get('max_position_embeddings',0)<32768:raise RuntimeError('MODEL_INVALID: AWQ/native32K required')
 return receipt
class Backend:
 def __init__(self,folder,packs,prompts):
  if sys.version_info[:2]!=(3,11):raise RuntimeError('Use fixed Python3.11 environment')
  cfg=load(ROOT/'config/r2_config.json')
  self.versions={k:metadata.version(k) for k in cfg['runtime_versions']}
  if any(self.versions[k].split('+')[0]!=v for k,v in cfg['runtime_versions'].items()):raise RuntimeError('RUNTIME_VERSION_MISMATCH')
  inspect_model(folder)
  from transformers import AutoTokenizer
  self.tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True,trust_remote_code=False)
  from pipeline import dump,make_prompt
  bounds=[]
  for pack in packs:
   q=make_prompt(prompts,'plan',pack)
   if self.count(q)+2048+128>32768:raise RuntimeError('PLAN_CONTEXT_OVERFLOW')
   payload={'question':pack['question'],'query_plan':None,'required_columns':[],'evidence_units':pack['evidence_units']}
   lengths={}
   for stage,key,cap in [('B0-R2','direct',4096),('B1-Batch-R2','batch',8192)]:
    base=self.count(prompts[key]+'\nVISIBLE_INPUT:\n'+dump(payload));lengths[stage]=base
    if base+1024+cap+128>32768:raise RuntimeError('PREFLIGHT_CONTEXT_OVERFLOW_NO_TRUNCATION')
   bounds.append({'sample_id':pack['sample_id'],'base_prompt_tokens':lengths,'plan_payload_reserve':1024})
  import torch
  from vllm import LLM,SamplingParams
  from vllm.sampling_params import GuidedDecodingParams
  self.GuidedDecodingParams=GuidedDecodingParams
  if torch.cuda.device_count()!=1 or '3090' not in torch.cuda.get_device_name(0):raise RuntimeError('One authorized RTX3090 required')
  self.torch=torch;self.SamplingParams=SamplingParams
  self.engine=LLM(model=folder,tokenizer=folder,trust_remote_code=False,dtype='half',quantization='awq',tensor_parallel_size=1,max_model_len=32768,max_num_seqs=1,gpu_memory_utilization=.85,enforce_eager=True,enable_prefix_caching=False,enable_chunked_prefill=True,max_num_batched_tokens=2048,seed=42,disable_log_stats=True,generation_config='vllm')
  ec=self.engine.llm_engine
  self.environment={'model':cfg['model'],'revision':cfg['revision'],'versions':self.versions,'torch_cuda':torch.version.cuda,'load_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'load_peak_reserved_bytes':torch.cuda.max_memory_reserved(),'max_model_len':ec.model_config.max_model_len,'KV_capacity_tokens':ec.cache_config.num_gpu_blocks*ec.cache_config.block_size,'GPU':torch.cuda.get_device_name(0),'CPU_context_bounds':bounds,'full_32768_token_probe':False,'guided_decoding':'outlines:no-fallback; schema per call; never silently unguided','backend':'vLLM V0 AWQ FP16 eager TP1; chunked prefill2048; no prefix cache'}
  if self.environment['max_model_len']!=32768 or self.environment['KV_capacity_tokens']<32768:raise RuntimeError('ENGINE_CONTEXT_CAPACITY_INVALID')
 def count(self,prompt):return len(self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
 def generate(self,prompt,cap,schema):
  import time
  ids=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True)
  if len(ids)+cap+128>32768:raise RuntimeError('CONTEXT_OVERFLOW_NO_TRUNCATION')
  self.torch.cuda.reset_peak_memory_stats();start=time.monotonic()
  params=self.SamplingParams(temperature=0.0,top_p=1.0,top_k=-1,repetition_penalty=1.0,max_tokens=cap,seed=42,n=1,guided_decoding=self.GuidedDecodingParams(json=schema,backend="outlines:no-fallback"))
  r=self.engine.generate([{'prompt_token_ids':ids}],params,use_tqdm=False)[0];out=r.outputs[0]
  if len(r.prompt_token_ids)!=len(ids):raise RuntimeError('INPUT_TOKEN_MISMATCH')
  return out.text,{'input_tokens':len(ids),'output_tokens':len(out.token_ids),'seconds':time.monotonic()-start,'finish_reason':out.finish_reason,'peak_allocated_bytes':self.torch.cuda.max_memory_allocated(),'peak_reserved_bytes':self.torch.cuda.max_memory_reserved()}
