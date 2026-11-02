import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from io_utils import verify_public
verify_public();print('R2 public code/config SHA verification PASS')
