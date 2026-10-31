import sys,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'PUBLIC_SHA256.json').read_text())
errors=[name for name,digest in m['files'].items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
if errors:raise SystemExit('Public source SHA failure: '+repr(errors))
print('Public code/config manifest verified:',len(m['files']),'files')
