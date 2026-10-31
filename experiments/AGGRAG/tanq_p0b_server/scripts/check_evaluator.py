"""Official CLI CPU sanity check on fictional UNIT_ONLY tables, not model scores."""
import argparse,sys,subprocess,os,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--report');a=p.parse_args()
 with tempfile.TemporaryDirectory() as d:
  d=Path(d);fixtures=[{'init_qid':'UNIT_EXACT','ext_question_rephrased':'UNIT_ONLY','answer_table':'entity | value\nA | red','prediction':'entity | value\nA | red'},{'init_qid':'UNIT_NUMERIC','ext_question_rephrased':'UNIT_ONLY','answer_table':'entity | value\nA | 100','prediction':'entity | value\nA | 105'}]
  inp=d/'unit.jsonl';inp.write_text(''.join(json.dumps(x)+'\n' for x in fixtures));out=d/'scores.json';per=d/'per.json'
  env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONPATH':str(ROOT/'vendor'),'TF_CPP_MIN_LOG_LEVEL':'2','PYTHONDONTWRITEBYTECODE':'1'}
  cmd=[sys.executable,'-m','tanq.evaluate_tanq',f'--input_path={inp}','--prediction_key=prediction',f'--output_path={out}',f'--sample_output_path={per}'];r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
  if r.returncode:print(r.stderr,file=sys.stderr);raise RuntimeError('Official CLI failed')
  scores=json.loads(out.read_text());cases=json.loads(per.read_text());assert cases['UNIT_EXACT']['f1']==1;assert abs(cases['UNIT_NUMERIC']['f1']-.95)<1e-10
  result={'status':'PASS','scope':'UNIT_ONLY_NOT_MODEL_PERFORMANCE','fixtures':2,'official_CLI_exit':r.returncode,'aggregate_expected_F1':97.5,'aggregate_observed_F1':scores['table_datapoints_f1']}
  if a.report:Path(a.report).write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result))
if __name__=='__main__':main()
