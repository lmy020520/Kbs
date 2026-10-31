"""One-shot supervisor. No network inference; never retries or exceeds nine attempts."""
import argparse,sys,os,time,subprocess,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
from supervision import watch
from reporting import report

def main():
 p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--model-dir',required=True);p.add_argument('--out',default=str(ROOT/'results/server_smoke'));p.add_argument('--gpu',required=True,type=int);a=p.parse_args()
 if a.gpu<0 or a.gpu>7:raise SystemExit('Select exactly one physical authorized GPU index 0..7')
 run=Path(a.out).resolve()
 if run.exists():raise SystemExit('Run directory already exists; refuse overwrite/retry/reset of call budget')
 run.mkdir(parents=True,mode=0o700);os.umask(0o077)
 config=load(ROOT/'config/server_config.json')
 write(run/'MODEL_ENVIRONMENT.json',{'status':'NOT_LOADED','model':config['model'],'revision':config['revision']})
 write(run/'GPU_MEMORY_AUDIT.json',{'status':'NOT_STARTED','scope':'whole selected device samples, includes other processes; not attributed peak'})
 try:
  verify_inputs(a.data_dir)
  if not (Path(a.data_dir)/'evaluation/reference.jsonl').is_file():raise RuntimeError('SERVER_DATA_BLOCKED: private reference file absent; existence only, contents not read before prediction freeze')
 except Exception as e:
  write(run/'DATA_FAILURE.json',{'error':str(e)});print(report(run));return 2
 env={**os.environ,'CUDA_VISIBLE_DEVICES':str(a.gpu),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','VLLM_USE_V1':'0','VLLM_WORKER_MULTIPROC_METHOD':'spawn','RAY_USAGE_STATS_ENABLED':'0','TOKENIZERS_PARALLELISM':'false','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
 # No automatic GPU choice or eviction of other workloads.
 try:
  gpu=subprocess.check_output(['nvidia-smi',f'--id={a.gpu}','--query-gpu=name,memory.total,memory.free','--format=csv,noheader,nounits'],text=True).strip().split(',')
  if '3090' not in gpu[0] or int(gpu[1])<23000 or int(gpu[2])<22000:raise RuntimeError('Need an idle authorized RTX3090 with >=22000MiB free; no fallback GPU/model')
 except Exception as e:
  write(run/'WORKER_FAILURE.json',{'error':str(e),'phase':'GPU_INVENTORY'});print(report(run));return 2
 samples=[];last=[0.0]
 def sample():
  if time.monotonic()-last[0]<1:return
  last[0]=time.monotonic()
  try:
   v=subprocess.check_output(['nvidia-smi',f'--id={a.gpu}','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],text=True,timeout=2).strip().split(',');samples.append({'at_monotonic':last[0],'used_MiB':int(v[0]),'free_MiB':int(v[1])})
  except Exception as e:samples.append({'at_monotonic':last[0],'sampling_error':str(e)})
 cmd=[sys.executable,str(ROOT/'src/gpu_worker.py'),'--data-dir',str(Path(a.data_dir).resolve()),'--model-dir',str(Path(a.model_dir).resolve()),'--run-dir',str(run)]
 start=time.monotonic()
 with (run/'GPU_WORKER.log').open('w') as log:
  proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:supervised=watch(proc,run/'WORKER_STATE.json',wall_seconds=7200,generation_seconds=1200,started=start,on_tick=sample)
  except BaseException as e:
   write(run/'SUPERVISOR_FAILURE.json',{'error':str(e),'no_retry':True});supervised={'returncode':proc.poll(),'stop_reason':'SUPERVISOR_INTERRUPTED','wall_seconds':time.monotonic()-start}
 write(run/'SUPERVISION.json',supervised)
 write(run/'GPU_MEMORY_AUDIT.json',{'GPU_index':a.gpu,'samples':samples,'sampled_device_peak_used_MiB':max((x['used_MiB'] for x in samples if 'used_MiB' in x),default=None),'scope':'whole GPU includes unrelated processes; current-process torch peaks are separately in each returned call','model_load_memory':load(run/'GPU_LOAD_MEMORY.json') if (run/'GPU_LOAD_MEMORY.json').exists() else None})
 # Freeze complete/partial predictions before any scorer may open private Gold.
 write(run/'PREDICTIONS_FROZEN.json',{'files':prediction_manifest(run),'at':time.time(),'calls':len(load(run/'CALL_LEDGER.json')['attempts']) if (run/'CALL_LEDGER.json').exists() else 0,'scope':'no Gold read in prediction worker'})
 print(report(run));print('GPU task stopped; scoring is a separate CPU-only command')
 return 0 if supervised.get('returncode')==0 else 2
if __name__=='__main__':sys.exit(main())
