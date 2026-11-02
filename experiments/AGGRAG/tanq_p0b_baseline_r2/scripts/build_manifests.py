"""Packaging only; no experiments. Run locally before committing the new R2 version."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=list((ROOT/'src').glob('*.py'))+list((ROOT/'scripts').glob('*.py'))+list((ROOT/'config').glob('*.json'))+list((ROOT/'vendor').rglob('*.py'))+list(ROOT.glob('requirements*.txt'))
parts={str(p.relative_to(ROOT)):sha(p) for p in sorted(contract)};digest=hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest()
(ROOT/'CONTRACT_DIGEST.json').write_text(json.dumps({'version':'P0B_BASELINE_CONTRACT_REPAIR_R2','sha256':digest,'files':parts},indent=2)+'\n')
files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'results' not in p.parts and p.name!='PUBLIC_SHA256.json'}
(ROOT/'PUBLIC_SHA256.json').write_text(json.dumps({'files':files,'scope':'safe R2 code/config/UNIT_ONLY fixtures; no original corpus, Gold, raw calls or model weights'},indent=2)+'\n');print('R2 contract:',digest,'public files:',len(files))
