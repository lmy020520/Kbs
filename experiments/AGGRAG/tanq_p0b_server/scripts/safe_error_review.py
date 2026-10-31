"""Private inspection helper. Does not label semantic correctness or call models."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import load
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);a=p.parse_args();d=Path(a.run_dir)
print(json.dumps(load(d/'RUN_SUMMARY.json'),indent=2))
print('Raw prompts, responses and reference values remain private; no automatic upload')
