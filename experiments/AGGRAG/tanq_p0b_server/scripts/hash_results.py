import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);a=p.parse_args();run=Path(a.run_dir)
write(run/'RESULT_SHA256.json',{str(f.relative_to(run)):sha(f) for f in sorted(run.rglob('*')) if f.is_file() and f.name!='RESULT_SHA256.json'})
print('Private result SHA manifest written')
