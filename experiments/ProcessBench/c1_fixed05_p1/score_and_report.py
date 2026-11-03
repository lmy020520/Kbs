"""CPU scorer. Enforces prediction freeze BEFORE opening reference labels."""
import argparse
from pathlib import Path
from contract import *
ROOT=Path(__file__).resolve().parent

def check_prediction_freeze(out):
 out=Path(out);f=load(out/'PREDICTION_FREEZE.json')
 if not f['worker_has_ended'] or not load(out/'SUPERVISION.json')['worker_has_ended']:raise ContractError('Worker still running')
 for n,h in f['files'].items():
  if Path(n).name!=n or sha(out/n)!=h:raise ContractError('PREDICTION_SHA_MISMATCH '+n)
 return f

def main(a):
 out=Path(a.out);data=Path(a.data)
 if (out/'FIXED05_RESULTS.json').exists():raise ContractError('Scoring already exists; preserve results')
 check_prediction_freeze(out);source,expected=verify_inputs(data,ROOT);pred=load(out/'PREDICTIONS_PRIVATE.json')
 if [x['id'] for x in pred]!=[x['id'] for x in source]:raise ContractError('Prediction order/denominator changed')
 rawfile=out/'RAW_TRAJECTORY_SCORES_PRIVATE.jsonl';raw=[__import__('json').loads(l) for l in rawfile.read_text().splitlines()] if rawfile.exists() else [];byraw={x['id']:x for x in raw}
 if len(byraw)!=len(raw):raise ContractError('Duplicate actual scored ID')
 if len(raw)>20 or set(byraw)-{x['id'] for x in source}:raise ContractError('Extra actual scored trajectory')
 if len(raw)!=sum(x['status']=='SUCCESS' for x in pred):raise ContractError('Raw/prediction success count mismatch')
 for p,s in zip(pred,source):
  if p['status']=='SUCCESS':
   validate_scores(p['step_scores'],len(s['steps']))
   if predict_first_error(p['step_scores'])!=p['pred_first_error_fixed_05']:raise ContractError('Fixed05 decision changed')
   r=byraw.get(p['id'])
   if not r or r['step_scores']!=p['step_scores'] or r['steps']!=s['steps'] or r['problem']!=s['problem'] or r['formal_forward_calls']!=1:raise ContractError('Missing or inconsistent raw real score record')
 # This is the FIRST evaluation-reference open/read of the inference+scoring workflow.
 refpath=data/'evaluation/reference.json';expectedsha=load(ROOT/'config/data_manifest.json')['reference_sha256_FOR_SCORER_ONLY']
 if sha(refpath)!=expectedsha:raise ContractError('REFERENCE_SHA_MISMATCH')
 refs=load(refpath)
 if [x['id'] for x in refs]!=[x['id'] for x in source]:raise ContractError('Reference identity/order mismatch')
 for r,s in zip(refs,source):
  if type(r['published_first_error']) is not int or not -1<=r['published_first_error']<len(s['steps']):raise ContractError('Reference label range invalid')
 save(out/'REFERENCE_COMPARISON_START.json',{'UTC':utc(),'prediction_freeze_sha256':sha(out/'PREDICTION_FREEZE.json'),'reference_sha256':expectedsha,'reference_opened_only_after_prediction_freeze_verified':True})
 valid=sum(x['status']=='SUCCESS' for x in pred);metrics=fixed_metrics(pred,refs) if valid else {'N':20,'valid':0,'metrics':None,'reason':'NO_MODEL_SCORES_NOT_A_ZERO_PERFORMANCE_RESULT','rows':[{'id':p['id'],'published_first_error':r['published_first_error'],'pred_first_error_fixed_05':None,'status':p['status'],'match':False} for p,r in zip(pred,refs)]}
 subsets={}
 for sub in ['gsm8k','math']:
  pp=[x for x in pred if x['subset']==sub];rr=[r for r,p in zip(refs,pred) if p['subset']==sub]
  subsets[sub]=fixed_metrics(pp,rr) if any(x['status']=='SUCCESS' for x in pp) else {'N':len(pp),'valid':0,'metrics':None}
 summary=load(out/'WORKER_SUMMARY.json') if (out/'WORKER_SUMMARY.json').exists() else {};sup=load(out/'SUPERVISION.json');returnedsteps=sum(len(p['step_scores']) for p in pred if p['status']=='SUCCESS')
 if valid==20 and returnedsteps==112 and sup['worker_exit']==0 and not sup['stop_reason']:status='C1_FIXED05_SMOKE_SUCCESS'
 elif valid or summary.get('actual_root_forward_attempts',0):status='C1_FIXED05_SMOKE_PARTIAL'
 elif summary.get('fatal',{}):
  err=summary['fatal'];status='C1_INPUT_CONTRACT_BLOCKED' if err['error_type']=='ContractError' else ('C1_RESOURCE_BLOCKED' if err['error_type']=='ResourceError' or 'out of memory' in err['error'].lower() else 'C1_MODEL_EXECUTION_BLOCKED')
 else:status='C1_RESOURCE_BLOCKED' if sup['stop_reason']=='TOTAL_WALL_TIMEOUT' else 'C1_MODEL_EXECUTION_BLOCKED'
 result={'status':status,'full20_metrics':metrics,'by_subset':subsets,'threshold':.5,'equality_passes':True,'comparison_scope':'PROJECT_FIXED05_DEV_NOT_OFFICIAL_THRESHOLD_REPLICATION','AI_review':'PENDING_CURRENT_CODEX_OFFLINE_REVIEW_OF_ALL_DISAGREEMENTS; not simulated','semantic_failure_mechanisms':'UNVERIFIED'};save(out/'FIXED05_RESULTS.json',result)
 queue=[]
 for p,r,s in zip(pred,refs,source):
  if p['status']=='SUCCESS' and p['pred_first_error_fixed_05']!=r['published_first_error']:
   pr=p['pred_first_error_fixed_05'];g=r['published_first_error'];position='FALSE_REJECT_ON_PUBLISHED_ALL_CORRECT' if g==-1 else ('MISSED_ALL_ERRORS' if pr==-1 else ('EARLY' if pr<g else 'LATE'))
   queue.append({'id':p['id'],'problem':s['problem'],'steps':s['steps'],'published_first_error':g,'prediction_first_error_fixed05':pr,'step_scores':p['step_scores'],'mechanically_observed_position_relation':position,'AI_semantic_judgment':None,'mechanism':'UNVERIFIED','independent_human_gold':None})
 save(out/'AI_FAILURE_REVIEW_QUEUE_PRIVATE.json',queue)
 ledgerfile=out/'FORWARD_LEDGER.jsonl';reserved=[__import__('json').loads(x) for x in ledgerfile.read_text().splitlines()] if ledgerfile.exists() else []
 cost={'reserved_trajectory_forwards':len(reserved),'reserved_step_scores':sum(x['steps'] for x in reserved),'successful_trajectories':valid,'returned_step_scores':returnedsteps,'actual_root_forward_attempts':summary.get('actual_root_forward_attempts'),'actual_input_tokens_successful':sum(p['input_tokens'] for p in pred if p['status']=='SUCCESS'),'GPU_worker_wall_seconds_including_hashing_loading':sup['wall_seconds'],'per_trajectory_GPU_synchronized_seconds_sum':sum(p.get('seconds',0) for p in pred if p['status']=='SUCCESS'),'paid_API_CNY':0,'training':False,'automatic_retry':False};save(out/'RESOURCE_COST.json',cost)
 freeze=load(ROOT/'config/sample_freeze.json');environment=load(out/'MODEL_ENVIRONMENT.json') if (out/'MODEL_ENVIRONMENT.json').exists() else {'status':'NOT_LOADED'}
 def report(name,text):(out/name).write_text(text.strip()+'\n')
 report('C1_THRESHOLD_PREREGISTRATION.md','# 项目阈值预注册\n\nC1_FIXED_THRESHOLD_SMOKE_APPROVED。阈值0.5，严格小于视为错误，等值通过，首错0起始，无错-1。所有分数先校验有限、非缺失、[0,1]，不预先四舍五入。无Gold调参、无阈值搜索。不是官方阈值复现。\n\n公开冻结合同见AUTHORIZATION_USED.json；原始预测冻结见PREDICTION_FREEZE.json。')
 report('C1_GPU_EXECUTION_AUDIT.md',f'# 实际执行审计\n\n{status}\n\n模型环境：\n```json\n{__import__("json").dumps(environment,ensure_ascii=False,indent=2)}\n```\n\n完整分母20，成功{valid}，返回步骤分数{returnedsteps}/112。每条完整轨迹最多一次forward；无生成/训练/自动重试。全部文件验证在RUNTIME_INPUT_AND_MODEL_SHA.json，加载源码SHA记录在环境文件；实际Token及步骤位置在RAW_TRAJECTORY_SCORES_PRIVATE.jsonl。\n\n先结束worker并冻结所有预测SHA，后由本CPU命令读取发布参考；顺序回执REFERENCE_COMPARISON_START.json。未执行新的独立AI裁决。')
 lines=['# 原始逐步分数','\n分数是作者dtype softmax的class1，不先行四舍五入，完整repr见JSON；表格文本精度只用于显示，预测使用原始浮点。']
 for p in pred:
  lines.extend([f'\n## {p["id"]} — {p["status"]}',f'\n固定0.5首错：{p["pred_first_error_fixed_05"]}'])
  if p['status']=='SUCCESS':
   lines.extend(['\n|step0起始|原始正类概率|','|---|---:|']);lines.extend(f'|{i}|{repr(v)}|' for i,v in enumerate(p['step_scores']))
  else:lines.append('\n无模型有效评分；不填充默认分数。')
 report('C1_PER_STEP_RAW_SCORES.md','\n'.join(lines))
 report('C1_FIXED05_RESULTS.md','# 项目固定0.5开发结果\n\n'+__import__('json').dumps(result,ensure_ascii=False,indent=2)+'\n\n首错准确率完整20分母；组内有错精确定位准确率、无错-1准确率及二者调和单列。混合20题调和不是原论文四子集均值，不能当同合同正式主表复现或与MiniCheckF1相比较。失败留在分母；没有任何有效评分时指标null而非伪造0分。')
 report('C1_AI_FAILURE_REVIEW.md',f'# AI辅助分歧审核待回传\n\n本轮有{len(queue)}个真实有效输出与发布参考不一致。这里只生成审阅队列，**未模拟AI审阅意见**。\n\nAI_FAILURE_REVIEW_QUEUE_PRIVATE.json保留原题、全部steps、原始分数及发布首错。过早/滞后是位置差异，不自动证明计算/逻辑/概念原因。请私下回传本包后由当前助手逐例审阅；语义尚未确定均UNVERIFIED，不修改发布Gold。')
 report('C1_RESOURCE_COST.md','# 资源账本\n\n```json\n'+__import__('json').dumps(cost,ensure_ascii=False,indent=2)+'\n```\n\nGPU_DEVICE_MEMORY是设备总峰值，可能包含其他进程；GPU_PROCESS_MEMORY是本Torch进程allocated/reserved峰值。每题输入Token、同步耗时和累积峰值保留。没有将加载/校验时间等同纯模型计算，未计量电费/租赁成本不等于总成本0。')
 report('C1_GATE_DECISION.md',f'# C1当前执行关口\n\n{status}\n\n这是固定0.5项目合同下的真实基线执行状态，不是官方阈值复现、新算法贡献或论文立项。AI语义审核待私下回传后完成；当前不能把所有分歧称模型数学错误。\n\n禁止扩大样本、重试、训练或开发新方法。完成后停止。')
 print(status);print('Reference comparison complete only after prediction freeze. AI review remains pending private return.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args();main(a)
