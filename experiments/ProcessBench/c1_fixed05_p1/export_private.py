"""Private archive for offline source-based review. Never Git add/push."""
import argparse,tarfile,shutil,tempfile,os
from pathlib import Path
from contract import *
from score_and_report import check_prediction_freeze
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--archive',required=True);a=p.parse_args();out=Path(a.out);archive=Path(a.archive);data=Path(a.data)
check_prediction_freeze(out)
if archive.exists():raise SystemExit('Archive already exists; do not overwrite')
with tempfile.TemporaryDirectory(prefix='c1-private-export-') as tmp:
 root=Path(tmp)/'C1_fixed05_dev20_20261103_01';root.mkdir()
 for f in out.iterdir():
  if f.is_file() and not f.is_symlink():shutil.copyfile(f,root/f.name)
 for folder in ['inputs','evaluation']:shutil.copytree(data/folder,root/folder)
 code=root/'public_code';code.mkdir()
 for n in load(ROOT/'PUBLIC_SHA256.json'):
  src=ROOT/n;dst=code/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 shutil.copyfile(ROOT/'PUBLIC_SHA256.json',code/'PUBLIC_SHA256.json')
 manifest={str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*')) if f.is_file()};save(root/'RESULT_SHA256.json',manifest)
 archive.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(archive,'x:gz') as tf:tf.add(root,arcname=root.name)
 os.chmod(archive,0o600)
 result=load(out/'FIXED05_RESULTS.json') if (out/'FIXED05_RESULTS.json').exists() else {'status':'SCORER_NOT_COMPLETE'}
 summary={'status':result.get('status'),'full20_metrics':{k:v for k,v in result.get('full20_metrics',{}).items() if k!='rows'},'cost':load(out/'RESOURCE_COST.json') if (out/'RESOURCE_COST.json').exists() else None,'private_archive_sha256':sha(archive),'AI_review':'PENDING_OFFLINE_SOURCE_REVIEW','no_automatic_upload':True}
 save(archive.with_suffix('.SUMMARY_REDACTED.json'),summary)
print('PRIVATE review archive:',archive);print('SHA256:',sha(archive));print('Contains original questions/steps/labels/prompts. Transfer privately; never auto Git add/push.')
