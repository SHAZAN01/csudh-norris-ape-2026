# Norris Research Project

## LLM post editing for English–Tagalog and English–Spanish translation

**Principal investigator:** Dr. Benyamin Ahmadnia  
**Graduate research assistant:** Shazan Ansar Mohammed  
**Institution:** California State University, Dominguez Hills  
**Program:** Norris Research Program, Fall 2026  
**Progress snapshot:** 19 October 2026

The sentence-split development baseline, actual LaBSE retrieval, Llama smoke run,
and full Llama/GPT development pilots are complete. The same 100 aligned dev IDs
produce **2,400 outcomes across four directions, three strategies and two editors**.
All 24 condition summaries, fallback decisions and retrieval links were audited.
**Phase 3 remains open: protocol freeze and PI sign-off are pending.** Main devtest
experiments have not started. The manuscript in `paper/` reports development only.

GPT retrieved one-shot gains +1.463 COMET points into Tagalog (descriptive dev
95% interval [+0.710, +2.396]). Llama reason-then-edit uses baseline fallback on
227/400 outcomes, versus 8/400 for GPT. These failures remain in the results.
The ICAI overlap review discloses shared anchoring/retrieval methods and positions
Norris as an empirical extension; it is brought to the PI before freeze.

## Read first

- [Phase Report 3 PDF](docs/phase3/Norris_Phase_Report_3.pdf)
- [Editable Word report](docs/phase3/Norris_Phase_Report_3.docx)
- [Report source in Markdown](docs/phase3/Norris_Phase_Report_3.md)
- [Execution runbook and acceptance criteria](docs/phase3/RUNBOOK.md)
- [Machine readable development metrics](docs/phase3/evidence/evaluation/dev_baseline_metrics.json)
- [Candidate status manifest](config/phase3/status.json)
- [Metric interpretation notes](docs/phase3/NUMERICAL_NOTES.md)
- [ICNLP development manuscript PDF](paper/Norris_ICNLP_Development_Draft.pdf)
- [Manuscript source and compilation guide](paper/README.md)
- [Specific decisions before freeze](docs/phase3/PROTOCOL_DECISIONS_PENDING.md)

## What is complete

| Work item | Current state |
|---|---|
| Split/unsplit dev baseline | Complete: 997 items per direction and condition |
| Dev retrieval preparation | Complete: three LaBSE indexes; all 400 pilot links checked |
| Llama smoke/full pilot | Complete: 24 smoke outcomes accounted for within the 1,200 full outcomes |
| GPT-4o Mini pilot | Complete: 1,200 outcomes with the exact dated snapshot |
| Quality and failure analysis | Complete: all 24 conditions, failures and preservation screens |
| ICAI comparison | Complete; PI review before freeze pending |
| Report 3 | Updated PDF, DOCX and Markdown with measured results |
| Manuscript | Modular IEEEtran development draft, pilot tables and source verification |
| Protocol freeze / Phase 3 acceptance | Pending PI decisions and final configuration record |
| Main devtest experiment / analysis | Future Phases 4 and 5; not executed |

## Study design and data boundaries

FLORES+ is the dataset used in the completed baseline workflow. The four
directions are `eng_Latn → tgl_Latn`, `tgl_Latn → eng_Latn`,
`eng_Latn → spa_Latn` and `spa_Latn → eng_Latn`.

The dataset's Tagalog configuration is **`fil_Latn`**; NLLB's Tagalog language
code is **`tgl_Latn`**. These identifiers serve different interfaces. Do not use
`tag_Latn` as an interchangeable replacement.

| Partition | IDs per direction | Permitted use |
|---|---:|---|
| dev | 997 | Baseline diagnosis, prompt development, retrieval and pilot selection |
| devtest | 1,012 | Main experiment and evaluation after the Phase 3 freeze |

Phase 2 generated older devtest baseline outputs, which remain separate and
unscored. This does not authorize devtest inspection during Phase 3. All current
development, retrieval and pilot decisions use dev only.

The study uses standard Spanish. It does not establish findings about heritage
Spanish, Los Angeles dialects or code switching. No external human raters are
included, following the PI's September 24 feedback. TRACE MT and the separate
ICAI work remain outside this implementation and its result claims.

## Phase 3 baseline methodology

### Sentence segmentation

The primary baseline uses independent translation of source sentence fragments
followed by rejoining their translations with one space. The original unsplit
baseline is retained as a diagnostic condition, as approved by the PI.

The final segmentation candidate uses `pysbd==0.3.4`, `clean=False` and character
spans. English and Spanish use their corresponding rule sets. Tagalog uses
English rules as a documented heuristic. Before generation, concatenating each
item's source segments must recover every original character and whitespace
exactly. This check establishes lossless source segmentation, not guaranteed
translation completeness or cross sentence consistency.

| Source language | Items | Multi sentence items | Total fragments |
|---|---:|---:|---:|
| English | 997 | 104 | 1,104 |
| Tagalog | 997 | 104 | 1,104 |
| Spanish | 997 | 109 | 1,109 |

The Spanish `Jr.` safeguard corrected IDs 31 and 159 in candidate v2. Candidate
v3 then changed exactly seven reviewed source language items relative to v2:
English 187, 641 and 960; Tagalog 641, 956 and 960; Spanish 641. These corrections
address a clock abbreviation before a weekday, the Tagalog abbreviation `atbp.`
and detached parenthetical or citation continuations. All 12 synthetic boundary
tests passed before the full run.

### Generation controls

| Setting | Completed baseline run |
|---|---|
| Model | `facebook/nllb-200-3.3B` |
| Precision | FP16 |
| Batch size | 32 |
| Decoding | Four beams; no sampling; early stopping |
| Length settings | `max_length=512`; length penalty 1.0 |
| Input handling | No silent truncation; maximum input length checked |
| Conditions | Current unsplit control and sentence split |

For single segment sources, the split condition reuses the current control
hypothesis. Multi sentence fragments require additional inference. All 3,988
current unsplit hypotheses exactly matched the archived Phase 2 hypotheses:
997 matches per direction and zero differences. A previous small smoke run had
one mismatch; the full control reproduced the archive, but does not isolate
the cause of that earlier mismatch.

## Verified dev results

Each condition contains **997 items per direction**. COMET 22 is primary; BLEU
and chrF++ are secondary. COMET is displayed as **native score × 100**. The
tables are generated from the saved full precision metric JSON.

| Direction | Condition | BLEU | chrF++ | COMET |
|---|---|---|---|---|
| English → Tagalog | Unsplit control | 35.436 | 60.054 | 84.735 |
| English → Tagalog | Sentence split | 35.820 | 60.665 | 85.086 |
| Tagalog → English | Unsplit control | 50.806 | 69.374 | 87.734 |
| Tagalog → English | Sentence split | 50.641 | 69.495 | 87.787 |
| English → Spanish | Unsplit control | 27.924 | 53.484 | 86.171 |
| English → Spanish | Sentence split | 28.231 | 53.913 | 86.463 |
| Spanish → English | Unsplit control | 32.882 | 59.306 | 87.400 |
| Spanish → English | Sentence split | 32.949 | 59.713 | 87.543 |

### Paired COMET differences

Differences below are **sentence split minus current unsplit**, in reported
COMET points. Confidence intervals use 10,000 paired percentile bootstrap
resamples with seed 42. They are descriptive dev diagnostics, not confirmatory
main experiment tests. No multiplicity adjusted significance claim is made.

| Direction | All item delta | 95% interval | Multi n | Multi delta | Multi 95% interval |
|---|---|---|---|---|---|
| English → Tagalog | +0.351 | [+0.216, +0.497] | 104 | +3.363 | [+2.197, +4.607] |
| Tagalog → English | +0.053 | [-0.019, +0.130] | 104 | +0.508 | [-0.186, +1.233] |
| English → Spanish | +0.292 | [+0.143, +0.448] | 104 | +2.797 | [+1.475, +4.224] |
| Spanish → English | +0.142 | [+0.061, +0.232] | 109 | +1.301 | [+0.575, +2.069] |

The intervals for English to Tagalog, English to Spanish and Spanish to English
are positive and exclude zero. The Tagalog to English interval includes zero;
its positive point estimate is inconclusive, and its BLEU decreases slightly.
This is neither proof of no effect nor an equivalence finding.

Larger multi sentence effects localize the observed change to the subset
exposed to segmentation. They do not mean every output improved. The approved
split baseline remains primary, with the unsplit condition retained for diagnosis.

### Textual changes and score change bands

An increase is native COMET delta **> +0.02**, a decrease is **< −0.02**, and
the middle band includes both endpoints. The threshold corresponds to
**2 reported COMET points**, not 0.02 reported points.

| Direction | Text changed | Increase | Within band | Decrease |
|---|---|---|---|---|
| English → Tagalog | 96 | 41 | 949 | 7 |
| Tagalog → English | 93 | 19 | 968 | 10 |
| English → Spanish | 85 | 33 | 955 | 9 |
| Spanish → English | 103 | 27 | 961 | 9 |

Across all directions, 377 hypotheses changed and 3,611 were textually identical.
The score bands contain 120 increases, 3,833 within band and 35 decreases.
Of the changed hypotheses, 222 fall within the score band. A score within the
band must not be described as an unchanged translation or guaranteed harmless edit.
These baseline changes are not LLM over editing rates.

### Baseline pools for later pilot diagnostics

| Direction | Native COMET < 0.80 | Native COMET ≥ 0.90 |
|---|---|---|
| English → Tagalog | 187 | 237 |
| Tagalog → English | 75 | 387 |
| English → Spanish | 119 | 277 |
| Spanish → English | 53 | 283 |

These are counts over the full dev split baseline, not pilot measurements or
human quality judgments. The pilot sample is balanced by direction and strategy,
not stratified by these score pools.

## Compute and evaluation accounting

- Generation saved **7,976 final records**: 997 × four directions × two conditions.
  This is not the number of independently inferred model sequences.
- Logged inference totaled **368.06 seconds**; invocation wall time was
  **381.06 seconds**, approximately 6 minutes 21 seconds, on an A100 80 GB.
  Earlier model download and loading are excluded.
- Evaluation scored 3,988 unsplit triplets and only the 377 changed split
  triplets: **4,365 triplets**, with scores reused for identical source,
  hypothesis and reference inputs.
- Original COMET scores were reproduced exactly in all four directions.
- Batch amortized time is distinct from isolated request latency.

BLEU uses mixed case, 13a tokenization and exponential smoothing. chrF++ uses
character order 6, **word order 2**, and beta 2. Earlier role text mentioning
word order 1 is superseded by this recorded configuration.

The numeric evidence audit recomputes whole-dev COMET means, paired intervals,
change bands and configuration/cache hashes. The supplied evaluation evidence
does not include raw translation JSONL files, so BLEU and chrF++ have not been
independently rescored in this audit. Their values and signatures come from the
provenance checked Colab evaluator. Multi sentence membership cannot be
independently reconstructed from the numeric caches alone.

## Candidate post editing system

**Measured prompt version:** `candidate_v2_explicit_diagnostics_not_frozen`.

| Strategy | Model context | Required response |
|---|---|---|
| Zero shot | Source, target language and NLLB draft | `edited_translation` |
| Retrieved one shot | Same query plus one solved nonpilot dev demonstration | `edited_translation` |
| Reason then edit | Source, target language and NLLB draft | `diagnostics`, followed by `edited_translation` |

All prompts use the source as the authority, preserve meaning and source
supported names/numbers/dates, and discourage stylistic rewriting. An accurate,
natural and grammatical draft should be returned unchanged. Source and draft
strings are data, not instructions. The implementation never claims prompt
instructions alone guarantee semantic correctness or entity preservation.

The six diagnostic categories are `MISTRANSLATION`, `OMISSION`,
`UNSUPPORTED_ADDITION`, `MORPHOSYNTAX_MISMATCH`, `NAMED_ENTITY_CORRUPTION`
and `NONE`. Each brief note is limited to 25 words; labels cannot repeat and
`NONE` must appear alone. Diagnostics are observable error summaries, not long
reasoning transcripts.

vLLM constrains JSON structure during generation. Pydantic performs strict
post generation validation, including cross field rules. JSON parsing, schema
validity and usable completion are recorded separately. A truncated response
may parse and validate structurally while still being unusable. Invalid or
unfinished responses retain raw evidence and fall back to the baseline, without
selective response repair.

### Retrieval and reference isolation

The builder uses `sentence-transformers/LaBSE` to create normalized float32
embeddings, 768 dimensions, and exact FAISS `IndexFlatIP` indexes over 997 dev
sources per source language. Top 1 selection uses cosine similarity and a
deterministic sentence ID tie break. No independent syntactic similarity claim
is made.

A seed 42 uniform sample selects 100 aligned dev IDs, reused in every direction
and strategy. **All 100 pilot IDs are excluded from every demonstration pool**,
leaving 897 candidate IDs before exact duplicate source exclusion. Current query
references and baseline metric scores never enter prompts. Only the retrieved
nonpilot demonstration may expose its own gold dev translation. Pilot gold
references are stored separately for offline evaluation.

The completed preparation saved three embedding arrays and indexes,
corpus maps, 400 retrieval links, 400 offline evaluation rows and 1,200 Llama
jobs, with checksums. These outputs are present in the returned full-pilot evidence bundle; all
400 links were independently reconstructed during report review.

### Candidate Llama settings

| Setting | Candidate value |
|---|---|
| Model | `meta-llama/Meta-Llama-3-8B-Instruct` |
| Model revision | `8afb486c1db24fe5011ec46dfbe5b5dccdb575c2` |
| Precision | BF16; no quantization |
| Sampling | Temperature 0; top_p 1; top_k −1; seed 42 |
| Output cap | 1,024 tokens |
| Context limit | 8,192 tokens, checked before generation |
| vLLM | 0.11.2; up to 16 sequences; GPU utilization 0.70 |
| Startup | Eager execution and prefix caching enabled |
| Chat rendering | Model template with consistency checks against input token IDs |
| Resumption | Configuration, prompt job and completed record hashes validated |

Llama 3.1 is not a silent replacement for the specified Llama 3 model. Model
access failure stops preparation. Gated Hugging Face access uses Colab Secrets
and is never stored in notebook source.

## Code and artifact map

| Path | Purpose |
|---|---|
| `notebooks/phase3/01_resume_dev_evaluation.ipynb` | Validate and reuse saved baseline evaluation |
| `notebooks/phase3/02_prompts_retrieval_llama.ipynb` | Prepare retrieval and run the Llama smoke stage |
| `src/phase3/evaluation/evaluate_dev_baselines.py` | Current resume evaluator |
| `src/phase3/post_editing/pilot_common.py` | Prompts, schemas, selection rules and response validation |
| `src/phase3/post_editing/prepare_pilot.py` | Dev retrieval preparation and job construction |
| `src/phase3/post_editing/run_llama_pilot.py` | Smoke/full generation, raw evidence and checkpoints |
| `src/phase3/post_editing/baseline_io.py` | Baseline validation snapshot shared with pilot preparation |
| `tests/phase3/test_pilot.py` | Synthetic validation and reference isolation checks |
| `tests/phase3/audit_evidence.py` | Numeric COMET and provenance audit |
| `docs/phase3/evidence/` | Numeric scores, specifications, provenance and scorer source |
| `paper/phase3/dev_baselines.tex` | Dev baseline table for the existing manuscript |

The original split translation generation cell is absent from the supplied
evidence. Its run specification, segmentation fingerprint and output hashes are
retained. `docs/phase3/evidence/code/generating_evaluator_source.py` is the **scorer**, not
the missing translation generator. The package therefore does not claim complete
source archival for that earlier generation step.

## Development pilot results and reproduction

The pilot runs are complete. Do not rerun an old notebook merely because its
historical stage text says “pending.” No further GPU run is needed to review
Report 3. Start with `docs/phase3/evidence/pilot/pilot_condition_results.csv` and
`independent_numeric_audit.json`. COMET is native score ×100; the exact baseline
for these conditions is the 100-ID sample, not the full 997-ID dev corpus.

The exact measured pilot code is in `src/phase3/post_editing/`. `gpt_pilot.py`
implements the dated API snapshot with resumable records, four workers, four
request starts/sec, explicit transient HTTP retries and halt-on-uncertain-call
behavior. `analyze_pilots.py` scores both complete dev pilots. Their original
CLI/pointer layout is preserved; use `--help` before reproducing the private run.
Neither is a completed main-devtest execution engine.

To reproduce the independent audit, extract the original private full evidence
ZIP, install `config/phase3/audit_requirements.txt` in an isolated environment,
then run `python tests/phase3/audit_full_pilot.py /path/to/extracted/evidence`.
This recomputes lexical metrics and checks COMET caches/aggregation; it does not
rerun neural COMET inference. Raw evidence is intentionally not in this public
repository. Numeric-only condition summaries and 2,400 segment-score rows are public.

For the manuscript: `python scripts/update_manuscript_tables.py --check`, then
`python src/analysis/audit_manuscript.py`. See `paper/README.md` for compilation.

## Local verification

Run these from the repository root in a separate environment:

```bash
python3 -m venv .venv-phase3-check
.venv-phase3-check/bin/pip install -r config/phase3/test_requirements.txt
.venv-phase3-check/bin/python tests/phase3/test_pilot.py
.venv-phase3-check/bin/python tests/phase3/audit_evidence.py
```

The documented synthetic tests passed with Pydantic 2.12.3. They cover query
reference isolation, permitted demonstration references, self exemplar rejection,
pilot exclusion, duplicate source checks, deterministic ties, strict schemas,
diagnostic ordering, truncation fallback, distinct smoke IDs, a 1,200 job
fixture, checkpoint reuse and checksum corruption. Both clean notebooks compile.
These checks are not a successful LaBSE indexing run or Llama experiment.

## Remaining Phase 3 acceptance criteria

- [x] Verify alignment, source segmentation, split/unsplit dev results.
- [x] Implement and execute candidate-v2 retrieval and all three strategies.
- [x] Review 24 Llama smoke outcomes and both full 1,200-outcome pilots.
- [x] Complete measured quality, failure and preservation analysis.
- [x] Compare the supplied final ICAI paper and document shared methodology.
- [x] Update Report 3 with measured pilot evidence and the exact candidate.
- [ ] PI review of the substantial ICAI overlap and proposed contribution boundary.
- [ ] Decide the diagnostic-contract disposition, with dev revalidation if changed.
- [ ] Record final prompt/schema/model/retrieval/evaluation/code hashes and freeze.
- [ ] Obtain Phase 3 acceptance before the main devtest study.

The measured condition retains failures and baseline fallback. A redesigned
contract, removed condition or changed metric policy must be documented before
freeze, with affected dev validation. The original roadmap's fastText screen
differs from the measured langdetect pilot; chrF++ uses word order 2 (the old
word-order-1 label was inconsistent). These differences are disclosed rather
than silently changing the measured evidence. The held-out contrast and
multiplicity plan and exact retrieval eligibility must be recorded before scoring.

## Next phases according to the roadmap

| Phase | Work | Current status |
|---|---|---|
| 4 | Main devtest generation using the frozen system matrix and resumable execution | Future work |
| 5 | Primary COMET analysis, secondary lexical metrics, paired statistics and systematic failure analysis | Future work |
| 6 | Manuscript integration in the existing ICNLP Overleaf project | IEEEtran development draft complete locally; live sync requires access |
| 7 | Numerical manuscript audit, figures and reviewer response preparation | Development checks and internal memo prepared; main-results audit pending |
| 8 | Final environment capture, repository sanitization and handoff | Current public update checked; final release pending |

The planned Phase 4 matrix is 1,012 devtest IDs × four directions × two post
editors × three strategies = **24,288 post editing outputs**, conditional on
the final approved model matrix and access. The API target in the roadmap is
`gpt-4o-mini-2024-07-18`; both API and Llama dev execution are now evidenced. The current Llama
pilot runner is not the complete Phase 4 multi backend execution engine.

Use the **existing ICNLP Overleaf project**. Transfer reviewed methods and the
included dev table with its exploratory caption. Do not present baseline
segmentation gains as post editing gains or future runs as completed findings.

## Provenance

| Artifact | Identifier |
|---|---|
| FLORES+ | `openlanguagedata/flores_plus` |
| Dataset revision | `5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06` |
| NLLB revision | `1a07f7d195896b2114afcb79b7b57ab512e7b43e` |
| COMET model | `Unbabel/wmt22-comet-da` |
| COMET revision | `2760a223ac957f30acfb18c8aa649b01cf1d75f2` |
| Generation signature | `f4a3af94ba1e72fddc14a8986924fc23e00ae2884dc8d51800ad79e43a6a0563` |
| Evaluation signature | `6d6e94fc2a8d3d8f34d4a1b4d5cddedc139ba4ce278cc1518277093dbefb3b08` |
| Pilot ID signature | `3012c0619fc11368b12a9e29c704ddc669e5f53b32f0685beec72a3fa25dd742` |
| Original Phase 3 update commit | `599aea4` |

Generation ran with Python 3.13.15, torch 2.11.0+cu130 and Transformers 5.18.0.
Evaluation ran with Python 3.11.17, torch 2.6.0+cu124, Transformers 4.49.0,
unbabel comet 2.2.7, NumPy 1.26.4 and SacreBLEU 2.6.0. Both used an A100 80 GB.
The evidence includes resolved evaluation packages and exact metric settings.
LaBSE revision is `836121a0533e5664b21c7aacc5d22951f2b8b25b`; Llama revision
is `8afb486c1db24fe5011ec46dfbe5b5dccdb575c2`. The current measured configuration
and isolated environment versions are in `config/phase3/Reviewed_Candidate_Configuration.json`.

## Data and repository policy

Raw FLORES text and translation JSONL outputs remain on Google Drive. Do not
commit raw source/reference text, model weights, embeddings, FAISS indexes,
API keys, token files or `.env` contents. Numeric dev score caches are included
for auditability. Keep notebook output cells clear before publication.

The root Drive location is `/content/drive/MyDrive/norris`. The saved baseline
run is under `outputs/generations/baselines/phase3_dev_f4a3af94ba1e72fd`, and
its completed evaluation is under `evaluation/6d6e94fc2a8d3d8f` within that run.
Candidate post editing artifacts are created under
`outputs/phase3_post_editing/candidate_<configuration hash>` when preparation runs.

Report 3 and this README are progress records. Update their measurements only
from returned, auditable run evidence; do not mark pilot execution or Phase 3
completion from code preparation alone.

## Update — 23 October 2026: Phase 3 revision, freeze, Phases 4–5 (code ready; runs pending)

Following the PI's 22 October acceptance message:

* **ICAI boundary approved.** Frozen-NMT anchoring and semantic exemplar retrieval are cited as prior methodology, not Norris contributions.
* **Reason-then-edit revised (dev only).** Minimal contract `rte_v3` (`diagnosis` → `edited_translation`) with a predeclared reliability gate; see `docs/phase3/RTE_CONTRACT_REVISION.md`. Rerun both models with `notebooks/phase3/03_rte_v3_revalidation_and_freeze.ipynb`.
* **Freeze.** `src/freeze/build_freeze_manifest.py` writes `config/frozen/protocol_freeze.json` only after the gate and the splitter dev gates pass.
* **Phase 4.** `src/baselines/generate_devtest_baseline.py` (S0 devtest, gated), `src/post_editing/prepare_main_jobs.py`, `src/post_editing/run_main_experiments.py` (AsyncOpenAI + vLLM, SQLite ledger + durable records, resumable, no repeat of uncertain paid calls), `src/post_editing/phase4_summary.py`; notebook `notebooks/phase4/01_devtest_main_run.ipynb`.
* **Phase 5.** `src/evaluation/evaluate_main_experiments.py` + `norris_stats.py` (centered paired bootstrap, Holm families F1/F2), `src/analysis/generate_main_figures.py`; notebook `notebooks/phase5/01_evaluate_main.ipynb`.
* **Tests (no GPU/API):** `tests/frozen/test_protocol.py`, `tests/phase4/test_engine_offline.py`, `tests/phase5/test_stats.py`, `tests/phase5/test_evaluator_synthetic.py`.
* **Manuscript** restructured for 5 pages around the held-out experiment (`paper/README.md`); schedule in `docs/SCHEDULE_AND_REPORTS.md`; runbook in `docs/phase4/RUNBOOK.md`.

No devtest output has been generated or scored at this commit.

## Update — 24 October 2026: protocol frozen

* Reason-then-edit v3 dev rerun: Llama 3 8B **0/400** fallbacks (v2: 227), GPT-4o Mini **0/400** (v2: 8); predeclared gate passed.
* S0 dev audit: segmentation 2,991/2,991 exact; dev unsplit regeneration 3,988/3,988 exact; multi-sentence translations 412/421 exact (disclosed; `docs/phase3/Norris_Phase_Report_3_2.pdf`, Section 5).
* Freeze declared 2026-10-24 06:58 UTC: `config/frozen/protocol_freeze.json` (SHA-256 `6e6259a9…f7462c`). Numeric evidence in `docs/phase3/evidence/rte_v3/`.
* Next: Phase 4 devtest run with `notebooks/phase4/01_devtest_main_run.ipynb` (branch `phase4-main`).

## Update — 24 October 2026: Phase 4 complete (generated, not scored)

24 conditions × 1,012 devtest items = 24,288 post-edited outputs plus the S0 baseline. Llama 3 8B and GPT-4o Mini: 12,144/12,144 accepted each, **0 fallbacks**; GPT 12,144 requests all HTTP 200, 0 retries (est. $1.10). Executed code identical to the frozen code. Report: `docs/phase4/Norris_Phase_Report_4.pdf`; numeric evidence: `docs/phase4/evidence/`. Next: Phase 5 (`notebooks/phase5/01_evaluate_main.ipynb`).

## Update — 25 October 2026: Phase 5 complete (held-out results)

GPT-4o Mini improved COMET-22 over the split NLLB baseline in all 12 direction × strategy conditions (+0.26 to +1.00 points, all Holm-significant); Llama 3 8B Instruct improved none and was significantly worse in 6 (all reason-then-edit directions; zero/one-shot En→Tl). Protect-pool over-editing: GPT-4o Mini 0.8–4.3% of 1,179 strong drafts, Llama 11.2–20.9%. All numbers independently recomputed from the 24,288 segment scores. Report: `docs/phase5/Norris_Phase_Report_5.pdf`; numeric evidence: `docs/phase5/evidence/`. Manuscript audit: `python scripts/audit_manuscript.py` (61 held-out claims + generated tables).

