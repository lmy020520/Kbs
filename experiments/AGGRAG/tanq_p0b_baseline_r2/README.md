# TANQ traditional baseline R2 — offline repair only

Independent successor to frozen `../tanq_p0b_contract_r1`; no original result is replaced.

Start with `R2_CONTRACT.md`, `R2_GATE_DECISION.md`, and the explicitly **unapproved** resource request in `R2_SERVER_RUNBOOK.md`.

CPU tests: `python -m unittest discover -s tests -v` after installing `requirements-cpu.lock.txt` in an isolated environment. No model/GPU imports occur in CPU validation. Official scorer smoke uses `requirements-evaluation.full.lock.txt` in a separate CPU environment and fictional fixtures only.

`python scripts/run_server_r2.py` without a fresh owner approval stops before CUDA/model import. Existing R0/R1 approvals are invalid. No inference was performed to prepare this version.

Public files include only code, synthetic fixtures, frozen sample IDs and integrity hashes. Private evidence/reference files stay outside this directory. Results are private and must never be committed. There are no natural performance scores here.
