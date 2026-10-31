"""Stdlib-only guards shared by private data preparation and the server runner."""
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.tmp')
 temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');os.chmod(temp,0o600);temp.replace(p)
def canonical_row(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n').encode()
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def verify_inputs(data_root):
 from baselines import validate_pack
 manifest=load(ROOT/'config/private_data_manifest.json');path=Path(data_root)/'inputs/source_only.jsonl'
 if not path.is_file():raise RuntimeError('SERVER_DATA_BLOCKED: missing private inputs/source_only.jsonl; see private transfer instructions')
 if sha(path)!=manifest['source_only_sha256']:raise RuntimeError('SERVER_DATA_BLOCKED: source-only SHA mismatch')
 records=rows(path)
 if [r['sample_id'] for r in records]!=manifest['sample_order']:raise RuntimeError('SERVER_DATA_BLOCKED: fixed three IDs/order mismatch')
 for p,m in zip(records,manifest['source_records']):
  validate_pack(p)
  if hashlib.sha256(canonical_row(p)).hexdigest()!=m['sha256'] or [e['evidence_id'] for e in p['evidence_units']]!=m['evidence_ids']:raise RuntimeError('SERVER_DATA_BLOCKED: evidence changed')
 return records
class CallBudget:
 def __init__(self,path,limit=9):self.path=Path(path);self.limit=limit
 def reserve(self,sample,stage):
  state=load(self.path) if self.path.exists() else {'attempts':[]}
  if len(state['attempts'])>=self.limit:raise RuntimeError('Generation call budget exhausted; no automatic retries')
  index=len(state['attempts']);state['attempts'].append({'index':index,'sample_id':sample,'stage':stage,'reserved_at':time.time(),'status':'RESERVED_BEFORE_GENERATION'})
  write(self.path,state);return index
 def finish(self,index,usage):
  state=load(self.path);state['attempts'][index].update(status='RETURNED',usage=usage);write(self.path,state)
def prediction_manifest(run):
 run=Path(run);files=[p for p in run.glob('predictions/*.json') if p.is_file()]
 return {str(p.relative_to(run)):sha(p) for p in sorted(files)}
def verify_prediction_freeze(run):
 run=Path(run);m=load(run/'PREDICTIONS_FROZEN.json')
 if m['files']!=prediction_manifest(run):raise RuntimeError('Frozen predictions changed')
 return m
