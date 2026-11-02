"""CPU-only R2 score; blocks comparison until every B1 Join really completed."""
import sys,argparse,os,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import *
from reporting import report
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--data-dir',required=True);a=p.parse_args();run=Path(a.run_dir)
frozen=load(run/'PREDICTIONS_FROZEN.json')
for key in ('predictions','calls','plans'):
    if frozen[key]!=file_manifest(run/key):raise SystemExit('Frozen R2 outputs changed; stop')
ids=load(ROOT/'config/private_data_manifest.json')['sample_order'];structured=[load(run/f'predictions/{sid}_B1-Batch-R2.json') for sid in ids]
if not all(r.get('join_completed') and r['status'] in ('JOIN_COMPLETED','JOIN_PARTIAL') for r in structured):raise SystemExit('SCORING_BLOCKED_INCOMPLETE_JOIN: retain engineering results; no B0/B1 effect comparison')
if (run/'SCORING_ATTEMPT.json').exists():raise SystemExit('Scoring already attempted; no overwrite')
write(run/'SCORING_ATTEMPT.json',{'after_prediction_and_calls_freeze':True})
# First semantic read of the evaluation reference occurs here, after prediction freeze.
gold=Path(a.data_dir)/'evaluation/reference.jsonl';manifest=load(ROOT/'config/private_data_manifest.json')
if sha(gold)!=manifest['gold_sha256']:raise SystemExit('Reference SHA mismatch')
refs={r['sample_id']:r['record'] for r in [json.loads(s) for s in gold.read_text().splitlines()]};scores={}
for arm in ('B0-R2','B1-Batch-R2'):
    rows=[]
    for sid in ids:
        r=load(run/f'predictions/{sid}_{arm}.json');ref=refs[sid]
        rows.append({'init_qid':ref['init_qid'],'ext_question_rephrased':ref['ext_question_rephrased'],'answer_table':ref['answer_table'],'prediction':r.get('prediction') or ''})
    inp=run/f'{arm}_PRIVATE_SCORE_INPUT.jsonl';inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));out=run/f'{arm}_OFFICIAL.json'
    cmd=[sys.executable,'-m','tanq.evaluate_tanq',f'--input_path={inp}','--prediction_key=prediction',f'--output_path={out}',f'--sample_output_path={run/(arm+"_PRIVATE_PER_CASE.json")}']
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONPATH':str(ROOT/'vendor'),'TF_CPP_MIN_LOG_LEVEL':'2','PYTHONDONTWRITEBYTECODE':'1'}
    r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=300);(run/f'{arm}_SCORER.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise SystemExit('Official scorer failed; no replacement score')
    scores[arm]=load(out)
write(run/'OFFICIAL_RMS_RESULTS.json',{'status':'SCORED','fixed_cases':3,'scores':scores,'reference':'AUTHOR_PUBLISHED_REFERENCE','natural_semantic_F1':None});report(run)
print('New R2 official scores saved privately; old experiment untouched')
