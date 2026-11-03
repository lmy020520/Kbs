"""Server-only single authorization run; watchdog, no retries, freeze before labels."""
import argparse,subprocess,os,sys,time,signal,threading,csv,traceback
from pathlib import Path
from contract import *
ROOT=Path(__file__).resolve().parent

def verify_public():
 m=load(ROOT/'PUBLIC_SHA256.json')
 for n,h in m.items():
  if sha(ROOT/n)!=h:raise ContractError('PUBLIC_CODE_SHA_MISMATCH '+n)

def inventory(gpu):
 raw=subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=index,uuid,name,memory.total,memory.free,memory.used,driver_version','--format=csv,noheader,nounits'],text=True,timeout=10)
 row=next(csv.reader(raw.splitlines()));idx,uuid,name,total,free,used,driver=[x.strip() for x in row]
 if 'RTX3090' not in name.replace(' ',''):raise ResourceError('Expected NVIDIA RTX3090')
 if int(free)<22000:raise ResourceError('Selected GPU not sufficiently free (need>=22000MiB); stop, no auto switch')
 return {'physical_index':idx,'uuid':uuid,'name':name,'total_MiB':int(total),'free_MiB':int(free),'before_used_MiB':int(used),'driver':driver}

def monitor(gpu,stop,out):
 peak=None;errors=[]
 while not stop.is_set():
  try:
   used=int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True,timeout=3).strip());peak=used if peak is None else max(peak,used)
  except Exception as e:errors.append(repr(e))
  stop.wait(.5)
 save(out/'GPU_DEVICE_MEMORY.json',{'device_peak_used_MiB':peak,'scope':'total selected device, may include other processes; not process-exclusive','monitor_errors':errors,'sampling_seconds':.5})

def main(a):
 verify_public();auth=load(ROOT/'config/authorization.json');check_authorization(auth);src,exp=verify_inputs(a.data,ROOT)
 out=Path(a.out)
 if out.exists():raise ContractError('Output directory exists: never overwrite/rerun')
 inv=inventory(a.gpu)
 # Exclusive authorization lock shared across code worktrees through the fixed private data root.
 AuthorizationLock(Path(a.data)/'state'/f'{auth["run_id"]}.USED.json').acquire(auth['run_id'])
 out.mkdir(parents=True);save(out/'AUTHORIZATION_USED.json',auth);save(out/'GPU_INVENTORY.json',inv)
 env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(a.gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1');stop=threading.Event();th=threading.Thread(target=monitor,args=(a.gpu,stop,out),daemon=True);th.start();process=None;reason=None;start=time.monotonic()
 try:
  with (out/'MODEL_RUNTIME.log').open('x') as log:
   process=subprocess.Popen([sys.executable,'-u',str(ROOT/'worker.py'),'--data',str(Path(a.data).resolve()),'--model',str(Path(a.model).resolve()),'--out',str(out.resolve())],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:process.wait(timeout=auth['worker_watchdog_seconds'])
   except subprocess.TimeoutExpired:reason='TOTAL_WALL_TIMEOUT';os.killpg(process.pid,signal.SIGTERM)
   except BaseException:reason='SUPERVISOR_INTERRUPTED';os.killpg(process.pid,signal.SIGTERM)
   if process.poll() is None:
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
 except BaseException as e:
  traceback.print_exc();reason=reason or repr(e)
  if process is not None and process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
 finally:
  stop.set();th.join(timeout=5)
  save(out/'SUPERVISION.json',{'worker_exit':process.returncode if process else None,'wall_seconds':time.monotonic()-start,'wall_limit_seconds':3600,'watchdog_seconds':auth['worker_watchdog_seconds'],'stop_reason':reason,'worker_has_ended':process is None or process.poll() is not None,'automatic_retry':False,'references_read':False})
  pp=out/'PREDICTIONS_PRIVATE.json';got=load(pp) if pp.exists() else [];by={x['id']:x for x in got}
  # Keep all20 denominator even on constructor/timeout failure. Do not invent scores.
  final=[by.get(s['id'],{'id':s['id'],'subset':s['subset'],'status':'NOT_RUN','step_scores':None,'pred_first_error_fixed_05':None,'reason':'WORKER_ENDED_BEFORE_SCORE'}) for s in src];save(pp,final)
  candidates=['AUTHORIZATION_USED.json','GPU_INVENTORY.json','GPU_DEVICE_MEMORY.json','SUPERVISION.json','PREDICTIONS_PRIVATE.json','RAW_TRAJECTORY_SCORES_PRIVATE.jsonl','FORWARD_LEDGER.jsonl','WORKER_SUMMARY.json','WORKER_FAILURE.json','WORKER_STATE.json','MODEL_ENVIRONMENT.json','GPU_PROCESS_MEMORY.json','RUNTIME_INPUT_AND_MODEL_SHA.json','INVALID_SCORE_RAW.json','MODEL_RUNTIME.log']
  m={n:sha(out/n) for n in candidates if (out/n).is_file()};save(out/'PREDICTION_FREEZE.json',{'files':m,'prediction_frozen_utc':utc(),'worker_has_ended':True,'published_reference_opened':False,'threshold':.5,'rule_origin':'PROJECT_PREREGISTRATION_NOT_OFFICIAL_THRESHOLD'})
  print('GPU worker ended; all raw/prediction SHA frozen before reference comparison.')
 return 0

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);p.add_argument('--gpu',type=int,default=0);a=p.parse_args()
 try:sys.exit(main(a))
 except Exception as ex:
  # Do not overwrite a previous run. An early preparation/resource failure starts no worker.
  target=Path(a.out)
  if not target.exists():
   target.mkdir(parents=True);save(target/'WRAPPER_START_FAILURE.json',{'status':'C1_RESOURCE_BLOCKED' if isinstance(ex,ResourceError) else 'C1_INPUT_CONTRACT_BLOCKED','error':repr(ex),'worker_started':False,'new_model_calls':0})
  raise
