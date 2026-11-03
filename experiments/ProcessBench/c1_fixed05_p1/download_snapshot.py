"""User-invoked fixed snapshot download. No automatic retry, resume, model load or GPU."""
import argparse,urllib.request,os
from pathlib import Path
from contract import *
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--endpoint',default='https://huggingface.co',choices=['https://huggingface.co','https://hf-mirror.com']);a=p.parse_args();target=Path(a.model);target.mkdir(parents=True,exist_ok=True);m=load(ROOT/'config/model_manifest.json')
for f in m['files']:
 dest=target/f['filename']
 if dest.exists():
  if dest.stat().st_size!=f['bytes'] or sha(dest)!=f['sha256']:raise SystemExit('Existing file mismatch: '+str(dest))
  print('Already SHA verified:',dest.name,flush=True);continue
 part=dest.with_name(dest.name+'.part')
 if part.exists():raise SystemExit('Partial file exists; preserve and report, no automatic restart: '+str(part))
 url=f'{a.endpoint}/{m["model"]}/resolve/{m["revision"]}/{f["filename"]}'
 print('Downloading fixed file:',dest.name,'bytes',f['bytes'],flush=True)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ProcessBench-C1-fixed05/1.0'}),timeout=60) as r,part.open('xb') as w:
  size=0
  while True:
   b=r.read(4*1024*1024)
   if not b:break
   size+=len(b)
   if size>f['bytes']:raise ContractError('Unexpected download size')
   w.write(b)
 if size!=f['bytes'] or sha(part)!=f['sha256']:raise ContractError('Downloaded SHA/size mismatch; preserve.part and stop')
 os.rename(part,dest);print('SHA256 verified:',dest.name,flush=True)
save(target/'C1_SNAPSHOT_VERIFIED.json',{'model':m['model'],'revision':m['revision'],'files':verify_model(target,m),'download_endpoint':a.endpoint,'automatic_retry':False});print('Snapshot complete; no model inference.')
