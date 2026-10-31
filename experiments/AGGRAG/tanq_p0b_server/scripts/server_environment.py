"""Server inventory only, no CUDA allocation or model loading."""
import sys,os,json,platform,subprocess,importlib.metadata as m
if platform.system()!='Linux' or platform.machine()!='x86_64' or sys.version_info[:2]!=(3,11):raise SystemExit('Use Linux x86_64 Python3.11 isolated env matching the lock')
r={'python':sys.version,'platform':platform.platform(),'glibc':platform.libc_ver(),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'GPU_inference_executed':False}
for label,cmd in [('gpu',['nvidia-smi']),('memory',['free','-h']),('disk',['df','-h','.'])]:
 x=subprocess.run(cmd,capture_output=True,text=True);r[label]={'returncode':x.returncode,'stdout':x.stdout,'stderr':x.stderr}
print(json.dumps(r,indent=2))
