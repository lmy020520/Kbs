"""No GPU action without NEW R1 approval. This round only prepares this entry point."""
import sys,argparse,os,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from io_utils import *
from supervision import watch
from reporting import report

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval-file');p.add_argument('--data-dir');p.add_argument('--model-dir');p.add_argument('--gpu',type=int);a=p.parse_args()
    auth=authorization(a.approval_file)
    if auth['status']!='AUTHORIZED':print(__import__('json').dumps(auth));return 2
    verify_public()
    if not a.data_dir or not a.model_dir or a.gpu is None or not 0<=a.gpu<=7:raise RuntimeError('Explicit private data/model paths and one GPU required')
    verify_inputs(a.data_dir)
    run=ROOT/'results'/('contract_r1_'+auth['approval']['run_id'])
    if run.exists():raise RuntimeError('Run exists: no overwrites, no reset of budget, no automatic retry')
    run.mkdir(parents=True,mode=0o700);os.umask(0o077);write(run/'NEW_R1_APPROVAL.json',auth)
    try:
        gpu=subprocess.check_output(['nvidia-smi',f'--id={a.gpu}','--query-gpu=name,memory.free','--format=csv,noheader,nounits'],text=True).strip().split(',')
        if '3090' not in gpu[0] or int(gpu[1])<22000:raise RuntimeError('Require idle authorized RTX3090; no device fallback')
    except Exception as e:
        write(run/'PRECHECK_FAILURE.json',{'error':str(e),'GPU_worker_started':False});report(run);print('R1_RESOURCE_PRECHECK_FAILED');return 2
    env={**os.environ,'CUDA_VISIBLE_DEVICES':str(a.gpu),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','VLLM_USE_V1':'0','VLLM_WORKER_MULTIPROC_METHOD':'spawn','RAY_USAGE_STATS_ENABLED':'0','PYTHONDONTWRITEBYTECODE':'1','TOKENIZERS_PARALLELISM':'false','PYTHONPATH':str(ROOT/'src')}
    cmd=[sys.executable,str(ROOT/'src/r1_worker.py'),'--approval-file',str(Path(a.approval_file).resolve()),'--data-dir',str(Path(a.data_dir).resolve()),'--model-dir',str(Path(a.model_dir).resolve()),'--out',str(run)]
    with (run/'GPU_WORKER.log').open('w') as log:
        proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:supervision=watch(proc,run/'WORKER_STATE.json',wall_seconds=7200,generation_seconds=1200)
        except BaseException as e:
            write(run/'SUPERVISOR_FAILURE.json',{'error':str(e),'no_retry':True});supervision={'returncode':proc.poll(),'stop_reason':'SUPERVISOR_INTERRUPTED','wall_seconds':None}
    write(run/'SUPERVISION.json',supervision)
    # Freeze both predictions AND original calls/plans, strengthening the old archive contract.
    write(run/'PREDICTIONS_FROZEN.json',{'predictions':file_manifest(run/'predictions'),'calls':file_manifest(run/'calls'),'plans':file_manifest(run/'plans'),'no_reference_read':True})
    report(run);print('R1 GPU task ended. Separate scoring requires all three actual Join completions.')
    return 0 if supervision['returncode']==0 else 2
if __name__=='__main__':sys.exit(main())
