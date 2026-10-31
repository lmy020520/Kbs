"""CPU-only official scoring AFTER prediction SHA freeze; never imported by worker."""
import argparse,sys,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
from diagnostics import compare,parse_reference
from reporting import report

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',default=str(ROOT/'results/server_smoke'));p.add_argument('--data-dir',required=True);a=p.parse_args();run=Path(a.run_dir)
 verify_prediction_freeze(run)
 if (run/'SCORING_ATTEMPT.json').exists():raise SystemExit('Scoring already attempted; no repeated score/rewrite')
 write(run/'SCORING_ATTEMPT.json',{'at':time.time(),'after_prediction_freeze':True})
 manifest=load(ROOT/'config/private_data_manifest.json');gold=Path(a.data_dir)/'evaluation/reference.jsonl'
 if not gold.is_file() or sha(gold)!=manifest['gold_sha256']:raise RuntimeError('SERVER_DATA_BLOCKED: private evaluation reference missing or SHA mismatch')
 refs=rows(gold)
 if [x['sample_id'] for x in refs]!=manifest['sample_order']:raise RuntimeError('Reference order differs')
 scores={};diagnostics=[]
 for arm in ('B0','B1-Batch'):
  items=[]
  for r in refs:
   f=run/'predictions'/f"{r['sample_id']}_{arm}.json"
   if not f.exists():continue # Never-executed items stay NOT_RUN, not manufactured empty predictions.
   prediction=load(f);raw=r['record'];items.append({'init_qid':raw['init_qid'],'ext_question_rephrased':raw['ext_question_rephrased'],'answer_table':raw['answer_table'],'prediction':prediction.get('prediction','')})
   if prediction.get('table'):
    try:diagnostics.append({'sample_id':r['sample_id'],'arm':arm,**compare(prediction['table'],parse_reference(raw['answer_table']))})
    except Exception as e:diagnostics.append({'sample_id':r['sample_id'],'arm':arm,'status':'DIAGNOSTIC_UNRESOLVED','reason':str(e)})
  if not items:scores[arm]={'status':'NOT_RUN','scored_cases':0,'metrics':None};continue
  inp=run/f'{arm}_PRIVATE_SCORE_INPUT.jsonl';inp.write_bytes(b''.join(canonical_row(x) for x in items))
  output=run/f'{arm}_OFFICIAL_SCORES.json';per=run/f'{arm}_PRIVATE_OFFICIAL_PER_CASE.json'
  env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONPATH':str(ROOT/'vendor'),'TF_CPP_MIN_LOG_LEVEL':'2','PYTHONDONTWRITEBYTECODE':'1'}
  cmd=[sys.executable,'-m','tanq.evaluate_tanq',f'--input_path={inp}','--prediction_key=prediction',f'--output_path={output}',f'--sample_output_path={per}']
  result=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=300)
  (run/f'{arm}_SCORER.log').write_text(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError('Official CLI failed; no substitute metric: '+arm)
  scores[arm]={'status':'SCORED','scored_cases':len(items),'NOT_RUN_cases':3-len(items),'metrics':load(output),'scope':'official RMS on executed cases only; partial denominator explicitly reported'}
 write(run/'OFFICIAL_RMS_RESULTS.json',{'status':'SCORED','arms':scores,'all_three_cases_scored_each':all(s.get('scored_cases')==3 for s in scores.values()),'reference_scope':'AUTHOR_PUBLISHED_REFERENCE; not independent natural semantic Gold'})
 write(run/'PRIVATE_CUSTOM_DIAGNOSTICS.json',diagnostics);print(report(run))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('Scoring failed: '+str(e),file=sys.stderr);sys.exit(2)
