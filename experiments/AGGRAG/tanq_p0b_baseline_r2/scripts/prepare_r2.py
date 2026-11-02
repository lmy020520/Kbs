"""CPU-only input and schema preflight. Does not read Gold or load a model."""
import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import verify_inputs,verify_public,load
from schemas import plan_schema,table_schema,facts_schema,compile_regex
p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);a=p.parse_args()
verify_public();packs=verify_inputs(a.data_dir)
fixture=load(ROOT/'fixtures/unit_world.json')
for schema in [plan_schema(),table_schema(fixture['plan']),facts_schema(fixture['plan'],fixture['units'])]:compile_regex(schema)
print(json.dumps({'version':'P0B_BASELINE_CONTRACT_REPAIR_R2','source_verification':'PASS','samples':[p['sample_id'] for p in packs],'schema_compiler':'outlines-core==0.1.26; CPU fixture compilation PASS','semantic_plan_verification':'UNVERIFIED','future_max_generations':9,'shared_plan_max':3,'B0_R2_max':3,'Batch_R2_max':3,'GPU_authorized':False,'new_model_calls':0},indent=2))
