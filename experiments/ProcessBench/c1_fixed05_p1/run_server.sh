#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE=/home/lmingyang/lmyproject
PY=${C1_PYTHON:-$BASE/aggrag_smoke_runtime/infer/bin/python}
DATA=${C1_DATA:-$BASE/processbench_c1_private_20261103}
MODEL=${C1_MODEL:-$BASE/processbench_models/Qwen2.5-Math-PRM-7B-06107400}
GPU=${C1_GPU:-0}
RUN="$ROOT/results/c1_fixed05_dev20_20261103_01"
ARCHIVE="$BASE/C1_FIXED05_SERVER_REVIEW_PRIVATE_20261103.tar.gz"
export PYTHONDONTWRITEBYTECODE=1
"$PY" "$ROOT/verify_public.py"
# No automatic dependency install or model download. Use separate preparation commands.
CUDA_VISIBLE_DEVICES='' "$PY" "$ROOT/preflight.py" --data "$DATA" --model "$MODEL" --out "$ROOT/CPU_PREFLIGHT_RECEIPT.json"
"$PY" "$ROOT/run_supervised.py" --data "$DATA" --model "$MODEL" --out "$RUN" --gpu "$GPU"
# Separate process; first allowed label open is inside this post-freeze CPU scorer.
CUDA_VISIBLE_DEVICES='' "$PY" "$ROOT/score_and_report.py" --data "$DATA" --out "$RUN"
CUDA_VISIBLE_DEVICES='' "$PY" "$ROOT/export_private.py" --data "$DATA" --out "$RUN" --archive "$ARCHIVE"
printf '%s\n' 'Stopped. No retry, expansion, training, extra model or automatic Git upload.'
