"""Run locally against existing AGGRAG; output private files OUTSIDE Git checkout."""
import sys,argparse,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
p=argparse.ArgumentParser();p.add_argument('--aggrag-root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
out=Path(a.out).resolve();repo=ROOT.parents[2]
if out.is_relative_to(repo):raise SystemExit('Private export must be outside Git repository')
if out.exists():raise SystemExit('Output exists; refuse overwrite')
old=Path(a.aggrag_root)/'experiments/tanq_p0b_pilot';m=load(ROOT/'config/private_data_manifest.json')
source=rows(old/'data/source_only.jsonl');ref=rows(old/'evaluation/reference.jsonl')
for rel,records in [('inputs/source_only.jsonl',source),('evaluation/reference.jsonl',ref)]:
 selected=[next(x for x in records if x['sample_id']==key) for key in m['sample_order']]
 p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b''.join(canonical_row(x) for x in selected));os.chmod(p,0o600)
os.chmod(out,0o700)
assert sha(out/'inputs/source_only.jsonl')==m['source_only_sha256']
assert sha(out/'evaluation/reference.jsonl')==m['gold_sha256']
verify_inputs(out)
write(out/'PRIVATE_TRANSFER_RECEIPT.json',{'sample_ids':m['sample_order'],'source_sha256':m['source_only_sha256'],'gold_sha256':m['gold_sha256'],'distribution':'LOCAL_PRIVATE_RESEARCH_ONLY; do not add to Git or public logs'})
print('Private export verified: three fixed samples, original evidence order; no model run')
