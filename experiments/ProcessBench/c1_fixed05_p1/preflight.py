"""CPU-only checks. No model constructor, torch forward or evaluation-file reads."""
import argparse,hashlib,importlib.metadata as md,sys
from pathlib import Path
from contract import *
ROOT=Path(__file__).resolve().parent

def environment():
 cfg=load(ROOT/'config/environment.json')
 if list(sys.version_info[:2])!=cfg['python_major_minor']:raise ContractError('Need existing Python3.11 environment')
 versions={}
 for n,v in cfg['packages'].items():
  actual=md.version(n);versions[n]=actual
  if actual.split('+')[0]!=v:raise ContractError(f'Environment mismatch {n}: {actual} expected {v}; no auto-install')
 return versions

def check(data,model):
 src,exp=verify_inputs(data,ROOT);manifest=load(ROOT/'config/model_manifest.json');files=verify_model(model,manifest);versions=environment()
 from transformers import AutoTokenizer
 tok=AutoTokenizer.from_pretrained(str(model),local_files_only=True,trust_remote_code=False,use_fast=True)
 marker=tok.encode('<extra_0>',add_special_tokens=False)
 if marker!=[151651]:raise ContractError('Scoring marker mismatch')
 rows=[]
 for s,e in zip(src,exp):
  messages=[{'role':'system','content':'Please reason step by step, and put your final answer within \\boxed{}.'},{'role':'user','content':s['problem']},{'role':'assistant','content':'<extra_0>'.join(s['steps'])+'<extra_0>'}]
  prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=False);ids=tok.encode(prompt)
  if prompt!=e['prompt'] or ids!=e['input_token_ids']:raise ContractError('RUNTIME_TOKENIZER_CHANGED '+s['id'])
  positions=[i for i,t in enumerate(ids) if t==marker[0]]
  if positions!=[x['scoring_marker_token_index'] for x in e['steps']]:raise ContractError('STEP_TOKEN_MAPPING_CHANGED')
  if len(ids)>4096:raise ContractError('NO_TRUNCATION_ALLOWED')
  rows.append({'id':s['id'],'input_tokens':len(ids),'scoring_positions':positions,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()})
 return {'status':'PASS','scope':'CPU_ONLY_NO_MODEL_INITIALIZATION','model_files':files,'versions':versions,'cases':rows,'total_tokens':sum(x['input_tokens'] for x in rows),'total_step_positions':sum(len(x['scoring_positions']) for x in rows),'threshold':.5,'equality_passes':True,'threshold_origin':'PROJECT_PREREGISTERED','reference_opened':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
 if out.exists():raise SystemExit('Preflight receipt exists; do not overwrite')
 try:receipt=check(Path(a.data),Path(a.model));save(out,receipt);print('CPU model/input/tokenizer preflight PASS; no model initialized.')
 except Exception as e:save(out,{'status':'BLOCKED','error':repr(e),'no_model_initialized':True});raise
