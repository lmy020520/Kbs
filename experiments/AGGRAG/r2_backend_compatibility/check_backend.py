"""Independent CPU-only check of the ORIGINAL R2 Plan schema. No generation API.
One explicitly requested attempt per invocation. Existing attempts cannot be reset.
"""
import argparse,hashlib,json,os,sys,subprocess,signal,time,traceback,shutil
from pathlib import Path
COMMIT='24cadba0b0c04a23bd876fbcd2770086bc20959f'
SCHEMA_SHA='86908a9e09cbf609077312748156ba211f6984974e62312cbfae06b82cd8a5e2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 with Path(p).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def schema_text(s):return json.dumps(s,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def original_schema(code):
 manifest=json.loads((code/'PUBLIC_SHA256.json').read_text())['files']
 for name,digest in manifest.items():
  if sha(code/name)!=digest:raise RuntimeError('R2_PUBLIC_SHA_MISMATCH: '+name)
 sys.path.insert(0,str(code/'src'))
 from schemas import plan_schema
 schema=plan_schema()
 if hashlib.sha256(schema_text(schema).encode()).hexdigest()!=SCHEMA_SHA:raise RuntimeError('ORIGINAL_PLAN_SCHEMA_MISMATCH')
 return schema

def worker(a):
 import faulthandler,importlib.metadata as md
 faulthandler.enable();faulthandler.dump_traceback_later(110,repeat=False)
 code=Path(a.code);out=Path(a.out);schema=original_schema(code)
 def result(status,**details):
  save(out/'WORKER_RESULT.json',{'status':status,'model_generations':0,'schema_transformed':False,**details});print(status,flush=True)
 versions={}
 for name in ['vllm','xgrammar','outlines','outlines-core','torch','transformers','jsonschema']:
  try:versions[name]=md.version(name)
  except md.PackageNotFoundError:versions[name]='NOT_INSTALLED'
 save(out/'ENVIRONMENT.json',{'python':sys.version,'versions':versions,'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES')})
 print('VERSIONS '+json.dumps(versions),flush=True)
 if versions['vllm']!='0.8.5.post1' or versions['xgrammar']!='0.1.18':
  result('BACKEND_INIT_BLOCKED',reason='Required existing pinned vLLM/XGrammar missing or different; no installation/upgrade attempted');return
 import xgrammar
 print('XGRAMMAR_IMPORT_PASS',flush=True)
 from vllm.sampling_params import GuidedDecodingParams
 from vllm.model_executor.guided_decoding import maybe_backend_fallback,get_local_guided_decoding_logits_processor
 from vllm.model_executor.guided_decoding.utils import has_xgrammar_unsupported_json_features
 import inspect
 utils_path=Path(inspect.getfile(has_xgrammar_unsupported_json_features))
 save(out/'INSTALLED_DISPATCH_SOURCE.json',{'path':str(utils_path),'sha256':sha(utils_path),'guard_source':inspect.getsource(has_xgrammar_unsupported_json_features),'fallback_source':inspect.getsource(maybe_backend_fallback)})
 guide=GuidedDecodingParams(json=schema,backend='xgrammar:no-fallback')
 unsupported=has_xgrammar_unsupported_json_features(schema)
 print('ORIGINAL_SCHEMA_UNSUPPORTED_FEATURES='+str(unsupported),flush=True)
 try:maybe_backend_fallback(guide)
 except ValueError as e:
  traceback.print_exc()
  result('CONTRACT_INCOMPATIBLE',reason=str(e),stage='Installed vLLM original-schema dispatch',unsupported_guard=unsupported,backend='xgrammar:no-fallback');return
 if guide.backend!='xgrammar:no-fallback':
  result('CONTRACT_INCOMPATIBLE',reason='Silent fallback/change detected');return
 # Only reached if installed dispatch accepts the ORIGINAL unchanged schema.
 from transformers import AutoTokenizer
 from types import SimpleNamespace
 model=Path(a.model);cfg=json.loads((model/'config.json').read_text());receipt=json.loads((model/'AGGRAG_MODEL_RECEIPT.json').read_text())
 assert receipt['revision']=='b25037543e9394b818fdfca67ab2a00ecc7dd641'
 assert receipt['model']=='Qwen/Qwen2.5-7B-Instruct-AWQ'
 tok=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False)
 mc=SimpleNamespace(hf_text_config=SimpleNamespace(vocab_size=cfg['vocab_size']),model=str(model))
 processor=get_local_guided_decoding_logits_processor(guide,tok,mc)
 assert processor is not None
 info=xgrammar.TokenizerInfo.from_huggingface(tok,vocab_size=cfg['vocab_size'])
 compiler=xgrammar.GrammarCompiler(info,max_threads=1,cache_enabled=False)
 compiled=compiler.compile_json_schema(schema)
 matcher=xgrammar.GrammarMatcher(compiled)
 # No schema rewrite; this is initialization only, not semantic plan or model accuracy.
 result('BACKEND_COMPATIBLE_NO_GENERATION',stage='Original-schema compiler and matcher initialization',processor=type(processor).__name__,matcher=type(matcher).__name__,semantic_plan_verification='UNVERIFIED',scope='Plan initialization only; dynamic table/facts schemas and GPU execution not tested')
 faulthandler.cancel_dump_traceback_later()

def parent(a):
 code=Path(a.code).resolve();root=Path(a.out).resolve();root.mkdir(parents=True,exist_ok=True)
 original_schema(code)
 if a.attempt not in (1,2):raise RuntimeError('At most two explicit attempts; no automatic retry')
 if a.attempt==2 and not (root/'attempt_01').exists():raise RuntimeError('Attempt 1 must be recorded first')
 out=root/f'attempt_{a.attempt:02d}';out.mkdir(mode=0o700)
 log=Path(a.original_log)
 if not log.is_file():
  save(out/'RESULT.json',{'status':'INSUFFICIENT_EVIDENCE','reason':'Original server cpu_diagnostic.log missing','attempt_started':False,'model_generations':0});print('INSUFFICIENT_EVIDENCE: original log missing');return
 shutil.copyfile(log,out/'ORIGINAL_cpu_diagnostic.log')
 for name in ['cpu_diagnostic.exit','cpu_diagnostic.py']:
  extra=log.parent/name
  if extra.is_file():shutil.copyfile(extra,out/('ORIGINAL_'+name))
 save(out/'ORIGINAL_LOG_RECEIPT.json',{'original_path':str(log),'sha256':sha(log),'bytes':log.stat().st_size,'source':'Exact server file copy, not pasted text','historical_python_traceback_present':'Traceback (most recent call last)' in log.read_text(errors='replace'),'prior_timeout_stack_limit':'Absent historical stack cannot be reconstructed; new attempt has 110s faulthandler'})
 schema=original_schema(code);(out/'ORIGINAL_PLAN_SCHEMA.json').write_text(schema_text(schema))
 save(out/'ATTEMPT_RESERVED.json',{'attempt':a.attempt,'limit_seconds':120,'automatic_retry':False,'frozen_R2_commit':COMMIT,'original_schema_sha256':SCHEMA_SHA,'raw_log_sha256':sha(log),'model_generations':0})
 env={**os.environ,'CUDA_VISIBLE_DEVICES':'','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','VLLM_USE_V1':'0','PYTHONDONTWRITEBYTECODE':'1','VLLM_NO_USAGE_STATS':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false'}
 cmd=[sys.executable,'-u',str(Path(__file__).resolve()),'--worker','--code',str(code),'--out',str(out),'--model',a.model]
 started=time.monotonic();timed_out=False
 with (out/'COMPATIBILITY.log').open('x') as log_out:
  p=subprocess.Popen(cmd,env=env,stdout=log_out,stderr=subprocess.STDOUT,start_new_session=True)
  try:p.wait(timeout=120)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 record= json.loads((out/'WORKER_RESULT.json').read_text()) if (out/'WORKER_RESULT.json').exists() else {'status':'BACKEND_INIT_BLOCKED','reason':'120s timeout' if timed_out else 'Worker failed; inspect full log'}
 record.update(exit_code=p.returncode,timeout=timed_out,wall_seconds=time.monotonic()-started,attempt=a.attempt,automatic_retry=False,model_generations=0)
 save(out/'RESULT.json',record)
 save(out/'SHA256.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='SHA256.json'})
 print((out/'COMPATIBILITY.log').read_text(errors='replace'));print(json.dumps(record,ensure_ascii=False,indent=2))
 print('STOP: no GPU Smoke, generation, retry, schema conversion or R3 is started.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--code',required=True);p.add_argument('--out',required=True);p.add_argument('--original-log');p.add_argument('--model',required=True);p.add_argument('--attempt',type=int,default=1);p.add_argument('--worker',action='store_true');a=p.parse_args()
 try:
  if a.worker:worker(a)
  elif not a.original_log:raise RuntimeError('Original log path required')
  else:parent(a)
 except BaseException:
  traceback.print_exc();sys.exit(2)
