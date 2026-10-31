# Pinned environments (isolated venvs; never one combined stack)

| File | Used for | Python |
|---|---|---|
| `llama_gpt.txt` | vLLM Llama generation, GPT AsyncOpenAI generation, offline tests | 3.11 |
| `evaluation.txt` | COMET/BLEU/chrF++, statistics, flags, figures, freeze builder | 3.11 (torch from cu124 index) |
| `retrieval.txt` | LaBSE/FAISS job preparation | 3.11 (torch from cu124 index) |
| `nllb.txt` | NLLB-200 3.3B baseline generation, splitter gates | 3.13 (torch from cu130 index) |

Install exactly as in the notebooks (`uv pip install --python <venv> -r <file>`; install torch first from the indicated index). Each run also saves `requirements_resolved.txt` with the full resolved set.

## Resolved lock files (collected 31 October 2026 with `notebooks/phase5/02_collect_environment_locks.ipynb`)

| Lock file | Environment | Coverage |
|---|---|---|
| `llama_gpt.lock.txt` | Held-out Llama and GPT-4o Mini runs | Exact resolved set of the Phase 4 run (identical for both editors) |
| `retrieval.lock.txt` | LaBSE/FAISS | Exact resolved set of the last pilot retrieval run; Phase 4 did not save its own set, but its embeddings reproduced the pilot matrices exactly |
| `evaluation.lock.txt` | COMET/BLEU/chrF++ | Exact resolved set of the pilot evaluation; Phase 5 added `rapidfuzz==3.10.1` and `pysbd==0.3.4` |
| `nllb.txt` only | NLLB-200 | No resolved set was saved; versions are recorded in `docs/phase4/evidence/s0_run_spec.json` (Python 3.13.16, torch 2.11.0+cu130, transformers 5.18.0) |

All source files found on Drive (`*requirements*resolved*.txt`):

| Drive path | Lines | SHA-256 |
|---|---|---|
| `outputs/generations/baselines/phase3_dev_f4a3af94ba1e72fd/evaluation/6d6e94fc2a8d3d8f/requirements_resolved.txt` | 80 | `8a8f5a698bac7b7c…` |
| `outputs/phase3_post_editing/candidate_906a8b8123bb3a54/llama_runs/e7656ef4b245e2aa/requirements_llama_resolved.txt` | 170 | `a20fdcac284c274e…` |
| `outputs/phase3_post_editing/candidate_906a8b8123bb3a54/pilot_analysis/9d6830a0b9c7cc97/requirements_evaluation_resolved.txt` | 69 | `ddf168e002159835…` |
| `outputs/phase3_post_editing/candidate_906a8b8123bb3a54/requirements_retrieval_resolved.txt` | 67 | `fd8100b86cfb72a8…` |
| `outputs/phase3_post_editing/candidate_95c7d9af123cd688/llama_runs/9390cd03839285c0/requirements_llama_resolved.txt` | 170 | `5c0fc1e822122083…` |
| `outputs/phase3_post_editing/candidate_95c7d9af123cd688/llama_runs/befab877cbe2f695/requirements_llama_resolved.txt` | 170 | `2102941585e21c7f…` |
| `outputs/phase3_post_editing/candidate_95c7d9af123cd688/requirements_retrieval_resolved.txt` | 67 | `40951efba3bdca3a…` |
| `outputs/phase3_post_editing/rte_v3_1b3d3273cdbf0c29/runs/gpt4o-mini/55a41d001ca33ffd/requirements_resolved.txt` | 170 | `6b21f829544ef538…` |
| `outputs/phase3_post_editing/rte_v3_1b3d3273cdbf0c29/runs/llama3-8b/14ddbd410fa1775f/requirements_resolved.txt` | 170 | `6b21f829544ef538…` |
| `outputs/phase4/main_prepared/main_adb98f4e942e213b/runs/gpt4o-mini/eb319d52dbcbe4fe/requirements_resolved.txt` | 170 | `041482f847e63743…` |
| `outputs/phase4/main_prepared/main_adb98f4e942e213b/runs/llama3-8b/1c9083d0022e90d1/requirements_resolved.txt` | 170 | `041482f847e63743…` |
