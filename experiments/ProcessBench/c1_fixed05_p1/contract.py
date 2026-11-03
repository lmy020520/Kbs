"""Project preregistration + deterministic audit utilities. Standard library only."""
import json,math,hashlib,os,datetime
from pathlib import Path
THRESHOLD=0.5
class ContractError(ValueError):pass
class ResourceError(RuntimeError):pass
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def obj_sha(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def append(p,d):
 with Path(p).open('a') as f:f.write(json.dumps(d,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def validate_scores(scores,count=None):
 if not isinstance(scores,list) or not scores:raise ContractError('Empty/missing step scores')
 if count is not None and len(scores)!=count:raise ContractError('Step score count mismatch')
 out=[]
 for x in scores:
  if x is None or isinstance(x,bool):raise ContractError('Missing/boolean step score')
  try:v=float(x)
  except (TypeError,ValueError):raise ContractError('Invalid step score')
  if not math.isfinite(v) or not 0<=v<=1:raise ContractError('Invalid step score')
  out.append(v)
 return out
def predict_first_error(scores):
 # Validate ALL values before returning an early error; no hidden NaN later in the trajectory.
 values=validate_scores(scores)
 for i,v in enumerate(values):
  if v<THRESHOLD:return i
 return -1
def check_authorization(a):
 if a.get('authorization')!='C1_FIXED_THRESHOLD_SMOKE_APPROVED' or a.get('threshold')!=.5:raise ContractError('Wrong authorization/threshold')
 for k,w in [('max_trajectories',20),('max_step_scores',112),('expected_input_tokens',10228),('planned_GPU_count',1),('forward_per_trajectory',1),('worker_watchdog_seconds',3550),('max_GPUs_authorized',2),('max_input_tokens',1153),('model_context_limit',4096)]:
  if a.get(k)!=w:raise ContractError('Changed authorization '+k)
 if a.get('max_wall_seconds')!=3600 or a.get('automatic_retry') is not False:raise ContractError('Changed time/retry contract')
def verify_model(model,manifest):
 model=Path(model);out=[]
 for f in manifest['files']:
  n=f['filename']
  if Path(n).name!=n:raise ContractError('Unsafe model filename')
  p=model/n
  if not p.is_file() or p.stat().st_size!=f['bytes'] or sha(p)!=f['sha256']:raise ContractError('MODEL_SHA_MISMATCH '+n)
  out.append({'filename':n,'bytes':f['bytes'],'sha256':f['sha256']})
 return out
def verify_inputs(data,root):
 # Evaluation files intentionally NOT opened here, including for hashing.
 data=Path(data);root=Path(root);m=load(root/'config/data_manifest.json');f=load(root/'config/sample_freeze.json');a=load(root/'config/authorization.json');check_authorization(a)
 for rel,key in [('inputs/source_only.json','source_only_sha256'),('inputs/expected_cpu.json','expected_cpu_sha256')]:
  if sha(data/rel)!=m[key]:raise ContractError('INPUT_SHA_MISMATCH '+rel)
 src=load(data/'inputs/source_only.json');exp=load(data/'inputs/expected_cpu.json')
 if len(src)!=20 or len(exp)!=20 or len(f['cases'])!=20:raise ContractError('Frozen case count changed')
 if len({x['id'] for x in src})!=20:raise ContractError('Duplicate frozen ID')
 steps=tokens=0
 for s,e,c in zip(src,exp,f['cases']):
  if set(s)!={'id','subset','problem','steps'}:raise ContractError('Unexpected predictor fields (possible Gold leakage)')
  if s['id']!=e['id'] or s['id']!=c['id'] or s['subset']!=c['subset']:raise ContractError('Frozen order mismatch')
  if not isinstance(s['steps'],list) or len(s['steps'])!=c['steps'] or not all(isinstance(z,str) and z for z in s['steps']):raise ContractError('Invalid frozen steps')
  if obj_sha(s)!=c['visible_record_sha256']:raise ContractError('Visible text changed')
  if hashlib.sha256(e['prompt'].encode()).hexdigest()!=c['expected_prompt_sha256'] or len(e['input_token_ids'])!=c['expected_input_tokens']:raise ContractError('Expected prompt/token count mismatch')
  steps+=len(s['steps']);tokens+=len(e['input_token_ids'])
 if steps!=112 or tokens!=10228:raise ContractError('Authorized total changed')
 return src,exp
class Ledger:
 def __init__(self,path):self.path=Path(path);self.ids=set();self.steps=0
 def reserve(self,case_id,count):
  if case_id in self.ids or len(self.ids)>=20 or self.steps+count>112 or count<=0:raise ContractError('FORWARD_BUDGET_OR_REPEAT_BLOCKED')
  append(self.path,{'event':'RESERVE_BEFORE_FORWARD','id':case_id,'steps':count,'forward_number':len(self.ids)+1,'utc':utc()});self.ids.add(case_id);self.steps+=count
class AuthorizationLock:
 def __init__(self,path):self.path=Path(path)
 def acquire(self,run_id):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.path.open('x') as f:f.write(json.dumps({'authorization_used':run_id,'utc':utc(),'automatic_retry':False}))
def fixed_metrics(predictions,references):
 refs={x['id']:x for x in references};rows=[];hits=[];err=[];corr=[]
 for p in predictions:
  g=refs[p['id']]['published_first_error'];valid=p['status']=='SUCCESS';match=valid and p['pred_first_error_fixed_05']==g
  rows.append({'id':p['id'],'published_first_error':g,'pred_first_error_fixed_05':p.get('pred_first_error_fixed_05'),'status':p['status'],'valid_output':valid,'match':bool(match)})
  hits.append(int(match));(corr if g==-1 else err).append(int(match))
 ea=sum(err)/len(err) if err else None;ca=sum(corr)/len(corr) if corr else None
 harmonic=None if ea is None or ca is None else (0 if ea+ca==0 else 2*ea*ca/(ea+ca))
 return {'N':len(rows),'valid':sum(x['valid_output'] for x in rows),'matched':sum(hits),'first_error_accuracy_full_denominator':sum(hits)/len(hits) if hits else None,'error_trajectory_exact_accuracy':ea,'all_correct_trajectory_accuracy':ca,'processbench_style_harmonic_F1':harmonic,'formula':'2*error_exact_accuracy*correct_trajectory_accuracy/(sum); not ordinary binary F1','threshold_origin':'PROJECT_FIXED_05_NOT_AUTHOR_OFFICIAL_THRESHOLD','rows':rows}
