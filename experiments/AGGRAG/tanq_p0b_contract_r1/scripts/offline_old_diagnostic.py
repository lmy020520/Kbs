"""Private read-only legacy diagnosis; does not unwrap, repair, render or score."""
import sys,argparse,collections,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import *
from binding import bind_quote
from contracts import parse_json
p=argparse.ArgumentParser();p.add_argument('--old-run-dir',required=True);p.add_argument('--source-only',required=True);p.add_argument('--out',required=True);a=p.parse_args()
run=Path(a.old_run_dir);inputs=Path(a.source_only);before=file_manifest(run);inputsha=sha(inputs)
sources={x['sample_id']:x for x in [json.loads(s) for s in inputs.read_text().splitlines()]};counts=collections.Counter();roots=[]
for f in sorted((run/'calls').glob('*.json')):
 r=load(f)
 if r['stage']!='batch':continue
 result=parse_json(r['response']);obj=result.get('value');roots.append({'sample_id':r['sample_id'],'raw_type':type(obj).__name__,'original_envelope_valid':isinstance(obj,dict) and set(obj)=={'facts'}})
 # Inspect legacy list members only as forensic candidates, never R1 accepted predictions.
 if isinstance(obj,list):
  for item in obj:
   if not isinstance(item,dict):counts['NON_OBJECT_ITEM']+=1;continue
   counts[bind_quote(item.get('evidence_id'),item.get('quote'),sources[r['sample_id']]['evidence_units'])['status']]+=1
expected={'EXACT_SOURCE_MATCH':9,'SAME_PAGE_OTHER_CHUNK':2,'DIFFERENT_PAGE_MATCH':5,'QUOTE_NOT_FOUND':8,'MISSING_QUOTE':6}
assert dict(counts)==expected,(counts,expected)
assert before==file_manifest(run) and inputsha==sha(inputs)
write(a.out,{'status':'READ_ONLY_DIAGNOSTIC_PASS','legacy_binding_counts':dict(counts),'raw_batch_roots':roots,'original_files_unchanged':True,'new_model_calls':0,'scores_recomputed':False,'scope':'Literal localization only; legacy envelopes remain invalid; not semantic Gold'})
print(json.dumps({'status':'PASS','counts':dict(counts),'new_model_calls':0,'new_scores':False}))
