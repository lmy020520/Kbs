"""Summaries do not create predictions, references or semantic Gold."""
from common import *
def report(run):
 run=Path(run);expected=load(ROOT/'config/private_data_manifest.json')['sample_order'];calls=[]
 for p in sorted((run/'calls').glob('*.json')) if (run/'calls').exists() else []:calls.append(load(p))
 (run/'RAW_PREDICTIONS.jsonl').write_bytes(b''.join(canonical_row(c) for c in calls));os.chmod(run/'RAW_PREDICTIONS.jsonl',0o600)
 arms={}
 for arm,name in [('B0','B0_RESULTS.json'),('B1-Batch','B1_BATCH_RESULTS.json')]:
  rec=[]
  for sid in expected:
   p=run/'predictions'/f'{sid}_{arm}.json';rec.append(load(p) if p.exists() else {'sample_id':sid,'arm':arm,'status':'NOT_RUN','prediction':None})
  arms[arm]=rec;write(run/name,{'scope':'PILOT_EXPLORATORY','cases':rec,'semantic_accuracy':None})
 official=load(run/'OFFICIAL_RMS_RESULTS.json') if (run/'OFFICIAL_RMS_RESULTS.json').exists() else {'status':'NOT_RUN','reason':'Not yet scored or no eligible frozen prediction set','B0':None,'B1-Batch':None}
 write(run/'OFFICIAL_RMS_RESULTS.json',official)
 n=sum(c.get('status')=='RETURNED' for c in calls);success=n==9 and all(r['status']=='SUCCESS' for rs in arms.values() for r in rs) and official.get('status')=='SCORED' and official.get('all_three_cases_scored_each') and not (run/'WORKER_FAILURE.json').exists()
 if success:status='SERVER_SMOKE_SUCCESS'
 elif n:status='SERVER_SMOKE_PARTIAL'
 elif (run/'DATA_FAILURE.json').exists():status='SERVER_DATA_BLOCKED'
 else:status='SERVER_MODEL_BLOCKED'
 errors=[{'sample_id':r['sample_id'],'arm':r['arm'],'status':r['status'],'error':r.get('error'),'quote_rejection_count':len(r.get('quote_rejections',[]))} for rs in arms.values() for r in rs]
 (run/'SMOKE_ERROR_ANALYSIS.md').write_text('# Smoke工程与错误状态\n\n全部为PILOT_EXPLORATORY。格式/quote/Join检查不是独立语义正确性。没有人工语义Gold，不计算自然F1。\n\n```json\n'+json.dumps(errors,ensure_ascii=False,indent=2)+'\n```\n')
 (run/'SMOKE_GATE_DECISION.md').write_text('# Smoke Gate\n\n'+status+'\n\n真实返回调用数：'+str(n)+' / 9。调用上限不因失败重试重置。\n\n成功只表示本轮模型/输出/评分工程链路正常，不代表发现算法创新，也不批准30题或原逐单元B1。\n')
 write(run/'RUN_SUMMARY.json',{'status':status,'returned_calls':n,'reserved_calls':len(load(run/'CALL_LEDGER.json')['attempts']) if (run/'CALL_LEDGER.json').exists() else 0,'API_cost_CNY':0,'input_tokens':sum(c.get('usage',{}).get('input_tokens',0) for c in calls),'output_tokens':sum(c.get('usage',{}).get('output_tokens',0) for c in calls),'GPU_loading_attempted':bool(load(run/'MODEL_ENVIRONMENT.json').get('model_loaded')) or ((run/'WORKER_STATE.json').exists() and load(run/'WORKER_STATE.json').get('phase')=='LOADING_MODEL'),'semantic_gold':None,'official_score_status':official['status']})
 return status
