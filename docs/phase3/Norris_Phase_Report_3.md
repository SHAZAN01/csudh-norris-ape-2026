# Norris Research Project Phase Report 3

Development Baselines and Post Editing Pilot Preparation

Project: Evaluating Large Language Models as Post Editors for English–Tagalog and English–Spanish Translation

Principal Investigator: Dr. Benyamin Ahmadnia
Graduate Research Assistant: Shazan Ansar Mohammed
Reporting period: October 16–17, 2026
Repository: https://github.com/SHAZAN01/csudh-norris-ape-2026

### Executive summary

The dev baseline experiment is complete and its COMET results have been audited. Sentence splitting changed 377 of 3,988 translations and increased mean COMET in all four directions. The paired confidence interval includes zero for Tagalog to English; improvement in that direction remains inconclusive. These are baseline diagnostics, not evidence of an LLM post editing gain.

The three candidate prompt strategies, strict output schemas, retrieval builder and resumable Llama runner are implemented and locally tested. Evidence of actual LaBSE indexing, Llama smoke generation and the full post editing pilot has not yet been supplied. Phase 3 therefore remains open and the protocol is not frozen. This report records verified progress and the remaining completion criteria.

**Required item checklist**

| Item | Current status |
|---|---|
| Dev integrity and segmentation | Verified |
| Split baseline generation and evaluation | Complete on dev only |
| Three prompts and output schemas | Implemented and locally tested |
| LaBSE and FAISS retrieval | Builder prepared; runtime evidence pending |
| Llama pilot | Runner prepared; execution evidence pending |
| GPT 4o Mini pilot | Pending API access and implementation |
| Protocol freeze | Not declared |
| GitHub update | Prepared for publication; not pushed here |

The current update covers Norris only. The separate ICAI work is outside this report. No external human raters are included, following the PI’s September 24 feedback.

## 1 Data Integrity and Sentence Segmentation

All development work used FLORES+ dev: 997 aligned sentence IDs in each of four directions. Source and reference alignment, nonempty drafts and manifest checksums passed. English, Spanish and Tagalog source texts comprise 2,991 unique source language records. No devtest file was opened or scored during this Phase 3 workflow. The older Phase 2 devtest generations remain separate and unscored.

The FLORES+ revision is pinned. Tagalog uses the dataset configuration fil_Latn and the NLLB language code tgl_Latn. These names are intentionally different and must not be replaced with tag_Latn.

### Segmentation method

The candidate uses pysbd 0.3.4 with clean=False and character spans. English and Spanish use their corresponding rule sets; Tagalog uses English rules as a documented heuristic. Source characters and whitespace must reconstruct exactly before translation. Independent fragment translations are then joined with a single space; reconstruction guarantees source preservation, not translation completeness.

**Final candidate source counts**

| Source | Items | Multi sentence | Fragments |
|---|---|---|---|
| English | 997 | 104 | 1,104 |
| Tagalog | 997 | 104 | 1,104 |
| Spanish | 997 | 109 | 1,109 |

The Spanish Jr. safeguard corrected items 31 and 159 in candidate v2. Candidate v3 then changed exactly seven reviewed source language items relative to v2: English 187, 641 and 960; Tagalog 641, 956 and 960; Spanish 641. These changes merge a clock abbreviation before a weekday, the Tagalog abbreviation atbp., and detached parenthetical or citation continuations. All 12 synthetic boundary tests and lossless reconstruction checks passed.

### Translation controls

NLLB 200 3.3B used FP16, batch size 32, four beams, max_length 512, length penalty 1.0, early stopping and no sampling. Inputs were not silently truncated. The same run generated an unsplit control and the split condition. For single segment sources, the split condition reuses the control hypothesis; only multi sentence fragments require additional inference.

All 997 unsplit hypotheses per direction exactly reproduced the archived Phase 2 hypotheses: 3,988 matches and zero differences. A prior small smoke run had one mismatch; the full control resolves the observed reproducibility check, but does not isolate the cause of that earlier mismatch.

## 2 Verified Development Baseline Results

COMET 22 is the primary metric. BLEU and chrF++ are secondary. All scores below come from the completed evaluation artifact. COMET is reported as the native score multiplied by 100; differences use sentence split minus current unsplit. Each condition has 997 items per direction.

**Table 1 Baseline metric values**

| Direction | Condition | BLEU | chrF++ | COMET |
|---|---|---|---|---|
| En to Tl | Unsplit | 35.436 | 60.054 | 84.735 |
| En to Tl | Split | 35.820 | 60.665 | 85.086 |
| Tl to En | Unsplit | 50.806 | 69.374 | 87.734 |
| Tl to En | Split | 50.641 | 69.495 | 87.787 |
| En to Es | Unsplit | 27.924 | 53.484 | 86.171 |
| En to Es | Split | 28.231 | 53.913 | 86.463 |
| Es to En | Unsplit | 32.882 | 59.306 | 87.400 |
| Es to En | Split | 32.949 | 59.713 | 87.543 |

**Table 2 Paired COMET differences in points**

| Direction | All items | 95% interval | Multi n | Multi delta |
|---|---|---|---|---|
| En to Tl | +0.351 | [+0.216, +0.497] | 104 | +3.363 |
| Tl to En | +0.053 | [-0.019, +0.130] | 104 | +0.508 |
| En to Es | +0.292 | [+0.143, +0.448] | 104 | +2.797 |
| Es to En | +0.142 | [+0.061, +0.232] | 109 | +1.301 |

Intervals use 10,000 paired percentile bootstrap resamples with seed 42. They are descriptive dev diagnostics; no confirmatory p values or multiplicity adjusted claims are made. The full precision values and multi sentence confidence intervals accompany the repository evidence.

English to Tagalog, English to Spanish and Spanish to English have positive intervals excluding zero. Tagalog to English has a smaller positive point estimate with an interval spanning zero; its BLEU also decreases slightly. Sentence splitting is retained as the PI approved primary baseline, while the unsplit condition remains available for diagnostic analysis.

The larger multi sentence effects localize the change to the subset exposed to segmentation. They do not show that every changed output improved or that every omission was repaired. Cross sentence consistency may still worsen. No LLM post editing results are reported in this table.

## 3 Quality Checks and Compute Accounting

**Table 3 Output changes and COMET change bands**

| Direction | Text changed | Increase | Within band | Decrease |
|---|---|---|---|---|
| En to Tl | 96 | 41 | 949 | 7 |
| Tl to En | 93 | 19 | 968 | 10 |
| En to Es | 85 | 33 | 955 | 9 |
| Es to En | 103 | 27 | 961 | 9 |

Increase means native COMET delta > 0.02; decrease means delta < −0.02; the middle band includes both endpoints. The threshold corresponds to 2 COMET points, not 0.02 reported points. Totals are 120 increases, 3,833 within band and 35 decreases. The middle band is not a count of unchanged translations: 3,611 hypotheses are textually identical, and 222 changed hypotheses fall within the band.

**Table 4 Baseline quality pools for later pilot analysis**

| Direction | COMET below 0.80 | COMET at least 0.90 |
|---|---|---|
| En to Tl | 187 | 237 |
| Tl to En | 75 | 387 |
| En to Es | 119 | 277 |
| Es to En | 53 | 283 |

These are dev baseline pool sizes, not pilot outcomes or human quality judgments. The sampling plan is uniform across aligned IDs, so it is balanced by direction and strategy rather than by baseline quality.

### Efficient use of the A100

Generation produced 7,976 final records: 997 IDs × four directions × two conditions. This count is not the number of independent model sequences. Logged inference totaled 368.06 seconds and invocation wall time was 381.06 seconds, approximately 6 minutes 21 seconds, on an A100 80 GB. Model download and loading before the invocation are excluded. Amortized item times are not isolated request latency.

Evaluation scored all 3,988 control triplets and only the 377 changed split triplets, reusing scores for identical source, hypothesis and reference triplets. This required 4,365 scored triplets rather than 7,976. The rechecked original COMET scores matched the archived scores exactly in every direction.

### Independent audit scope

The supplied evidence supports verification of configuration and cache hashes, per item COMET means, all item paired intervals and change bands. The uploaded evidence does not contain the raw translation JSONL files, so BLEU and chrF++ have not been independently rescored here; their reported values and signatures are retained from the provenance checked Colab evaluator. Source subgroup membership is recorded in the generation evidence; subgroup intervals were not independently reconstructed from raw rows here.

## 4 Post Editing Implementation

Candidate prompt version candidate_v1_not_frozen implements all three roadmap strategies. The templates treat source text as the authority, require the requested target language, discourage stylistic rewriting and preserve names, numbers and dates. Accurate drafts should be returned unchanged. Source and draft strings are treated as data rather than executable instructions.

### Prompt strategies and structured output

Zero shot receives the current source and NLLB draft and returns edited_translation only. Retrieved one shot adds one solved dev demonstration containing its source, draft and gold translation. Reason then edit returns a diagnostics array before edited_translation, with brief observable error summaries separated from the translation.

The six allowed diagnostic categories are MISTRANSLATION, OMISSION, UNSUPPORTED_ADDITION, MORPHOSYNTAX_MISMATCH, NAMED_ENTITY_CORRUPTION and NONE. Notes are limited to 25 words each, categories cannot repeat, and NONE must appear alone. Pydantic validators reject empty translations, duplicate or extra keys and incoherent diagnostics. The runner distinguishes JSON parsing, schema validity and usable completion; a truncated response can parse successfully while remaining unusable.

vLLM supplies structural JSON constraints; Pydantic supplies post generation and cross field validation. These are separate mechanisms. Unusable outputs retain their raw record and fall back to the baseline, with no selective repair pass. Actual model compliance rates remain unmeasured.

### Retrieval and leakage controls

The builder encodes 997 dev sources per source language using normalized float32 LaBSE embeddings and exact FAISS IndexFlatIP cosine ranking. Top 1 is selected within the appropriate direction with a deterministic sentence ID tie break. Semantic similarity is measured; a separate syntactic similarity claim is not made.

The same 100 seed 42 pilot IDs are used in all directions. All 100 IDs are excluded from every demonstration pool, leaving 897 candidate IDs before exact duplicate source exclusion. The current query reference and baseline quality scores never enter a model prompt. Only the retrieved nonpilot example may expose its own gold dev translation. Gold pilot references remain in a separate offline evaluation file.

Prepared code saves embeddings, FAISS indexes, corpus maps, 400 retrieval links, 1,200 Llama jobs and configuration hashes. These are expected outputs of the builder; their creation on the real corpus is not yet verified. LaBSE and Llama revisions are resolved and pinned by the notebook before execution, rather than silently substituting a different model.

## 5 Pilot Readiness and Technical Issues

The supplied Colab notebook targets Meta Llama 3 8B Instruct, not Llama 3.1. It first prepares retrieval and then runs a 24 output smoke check: two distinct dev IDs × four directions × three strategies, including a multi sentence item. The full Llama pilot is 1,200 outputs. The notebook defaults to smoke execution; the full run requires the runner’s full stage after smoke review.

Candidate generation settings are BF16 without quantization, temperature 0, top_p 1, top_k −1, seed 42 and a 1,024 output token cap. vLLM uses an 8,192 token context, GPU memory utilization 0.70, at most 16 concurrent sequences, prefix caching and eager execution to avoid compilation startup. These settings are prepared and dependency resolved; they are not yet validated by a successful GPU pilot.

### Local validation completed

Synthetic tests with Pydantic 2.12.3 passed for query reference isolation, permitted demonstration references, self exemplar rejection, all pilot IDs excluded, duplicate source rejection and deterministic tie breaking. Other checks cover JSON validation, diagnostics ordering, truncation fallback, two distinct smoke IDs, a 1,200 job fixture, checkpoint reuse and deliberate checksum corruption. All six notebook code cells compile and embedded source hashes match the prepared modules. No real post editor output was generated by these tests.

### Issues and responses

An earlier segmentation assertion expected fewer changes than the seven reviewed corrections. The expected item set was corrected and the complete synthetic suite was rerun. Spanish Jr. and detached parentheticals were repaired before the full generation. Tagalog segmentation still uses a heuristic and remains a limitation.

The original Python 3.13 environment was retained for NLLB generation. COMET evaluation used an isolated Python 3.11 environment to avoid dependency conflicts. Retrieval and Llama preparation use separate pinned environments. Successful dependency resolution is recorded as setup validation, not proof that inference completed.

An earlier notebook label suggested a Phase 3 pilot despite containing Phase 2 code. The replacement notebooks now separate completed baseline evaluation from candidate retrieval and Llama execution. Hash checked checkpoints support resumption after a Colab disconnect; an unfinished batch may need recomputation.

Pending measurements include parse and schema success, usable output and fallback rates, latency, edit rate, over editing on strong drafts, number and entity preservation, target language errors, and COMET changes by direction and strategy. None is assigned an invented value in this report. GPT 4o Mini remains pending API access and its runner.

## 6 Completion Criteria and Next Phases

The next priority is to finish and analyze the dev pilot before freezing settings. Repeating NLLB generation or completed baseline scoring would spend A100 time without resolving the remaining question.

**Remaining Phase 3 milestones**

| Order | Action | Evidence needed |
|---|---|---|
| 1 | Run the prepared 24 output Llama smoke check | Model revisions, retrieval files, raw outputs and logs |
| 2 | Review failures and run the 1,200 output Llama pilot | Complete hash checked records for every planned job |
| 3 | Score and diagnose the pilot on dev | Quality, validity, edit and preservation summaries |
| 4 | Complete GPT pilot when access is available | Equivalent 1,200 jobs or a documented PI approved deviation |
| 5 | Freeze prompts and experimental settings | Versioned freeze manifest and unresolved issue disposition |

Pilot analysis should retain invalid generations in the accounting and report baseline fallback separately. Over editing should be evaluated on predeclared strong baseline pools, with both edit frequency and quality change. Name and number checks are heuristic flags requiring systematic source based review; they are not human evaluation or guaranteed error labels. Candidate revisions must remain logged rather than being chosen from devtest scores.

### Protocol freeze requirements

The freeze must record exact prompt bytes, schemas, model revisions, retrieval exclusions and tie breaking, decoding and chat template settings, output limits, stop rules, failure handling, sample IDs and scoring definitions. Prompt, retrieval and model decisions remain dev only. Phase 3 is complete only after pilot evidence and analyses are reviewed and the freeze is explicitly recorded. Any outstanding PI scope decisions must be documented rather than silently assumed resolved.

### Phase 4 and Phase 5 according to the roadmap

After the freeze, Phase 4 runs the main experiment on the 1,012 held out devtest IDs in four directions, for two post editors and three strategies: 24,288 planned post editing outputs. This total assumes both model conditions remain approved and accessible. Use resumable checkpoints, track missing or failed jobs and keep the approved split baseline as the primary comparison with unsplit diagnostics retained.

Phase 5 evaluates quality and failures using COMET as primary, BLEU and chrF++ as secondary, with the predeclared paired statistical analysis and comparison families. Main experiment inference and confirmatory analysis are still future work. Transfer reviewed methods and current dev tables into the existing ICNLP Overleaf project; do not describe future pilot results as completed findings.

## 7 Provenance and Repository Handoff

The source evidence is the completed dev evaluation ZIP, its generation and evaluation manifests, four numeric per item score caches, evaluator source and resolved package list. Reports 1 and 2, the eight role instructions and September 24 PI feedback supplied the scope and next phase criteria. Report 3 updates the observed state; earlier repository content claims are not treated as proof of the current remote state.

**Pinned model and data revisions**

| Artifact | Revision |
|---|---|
| FLORES+ | 5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06 |
| NLLB 200 3.3B | 1a07f7d195896b2114afcb79b7b57ab512e7b43e |
| COMET 22 | 2760a223ac957f30acfb18c8aa649b01cf1d75f2 |

Generation signature
f4a3af94ba1e72fddc14a8986924fc23e00ae2884dc8d51800ad79e43a6a0563
Evaluation signature
6d6e94fc2a8d3d8f34d4a1b4d5cddedc139ba4ce278cc1518277093dbefb3b08

Generation used Python 3.13.15, torch 2.11.0+cu130 and Transformers 5.18.0. Evaluation used Python 3.11.17, torch 2.6.0+cu124, Transformers 4.49.0, unbabel comet 2.2.7, NumPy 1.26.4 and SacreBLEU 2.6.0. Exact evaluator settings and resolved packages are included with the evidence. BLEU uses mixed case, 13a tokenization and exponential smoothing; chrF++ uses character order 6, word order 2 and beta 2.

### What the GitHub update contains

The prepared update includes Report 3 in PDF, Word and Markdown; exact numeric dev evidence; the evaluator and candidate prompt, retrieval and Llama modules; clean Colab notebooks; validation scripts; a candidate status manifest; and LaTeX dev table material for the existing manuscript. Raw FLORES text, translation JSONL files, weights, embeddings, indexes and credentials are excluded.

The original sentence split generation was run in Colab. Its specification and output hashes are retained, but the supplied evidence does not include the exact generation cell source; this update does not claim to archive that missing source. The evaluator source that produced the scores is preserved separately from the current resume evaluator.

The supplied Mac snapshot showed main at commit 35766b3 with only the scaffold tracked. The current remote could not be authenticated from this session. The update package creates a separate branch from fetched origin/main, preserves existing files when conflicts occur and does not commit or push automatically. A successful remote commit or pull request must be verified before claiming GitHub is updated.

Current conclusion: the split baseline is established and evaluated on dev; the post editing implementation is ready for runtime validation. Phase 3 completion, the protocol freeze and the main experiment remain pending.
