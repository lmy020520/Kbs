"""CPU-only package/data/authorization readiness. Does not load any model."""
import sys,argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import *
p=argparse.ArgumentParser();p.add_argument('--data-dir');a=p.parse_args();verify_public()
ids=load(ROOT/'config/private_data_manifest.json')['sample_order']
if a.data_dir:verify_inputs(a.data_dir)
print(json.dumps({'version':'P0B_BASELINE_CONTRACT_REPAIR_R1','source_verification':'PASS' if a.data_dir else 'NOT_CHECKED','samples':ids,'future_nominal_unique_generations':9,'shared_plans':3,'B0_generations':3,'batch_generations':3,'each_arm_standalone_calls':6,'naively_summed_standalone_total':12,'GPU_authorized':False,'new_model_calls':0},indent=2))
