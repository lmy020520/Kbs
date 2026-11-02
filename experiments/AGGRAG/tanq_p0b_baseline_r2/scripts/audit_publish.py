"""Index-bound publication scanner. Does not read private historical data."""
import subprocess,re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2];prefix=str(ROOT.relative_to(REPO))+'/'
paths=[p for p in subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=REPO).decode().split('\0') if p];issues=[];size=0
if not paths:raise SystemExit('Nothing staged')
for name in paths:
 if not name.startswith(prefix):issues.append({'path':name,'reason':'OUTSIDE_R2_DIRECTORY'});continue
 p=REPO/name;b=p.read_bytes();size+=len(b)
 if p.suffix in ('.jsonl','.csv','.bin','.safetensors','.gguf','.pyc','.gz','.tar') or any(x in p.parts for x in ('results','private','__pycache__','.venv')) or len(b)>2_000_000:issues.append({'path':name,'reason':'FORBIDDEN_DATA_OR_LARGE_FILE'})
 if re.search(rb'(?:sk-[A-Za-z0-9_-]{24,}|hf_[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',b):issues.append({'path':name,'reason':'SECRET_PATTERN'})
 if p.suffix=='.json':
  def walk(x):
   if isinstance(x,dict):
    if set(x)&{'answer_table','answer_list','filter_pass','model_input'}:issues.append({'path':name,'reason':'FORBIDDEN_GOLD_DATA_KEY'})
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(json.loads(b))
if issues:raise SystemExit(json.dumps({'status':'FAIL','issues':issues},indent=2))
print(json.dumps({'status':'PASS','files':len(paths),'bytes':size,'scope':prefix,'no_data_weights_secrets':True},indent=2))
