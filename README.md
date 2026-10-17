# Norris Research Project

## LLM post editing for English–Tagalog and English–Spanish translation

**Principal investigator:** Dr. Benyamin Ahmadnia  
**Graduate research assistant:** Shazan Ansar Mohammed  
**Institution:** California State University, Dominguez Hills  
**Program:** Norris Research Program, Fall 2026  
**Progress snapshot:** 17 October 2026

This project evaluates whether large language models can improve NLLB translations
while avoiding unnecessary edits and meaning changes. The experiment compares
zero shot, retrieved one shot and structured reason then edit strategies across
English ↔ Tagalog and English ↔ standard Spanish.

**Current conclusion:** the sentence split NLLB baseline has been generated and
evaluated on dev. Candidate prompts, schemas, retrieval preparation and a Llama
runner are implemented and locally tested. Real retrieval execution and Llama
pilot evidence remain pending. **Phase 3 is open and the protocol is not frozen.**

The results below measure the effect of baseline segmentation. They are not LLM
post editing results. Devtest has not been opened or scored in Phase 3.

## Read first

- [Phase Report 3 PDF](docs/phase3/Norris_Phase_Report_3.pdf)
- [Editable Word report](docs/phase3/Norris_Phase_Report_3.docx)
- [Report source in Markdown](docs/phase3/Norris_Phase_Report_3.md)
- [Execution runbook and acceptance criteria](docs/phase3/RUNBOOK.md)
- [Machine readable development metrics](docs/phase3/evidence/evaluation/dev_baseline_metrics.json)
- [Candidate status manifest](config/phase3/status.json)
- [Metric interpretation notes](docs/phase3/NUMERICAL_NOTES.md)

## What is complete

| Work item | Evidence and current state |
|---|---|
| Phase 2 data and original NLLB baseline | Earlier reported work; original outputs remain on Drive |
| Dev data integrity | 997 aligned, nonempty records per direction; source checksums verified |
| Lossless source segmentation | Final candidate tested; all 2,991 source language records reconstruct exactly |
| Split and control generation | 7,976 final records across four directions and two conditions |
| Baseline evaluation | COMET, BLEU and chrF++ recorded on dev; paired COMET diagnostics audited |
| Prompt and schema code | Three candidate strategies implemented and tested with synthetic fixtures |
| Retrieval implementation | LaBSE/FAISS builder implemented; real corpus execution evidence pending |
| Llama implementation | Resumable runner and 24 output smoke notebook prepared; execution evidence pending |
| Full pilot and analysis | Still to execute and evaluate |
| GPT 4o Mini | API access and runner remain pending |
| Protocol freeze | Not declared |
| Main devtest experiment | Future Phase 4 work after freeze |

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

**Prompt version:** `candidate_v1_not_frozen`.

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

The preparation code is designed to save three embedding arrays and indexes,
corpus maps, 400 retrieval links, 400 offline evaluation rows and 1,200 Llama
jobs, with checksums. These are planned real corpus outputs; their creation has
not yet been evidenced by a returned execution bundle.

### Candidate Llama settings

| Setting | Candidate value |
|---|---|
| Model | `meta-llama/Meta-Llama-3-8B-Instruct` |
| Model revision | Resolved and pinned by the notebook before execution |
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

## Run next in Colab Pro

1. Open `notebooks/phase3/02_prompts_retrieval_llama.ipynb` in Colab.
2. Select an **A100 80 GB** runtime and retain the existing Drive root
   `/content/drive/MyDrive/norris`.
3. Grant the notebook access to the Colab Secret `HF_TOKEN` for the authorized
   model account. Do not print or commit the token.
4. Run cells in order. The notebook restores its tested embedded source,
   installs separate environments, validates the saved baselines, pins model
   revisions and prepares retrieval/jobs.
5. Its default execution is the **24 output smoke stage**: two distinct dev IDs
   × four directions × three strategies, including a multi sentence item.
6. Retain the downloaded `Norris_Phase3_Llama_Smoke_Evidence_<runsha>.zip`.
   Review revisions, retrieval exclusions, raw completions, token limits,
   JSON/schema/usable counts, fallbacks and logs.
7. After reviewing the smoke evidence, run the saved runner with the exact
   pointer shown by the notebook and `--stage full` to produce the 1,200 output
   Llama pilot. The default notebook does not run that full stage automatically.

The original Python 3.13 NLLB generation environment and Python 3.11 COMET
environment were different. Retrieval and vLLM also use separate environments.
Use the notebook's recorded installations rather than installing all packages
into Colab's base environment. Dependency resolution passed locally; real GPU
pilot execution remains to be validated.

Completed NLLB generation and baseline evaluation do not need repeating to
start the pilot. Load models sequentially and use checkpoint resumption after
interruptions. Completed matching records are reused; an interrupted unfinished
batch may require recomputation. No pilot duration is asserted without run logs.

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

- [x] Validate dev alignment and source integrity.
- [x] Review segmentation and generate the split and unsplit controls.
- [x] Evaluate and audit the development baseline comparison.
- [x] Implement candidate prompt, schema, retrieval and Llama generation code.
- [x] Complete synthetic validation and dependency resolution checks.
- [ ] Capture actual dev retrieval/index preparation evidence.
- [ ] Execute and review all 24 Llama smoke outputs.
- [ ] Execute the full 1,200 output Llama pilot.
- [ ] Implement and run pilot quality and failure analysis.
- [ ] Complete the GPT pilot when access is available, or record a PI approved scope deviation.
- [ ] Review unresolved failures and record any candidate revisions.
- [ ] Freeze prompts, schemas and experimental settings explicitly.
- [ ] Update Report 3 with the actual pilot results before labeling Phase 3 complete.

Pilot analysis must report parse, schema and usable output rates; fallback;
edit frequency; COMET changes; over editing on strong baseline pools; number
and name preservation flags; target language flags; and latency with its
measurement definition. Heuristic flags are not gold error labels. Keep failed
outputs in the accounting and distinguish baseline fallback from model success.

The freeze must identify exact prompt bytes, schemas, model/tokenizer revisions,
retrieval policy, sample IDs, decoding and chat template settings, output limits,
stop and failure rules, environments and analysis definitions. Model or prompt
choices must remain based on dev. Outstanding PI scope decisions must be
documented rather than silently treated as resolved.

## Next phases according to the roadmap

| Phase | Work | Current status |
|---|---|---|
| 4 | Main devtest generation using the frozen system matrix and resumable execution | Future work |
| 5 | Primary COMET analysis, secondary lexical metrics, paired statistics and systematic failure analysis | Future work |
| 6 | Manuscript integration in the existing ICNLP Overleaf project | Current verified methods may be drafted; full results pending |
| 7 | Numerical manuscript audit, figures and reviewer response preparation | Future work |
| 8 | Final environment capture, repository sanitization and handoff | Future work |

The planned Phase 4 matrix is 1,012 devtest IDs × four directions × two post
editors × three strategies = **24,288 post editing outputs**, conditional on
the final approved model matrix and access. The API target in the roadmap is
`gpt-4o-mini-2024-07-18`; no API execution is claimed here. The current Llama
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
LaBSE and Llama runtime revisions remain pending until the prepared notebook
resolves and records them. Do not invent commit IDs for unexecuted preparation.

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
