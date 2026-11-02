"""Portable I/O; prediction code never reads evaluation reference contents."""
from pathlib import Path
import json,hashlib,os
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');os.chmod(tmp,0o600);tmp.replace(p)
def verify_inputs(data):
 p=Path(data)/'inputs/source_only.jsonl';m=load(ROOT/'config/private_data_manifest.json')
 if not p.is_file() or sha(p)!=m['source_only_sha256']:raise RuntimeError('DATA_INVALID: private source-only file missing or SHA mismatch')
 packs=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
 if [x.get('sample_id') for x in packs]!=m['sample_order']:raise RuntimeError('DATA_INVALID: IDs/order changed')
 for x,record in zip(packs,m['source_records']):
  if set(x)!={'sample_id','question','evidence_units'}:raise RuntimeError('DATA_INVALID: unexpected predictor fields')
  raw=(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n').encode()
  if hashlib.sha256(raw).hexdigest()!=record['sha256'] or [u['evidence_id'] for u in x['evidence_units']]!=record['evidence_ids']:raise RuntimeError('DATA_INVALID: evidence pool changed')
 return packs

def file_manifest(folder):
 root=Path(folder);return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def verify_public():
 m=load(ROOT/'PUBLIC_SHA256.json')['files'];bad=[k for k,v in m.items() if not (ROOT/k).is_file() or sha(ROOT/k)!=v]
 if bad:raise RuntimeError('CODE_MANIFEST_INVALID: '+str(bad))

def authorization(path):
 # This check must run before any model or CUDA import.
 if not path:return {'status':'GPU_NOT_AUTHORIZED','reason':'R2 needs a NEW explicit approval file; old nine-call budget is exhausted'}
 p=Path(path)
 if not p.is_file():return {'status':'GPU_NOT_AUTHORIZED','reason':'Approval file absent'}
 a=load(p)
 if not isinstance(a,dict) or a.get('authorized') is not True:return {'status':'GPU_NOT_AUTHORIZED','reason':'No new affirmative R2 approval'}
 cfg=load(ROOT/'config/r2_config.json');freeze=load(ROOT/'config/smoke_freeze.json');contract=load(ROOT/'CONTRACT_DIGEST.json')['sha256']
 expected={'authorized':True,'version':cfg['version'],'model_revision':cfg['revision'],'max_calls':9,'wall_seconds':7200,'call_seconds':1200,'sample_ids':[s['sample_id'] for s in freeze['samples']],'contract_sha256':contract}
 if any(a.get(k)!=v for k,v in expected.items()):return {'status':'GPU_NOT_AUTHORIZED','reason':'Approval does not match fixed R2 scope/version/budget'}
 import re
 if not isinstance(a.get('run_id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,60}',a['run_id']):return {'status':'GPU_NOT_AUTHORIZED','reason':'Unique R2 run_id required'}
 return {'status':'AUTHORIZED','approval':a,'sha256':sha(p)}
