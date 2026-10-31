import argparse,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from preflight import check
p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--model-dir',required=True);a=p.parse_args()
r,_,_=check(a.data_dir,a.model_dir);print(json.dumps(r,indent=2))
