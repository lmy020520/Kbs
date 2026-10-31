"""No GPU allocations: CPU tokenizer, exact data/model hashes, environment inventory."""
import json,os,subprocess,sys,platform,importlib.metadata as metadata
from pathlib import Path
from common import *
def inspect_model(model):
 cfg=load(ROOT/'config/server_config.json');model=Path(model)
 if not (model/'AGGRAG_MODEL_RECEIPT.json').is_file():raise RuntimeError('SERVER_MODEL_BLOCKED: download receipt absent')
 receipt=load(model/'AGGRAG_MODEL_RECEIPT.json')
 if receipt['model']!=cfg['model'] or receipt['revision']!=cfg['revision']:raise RuntimeError('SERVER_MODEL_BLOCKED: wrong official model/revision')
 for name,digest in receipt['files'].items():
  f=model/name
  if not f.resolve().is_relative_to(model.resolve()) or not f.is_file() or sha(f)!=digest:raise RuntimeError('SERVER_MODEL_BLOCKED: model file SHA mismatch')
 mc=load(model/'config.json')
 if mc.get('quantization_config',{}).get('quant_method')!='awq' or mc.get('max_position_embeddings',0)<32768:raise RuntimeError('SERVER_MODEL_BLOCKED: AWQ/native32K config missing')
 return receipt,mc

def check(data,model,check_gpu=True):
 if platform.system()!='Linux' or platform.machine()!='x86_64' or sys.version_info[:2]!=(3,11):raise RuntimeError('SERVER_MODEL_BLOCKED: fixed lock requires Linux x86_64 Python3.11')
 cfg=load(ROOT/'config/server_config.json');packs=verify_inputs(data);receipt,mc=inspect_model(model)
 os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
 from transformers import AutoTokenizer
 tok=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False)
 from baselines import dump
 prompts=load(ROOT/'config/prompts.json');batch=load(ROOT/'config/B1_BATCH_PREREGISTRATION.json')
 lengths=[]
 def count(prompt):return len(tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
 for p in packs:
  direct=prompts['B0']+'\n'+dump({'question':p['question'],'evidence_units':p['evidence_units']})
  plan=prompts['B1_plan_question_only']+'\nQuestion: '+p['question']
  extraction=batch['prompt']+'\n'+dump({'question':p['question'],'predicates':[],'evidence_units':p['evidence_units']})
  n=[count(direct),count(plan),count(extraction)]
  if n[0]+4096>32768 or n[1]+4096>32768 or n[2]+8192+1024+128>32768:raise RuntimeError('SERVER_MODEL_BLOCKED: frozen full evidence exceeds native32K, no truncation permitted')
  lengths.append({'sample_id':p['sample_id'],'B0_input_tokens':n[0],'plan_input_tokens':n[1],'batch_empty_predicates_input_tokens':n[2],'batch_predicate_reserve':1024,'max_context':32768})
 versions={n:metadata.version(n) for n in cfg['runtime_versions']}
 for n,v in cfg['runtime_versions'].items():
  if versions[n].split('+')[0]!=v:raise RuntimeError('SERVER_MODEL_BLOCKED: runtime version differs from lock: '+n)
 inventory=None
 if check_gpu:
  selected=os.environ.get('CUDA_VISIBLE_DEVICES','')
  if not selected or ',' in selected or selected=='-1':raise RuntimeError('Select exactly one authorized GPU using CUDA_VISIBLE_DEVICES')
  inventory=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free,driver_version','--format=csv'],text=True)
 return {'model':cfg['model'],'revision':cfg['revision'],'versions':versions,'model_manifest_sha256':sha(Path(model)/'AGGRAG_MODEL_RECEIPT.json'),'lengths':lengths,'GPU_inventory':inventory,'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'trust_remote_code':False,'preflight':'CPU_TOKENIZER_ONLY_NO_MODEL_LOADING'},packs,tok
