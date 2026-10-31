# LLM post-editing of NMT for English–Tagalog and English–Spanish

Held-out evaluation of whether large language models help or harm when they post-edit strong neural machine
translation drafts. Four directions (En→Tl, Tl→En, En→Es, Es→En) on FLORES+ `devtest` (1,012 sentences each);
a sentence-split NLLB-200 3.3B baseline (S0); two editors (Llama 3 8B Instruct, GPT-4o Mini) × three prompting
strategies (zero-shot, retrieved one-shot, single-call reason-then-edit) = 24 conditions, 24,288 outputs.
The protocol was frozen on development data before `devtest` was opened.

> **Anonymous review.** The manuscript is under anonymous submission. Benchmark text and model outputs are not in
> this repository; only code, prompts, frozen configuration and numeric evidence are.

## Results at a glance

ΔCOMET-22 (points, condition − S0; `*` = significant after Holm correction over 24 tests). S0 COMET: En→Tl 85.20 · Tl→En 87.57 · En→Es 86.67 · Es→En 87.37.

| Editor | Strategy | En→Tl | Tl→En | En→Es | Es→En |
|---|---|---|---|---|---|
| GPT-4o Mini | zero-shot | +0.64* | +0.83* | +0.28* | +0.34* |
| GPT-4o Mini | retrieved one-shot | +0.95* | +1.00* | +0.53* | +0.36* |
| GPT-4o Mini | reason-then-edit | +0.51* | +0.65* | +0.26* | +0.27* |
| Llama 3 8B Instruct | zero-shot | -0.48* | -0.10 | +0.00 | -0.01 |
| Llama 3 8B Instruct | retrieved one-shot | -0.39* | +0.03 | +0.18 | -0.04 |
| Llama 3 8B Instruct | reason-then-edit | -1.44* | -1.32* | -0.51* | -0.74* |

Over-editing: strong drafts (S0 COMET ≥ 0.90) whose text changed and lost more than 0.02 COMET:

* GPT-4o Mini zero-shot: 10 / 1,179 (0.8%)
* GPT-4o Mini retrieved one-shot: 51 / 1,179 (4.3%)
* GPT-4o Mini reason-then-edit: 25 / 1,179 (2.1%)
* Llama 3 8B Instruct zero-shot: 132 / 1,179 (11.2%)
* Llama 3 8B Instruct retrieved one-shot: 133 / 1,179 (11.3%)
* Llama 3 8B Instruct reason-then-edit: 247 / 1,179 (20.9%)

Full tables: `docs/phase5/Norris_Phase_Report_5.pdf`; robustness analyses: `docs/phase5/Norris_Phase_Report_5_1.pdf`.

## Status

| Phase | Status | Evidence |
|---|---|---|
| 1–2 Data and NLLB baselines | Complete | `docs/phase3/`, `notebooks/phase2_nllb_baselines.ipynb` |
| 3 Development pilots, contract revision, protocol freeze | Complete; approved | `docs/phase3/Norris_Phase_Report_3_2.pdf`, `config/frozen/protocol_freeze.json` |
| 4 Held-out generation (24,288 outputs, 0 fallbacks) | Complete; approved | `docs/phase4/Norris_Phase_Report_4.pdf`, `docs/phase4/evidence/` |
| 5 Evaluation, tests, over-editing, case inspection | Complete; approved | `docs/phase5/Norris_Phase_Report_5.pdf`, `docs/phase5/evidence/` |
| 5.1 Exploratory robustness analyses | Complete | `docs/phase5/Norris_Phase_Report_5_1.pdf`, `docs/phase5/evidence/extended/` |
| Manuscript (IEEEtran, 5 pages, anonymous) | Draft; audited | `paper/` |

PI decisions are recorded in `docs/PI_DECISIONS_2026-10-31.md`; the schedule is in `docs/SCHEDULE_AND_REPORTS.md`.

## Repository map

| Path | Contents |
|---|---|
| `config/frozen/protocol_freeze.json` | Frozen protocol: research questions, prompts, schemas, model revisions, decoding, statistics, code hashes |
| `config/environments/` | Pinned top-level requirements for the four isolated environments |
| `src/baselines/` | Sentence splitter and S0 generation (frozen) |
| `src/post_editing/` | Job preparation and execution engine (frozen) |
| `src/common/norris_protocol.py` | Prompts, schemas and output contract (frozen) |
| `src/evaluation/` | Phase 5 evaluator and paired-bootstrap statistics (frozen) |
| `src/analysis/` | Figures, case-selection rules, manuscript facts, exploratory analyses (`phase5_extended.py`) |
| `notebooks/phase3/`, `phase4/`, `phase5/` | Colab notebooks that ran each phase |
| `docs/phase*/` | Phase reports and numeric evidence |
| `paper/` | Manuscript sources, generated tables, claims manifest, reviewer memo, submission checklist |
| `scripts/` | Manuscript and public-file audits |
| `tests/` | Offline tests for the frozen protocol, engine, statistics and analyses |

## Environments

Each stage ran in its own Python 3.11 virtual environment on a Colab A100 (NLLB: Python 3.13), created with `uv`.
Top-level pins are in `config/environments/{nllb,retrieval,llama_gpt,evaluation}.txt`; the fully resolved set for the
held-out editors is `docs/phase4/evidence/llama_gpt_env_requirements_resolved.txt`. Key versions: vLLM 0.11.2,
openai 1.109.1, unbabel-comet 2.2.7 (`Unbabel/wmt22-comet-da` @ 2760a223), sacrebleu 2.6.0, transformers 4.49.0
(evaluation).

## Reproducing the study

1. **Development and freeze:** `notebooks/phase3/03_rte_v3_revalidation_and_freeze.ipynb` (dev only).
2. **Held-out generation:** `notebooks/phase4/01_devtest_main_run.ipynb` (needs `HF_TOKEN`, `OPENAI_API_KEY` in Colab Secrets).
3. **Evaluation:** `notebooks/phase5/01_evaluate_main.ipynb` (COMET, BLEU, chrF++, both Holm families, figures, tables).
4. **Exploratory analyses (no GPU, no text):** `python src/analysis/phase5_extended.py`.
5. **Manuscript tables:** written by the evaluator into `paper/generated/` (never edited by hand).

Notebooks clone the branch named in their first cell and verify the frozen code hashes before running.

## Verifying the committed evidence (CPU, a few seconds)

```
pip install pydantic==2.12.3            # for the protocol module
python scripts/audit_manuscript.py        # RQs, anonymity, 79 held-out claims, generated tables
python scripts/audit_public_files.py      # no secrets, benchmark text or generations
python tests/frozen/test_protocol.py
python tests/phase5/test_stats.py
python tests/phase5/test_extended.py
```

## What is not published, and why

FLORES+ sentences, NLLB drafts, LLM outputs, embeddings and the private case-review file stay on the project's
private Drive: redistributing benchmark text and model generations is outside the release policy. API keys are never
committed. Numeric evidence (scores, counts, hashes, statistics) is public and sufficient to verify every reported number.

## Changelog

* **2026-10-31** PI decisions applied: anonymous manuscript, S0 disposition documented, case review strictly
  source/reference-based, Conclusions and Future Work; README rewritten; anonymity check added to the audit.
* **2026-10-30** Report 5.1: exploratory robustness analyses; RQ1 wording corrected.
* **2026-10-25** Phase 5 complete; source-based review of 96 rule-selected cases.
* **2026-10-24** Protocol frozen; Phase 4 held-out generation complete.
* **2026-10-17 to 23** Phase 3 pilots, reason-then-edit contract revision.

The previous long-form README is archived in `docs/archive/README_through_2026-10-30.md`.
