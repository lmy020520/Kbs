# ProcessBench C1 — project fixed0.5 smoke

Authorization: **C1_FIXED_THRESHOLD_SMOKE_APPROVED**. Exactly the original20 consumed development trajectories,112 steps,10228 CPU-preflight input tokens. This is a traditional baseline, not a new algorithm or author-threshold reproduction.

Decision: validate every score is finite and within[0,1]; return first zero-based score strictly below0.5. Equality passes. All pass→-1. Do not round, search thresholds, choose with Gold, change steps, replace cases or retry.

Model: Qwen/Qwen2.5-Math-PRM-7B revision0610740060112df12585d00a1c5f4624d2f59051. All16 required snapshot files, including4 weight shards, are pinned by SHA256. Model license is the Qwen agreement. No model code or weights/data/Gold are bundled in this public repository.

Prediction uses official fixed local custom AutoModel/AutoTokenizer files, after SHA verification. One complete trajectory forward yields every `<extra_0>` position's positive-class softmax probability. The original dtype softmax is retained; zeros are not discarded. Classification indexing is explicit, avoiding the model-card example's nonzero-flatten corner case. Raw two-class logits and probabilities are saved.

Execution adaptations: Python3.11; reuse the previously approved Torch2.6.0 / Transformers4.51.3 environment. CPU model loading then one explicit GPU transfer, BF16, eval/inference mode, no device_map/accelerate, no quantization/offload. `use_cache=False` for full-sequence classification, never prefix-cached scoring; no prompt or step changes. Record actual backend and source SHA; loading compatibility remains to be measured on the user server.

Planned resources: one free RTX3090, batch1. Authorization permits at most2, but this delivery selects1 only, never automatically switches GPUs or starts8-card execution. OOM/load/token mismatch stops. Each trajectory reserved before forward; exclusive authorization lock prevents re-running with a new output name. Worker3550-second watchdog plus bounded termination stays within3600-second GPU task limit. No warmup forward/generation or automatic retry.

## CPU verification

`python -m unittest discover -s tests -v` uses synthetic fixtures only; it does not load models. `python verify_public.py` checks this delivery's manifest. `preflight.py` checks fixed private inputs, full snapshot SHA and actual AutoTokenizer against all frozen prompts/Token IDs without initializing a model. It never opens evaluation references.

## Private input and model preparation

Privately transfer the separately supplied `C1_FIXED05_PRIVATE_INPUTS_20261103.tar.gz` to the server. Its `inputs/` files contain only the original question/steps and CPU expectations; `evaluation/` is read only by the separate post-freeze scorer. They must not be copied into this public directory or Git.

`download_snapshot.py` is a separate user-invoked downloader. It supports the official HuggingFace endpoint or hf-mirror.com, uses the same fixed official revision/hashes and single-attempt per file. Missing or partial/bad files stop; there is no model load or automatic retry. It does not modify historical model caches.

GPU command is `C1_GPU=0 bash run_server.sh` only after private data and model preflight prerequisites. Defaults:

- Python: `/home/lmingyang/lmyproject/aggrag_smoke_runtime/infer/bin/python`
- Data: `/home/lmingyang/lmyproject/processbench_c1_private_20261103`
- Model: `/home/lmingyang/lmyproject/processbench_models/Qwen2.5-Math-PRM-7B-06107400`
- Output: `results/c1_fixed05_dev20_20261103_01` in this delivered directory.

Override only resource paths via C1_PYTHON/C1_DATA/C1_MODEL and the selected single physical GPU via C1_GPU. These do not alter the frozen task/model. An existing output/preflight receipt or authorization state stops, it is never deleted automatically. Do not use reset --hard, clean, or delete old results to bypass a guard.

## Freeze and reference comparison

run_supervised.py ends the worker, saves complete20 status records (including failures), freezes all prediction artifacts and their SHA. Only the separate CPU `score_and_report.py` then opens evaluation/reference.json. Exact first-error accuracy uses all20. The ProcessBench-style harmonic of error-group exact accuracy and correct-trajectory accuracy is distinct from ordinary binary F1; the two-subset pilot must not be compared as the original four-subset official main-table reproduction.

The six requested reports and an additional cost report are generated. `C1_AI_FAILURE_REVIEW.md` is explicitly a pending review queue: this server code does not impersonate an AI reviewer. Transfer the private review archive back to Codex for source-based review of all real disagreements; unresolved mechanisms stay UNVERIFIED. Never auto-relabel Gold.

All raw questions/steps/prompts,Token IDs,step mappings,logits/probabilities,times,memory,failures,labels and hashes stay private. Export prints the private archive path/SHA and writes only an allowlisted aggregate sidecar. No automatic Git add/commit/push. Stop after smoke; no expansion/training/new algorithm.
