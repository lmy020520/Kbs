"""Strict allowlist statistics export. No prompts, source text, answers or tables."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
p=argparse.ArgumentParser();p.add_argument('--run-dir',default=str(ROOT/'results/server_smoke'));p.add_argument('--out',required=True);a=p.parse_args();run=Path(a.run_dir);out=Path(a.out)
if out.exists():raise SystemExit('Export destination exists')
out.mkdir(parents=True,mode=0o700)
summary=load(run/'RUN_SUMMARY.json');official=load(run/'OFFICIAL_RMS_RESULTS.json');env=load(run/'MODEL_ENVIRONMENT.json')
public={'status':summary['status'],'returned_calls':summary['returned_calls'],'reserved_calls':summary['reserved_calls'],'input_tokens':summary['input_tokens'],'output_tokens':summary['output_tokens'],'API_cost_CNY':0,'model':env.get('model'),'revision':env.get('revision'),'versions':env.get('versions'),'max_model_len_effective':env.get('max_model_len_effective'),'KV_capacity_tokens':env.get('KV_capacity_tokens'),'official_RMS':official,'scope':'PILOT_EXPLORATORY; no natural semantic F1'}
write(out/'SUMMARY_REDACTED.json',public)
write(out/'PRIVATE_RESULT_SHA256.json',{str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()})
print('Allowlist summary + hashes exported; inspect before sharing; no automatic Git add/push')
