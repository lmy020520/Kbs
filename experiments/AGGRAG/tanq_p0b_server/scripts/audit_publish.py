"""Run on the exact Git index. No auto-add or push; print paths/counts only."""
import subprocess,re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2];PREFIX=str(ROOT.relative_to(REPO))+'/'
names=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=REPO).decode().split('\0');names=[x for x in names if x]
if not names:raise SystemExit('No staged delivery')
errors=[];total=0
for name in names:
 if not name.startswith(PREFIX):errors.append({'path':name,'reason':'OUTSIDE_ALLOWED_EXPERIMENT'});continue
 rel=name[len(PREFIX):];p=REPO/name;b=p.read_bytes();total+=len(b)
 if any(k in Path(rel).parts for k in ('results','private','models','.cache','.venv','__pycache__')) or p.suffix.lower() in ('.jsonl','.csv','.bin','.safetensors','.gguf','.pyc','.gz','.tar') or len(b)>2_000_000:errors.append({'path':name,'reason':'FORBIDDEN_PAYLOAD_OR_SIZE'})
 text=b.decode('utf-8',errors='replace')
 if re.search(r'(?:sk-[A-Za-z0-9_-]{24,}|hf_[A-Za-z0-9]{24,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',text):errors.append({'path':name,'reason':'SECRET_PATTERN'})
 if p.suffix=='.json':
  def walk(x):
   if isinstance(x,dict):
    if set(x)&{'answer_table','answer_list','filter_pass','model_input','evidence_units'}:errors.append({'path':name,'reason':'DATA_OR_GOLD_FIELDS'})
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(json.loads(text))
if errors:raise SystemExit(json.dumps({'status':'FAIL','errors':errors},indent=2))
print(json.dumps({'status':'PASS','files':len(names),'bytes':total,'allowed_prefix':PREFIX,'model_weights_or_raw_data':False},indent=2))
