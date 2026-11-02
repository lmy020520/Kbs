"""Supervise only our process group; deadlines cannot be swallowed by CUDA code."""
import os,signal,time,subprocess
from pathlib import Path
from io_utils import load

def watch(proc,state_path,wall_seconds=7200,generation_seconds=1200,started=None,clock=time.monotonic,sleep=time.sleep,on_tick=None):
 start=clock() if started is None else started
 reason=None
 try:
  while proc.poll() is None:
   now=clock()
   if now-start>=wall_seconds:reason='TOTAL_WALL_TIMEOUT';break
   try:state=load(state_path)
   except (OSError,ValueError):state={}
   if state.get('phase')=='GENERATING' and now-state['at_monotonic']>=generation_seconds:reason='GENERATION_TIMEOUT';break
   if on_tick:on_tick()
   sleep(.25)
 finally:
  if True:  # Also clean up owned orphan workers after a normal driver exit.
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait()
 return {'returncode':proc.returncode,'stop_reason':reason,'wall_seconds':clock()-start,'includes_model_loading':True,'no_retry':True}
