"""SERVER ONLY: explicit authorized fixed official model, no alternate revisions."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True);p.add_argument('--authorized-server-download',action='store_true');a=p.parse_args()
 if not a.authorized_server_download:raise SystemExit('Explicit server download flag required; do not run locally')
 cfg=load(ROOT/'config/server_config.json');out=Path(a.model_dir).resolve()
 if out.is_relative_to(ROOT.parents[2]):raise SystemExit('Model cache must be outside code checkout')
 if out.exists() and any(out.iterdir()):raise SystemExit('Model directory nonempty; refuse mixing models/revisions')
 from huggingface_hub import HfApi,snapshot_download
 api=HfApi(token=False);info=api.model_info(cfg['model'],revision=cfg['revision'],files_metadata=True)
 if info.id!=cfg['model'] or info.sha!=cfg['revision']:raise RuntimeError('Official repository/revision verification failed')
 write(out/'../MODEL_REVISION_VERIFICATION.json',{'model':info.id,'revision':info.sha,'verified_at':time.time(),'method':'official Hugging Face API; token=False'})
 snapshot_download(repo_id=cfg['model'],revision=cfg['revision'],local_dir=out,token=False,allow_patterns=['*.json','*.safetensors','*.txt','*.model','LICENSE','README.md'])
 files={}
 for s in info.siblings:
  f=out/s.rfilename
  if not f.is_file():continue
  digest=sha(f)
  expected=(s.lfs.get('sha256') if isinstance(s.lfs,dict) else getattr(s.lfs,'sha256',None)) if s.lfs else None
  if s.rfilename.endswith('.safetensors') and not expected:raise RuntimeError('Official weight LFS SHA missing: '+s.rfilename)
  if expected and expected!=digest:raise RuntimeError('Official LFS SHA mismatch: '+s.rfilename)
  files[s.rfilename]=digest
 if not any(n.endswith('.safetensors') for n in files):raise RuntimeError('Missing model weights')
 write(out/'AGGRAG_MODEL_RECEIPT.json',{'model':info.id,'revision':info.sha,'files':files,'all_lfs_shas_verified':True,'method':'official fixed-revision snapshot, no remote model code executed'})
 print('Fixed official model downloaded and SHA-verified; no inference performed')
if __name__=='__main__':main()
