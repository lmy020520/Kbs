"""Allowlist summary only. No original prompts, tables, values, quotes or reference."""
import sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import *
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--out',required=True);a=p.parse_args();run=Path(a.run_dir);out=Path(a.out)
if out.exists():raise SystemExit('Export directory exists; no overwrite')
out.mkdir(mode=0o700,parents=True);summary=load(run/'RUN_SUMMARY.json')
write(out/'R1_REDACTED_SUMMARY.json',summary)
write(out/'PRIVATE_RESULT_SHA256.json',file_manifest(run))
print('R1 statistics+hashes only exported; inspect before sharing; no automatic Git push')
