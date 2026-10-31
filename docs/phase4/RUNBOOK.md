# Phase 3 close-out → Phase 4 → Phase 5 runbook

All notebooks: Colab, A100 GPU, High-RAM; Colab Secrets `HF_TOKEN` and `OPENAI_API_KEY` (notebook access ON). Never paste keys into cells. If a cell stops, send the error; do not edit code (frozen code is hash-checked).

## A. Phase 3 revision and freeze — `notebooks/phase3/03_rte_v3_revalidation_and_freeze.ipynb` (branch `phase3-rte-v3-freeze`)
1. Offline tests (protocol, engine with mock API, statistics).
2. Build 400 dev RTE v3 jobs (proves 1,200/1,200 v2 prompts reproduced byte-for-byte).
3. GPT smoke 8 → full 400; Llama smoke 8 → full 400.
4. Analysis: v3 scores, 1,600 v2 ZS/OS outcomes re-verified, baseline recheck, **reliability gate**.
5. If the gate passed: S0 dev audit (2,991 segmentations exact; join rule exact; frozen fragment variant deterministic and >=95% exact vs saved dev; residuals disclosed), then declare the freeze.
6. Download the evidence ZIP → upload in chat → Report 3.2 (freeze package) → send to PI.
7. Commit `config/frozen/protocol_freeze.json` (from the ZIP) on branch `phase4-main` and push.

## B. Phase 4 — `notebooks/phase4/01_devtest_main_run.ipynb` (branch `phase4-main`)
S0 devtest (unsplit must equal the Phase 2 archive exactly) → 12,144 jobs → smoke (24 per model) → Llama full → GPT full by direction (Tier-1 daily cap ≈10,000 requests: may need two days; resume) → completion audit → evidence ZIP → Report 4.

## C. Phase 5 — `notebooks/phase5/01_evaluate_main.ipynb`
Statistics self-test → evaluation (F1/F2 Holm families, pools, over-editing, failure classes, flags) → tables + macros + figures → evidence ZIP → Report 5 and manuscript results.

## Acceptance conditions (from the approved plan)
Exactly 24 conditions × 1,012 unique IDs; source/reference alignment; non-empty final translation for every item (fallback labelled); no unresolved transport states; all records match the frozen run/config hashes; files reopened and checksummed; nothing scored before the freeze; references never in prompts.
