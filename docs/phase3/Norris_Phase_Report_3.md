# Norris Phase Report 3

Development pilots and acceptance review

Principal Investigator  Dr Benyamin Ahmadnia
Graduate Research Assistant  Shazan Ansar Mohammed
Reporting update  19 October 2026
Repository  github.com/SHAZAN01/csudh-norris-ape-2026

Empirical pilot work complete  Final protocol freeze and Phase 3 sign off pending

## Executive summary

Both development pilots are complete and evaluated: 100 aligned dev IDs across four directions and three strategies for each of two post-editors, giving 2,400 system outcomes. Actual retrieval, Llama smoke/full generation, GPT-4o Mini inference, quality scoring and failure analysis are now evidenced. The independent audit reproduced the 24 metric rows and paired intervals from raw text and audited numeric score caches.

GPT retrieved one-shot achieved the largest En-to-Tl pilot gain: +1.463 COMET points, with a descriptive 95% interval of [+0.710, +2.396]. This is a dev diagnostic, not a confirmatory finding. Llama reason-then-edit returned usable output on only 173/400 items; the other 227 used the predeclared baseline fallback. GPT reason-then-edit used fallback on 8/400 items. These failures remain in all reported results.

The supplied ICAI paper confirms substantive overlap in frozen-NMT anchoring and semantic exemplar retrieval. Norris should be positioned as a distinct empirical extension, with those shared components cited as prior work. This comparison is now complete and is brought to the PI before freeze, as requested. No main devtest experiment or protocol freeze is declared here.

| Acceptance item | Evidence status |
| --- | --- |
| Actual dev retrieval | Complete and independently checked |
| Llama smoke and full pilot | 24 smoke and 1,200 full outcomes accounted for |
| GPT pilot | Exact dated snapshot; 1,200 outcomes accounted for |
| Quality and failure analysis | Complete; 24 rows independently reproduced |
| ICAI comparison | Complete; substantial shared methods disclosed |
| Freeze and main experiment | Pending PI review of overlap and protocol disposition |

## 1  Development design and baseline continuity

The same seed-42 sample of 100 aligned FLORES+ dev IDs is used in every model and strategy. This is balanced by condition count, not by baseline-quality strata. The 2,400 outcomes are repeated system observations on 100 aligned IDs in four directions; they are not 2,400 independent source sentences. The supplied workflow remains dev only. The 1,012-item devtest partition is reserved for the main experiment.

FLORES+ revision 5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06 is retained. The dataset configuration fil_Latn maps to NLLB tgl_Latn. Standard Spanish is the comparator; the benchmark does not support claims about heritage, dialectal, code-switched or Los Angeles community Spanish.

### Earlier split versus unsplit comparison

| Direction | Split COMET | Delta points | 95% dev interval |
| --- | --- | --- | --- |
| En to Tl | 85.086 | +0.351 | [+0.216, +0.497] |
| Tl to En | 87.787 | +0.053 | [-0.019, +0.130] |
| En to Es | 86.463 | +0.292 | [+0.143, +0.448] |
| Es to En | 87.543 | +0.142 | [+0.061, +0.232] |

These earlier figures use all 997 dev items per direction and are retained from the audited baseline report. Tagalog-to-English remains inconclusive because its interval includes zero. The sentence-split condition remains the PI-approved primary baseline and the unsplit condition remains diagnostic. These segmentation gains are separate from LLM post-editing gains.

### Split baseline on the actual pilot sample

| Direction | BLEU | chrF++ | COMET | Below .80 | At least .90 |
| --- | --- | --- | --- | --- | --- |
| En to Tl | 35.884 | 60.632 | 84.442 | 19 | 22 |
| Tl to En | 46.957 | 67.821 | 87.118 | 12 | 45 |
| En to Es | 27.694 | 54.086 | 86.076 | 11 | 21 |
| Es to En | 29.780 | 58.116 | 87.829 | 3 | 28 |

COMET is reported as native score x100. Quality pools use the original baseline native segment scores, fixed before post-editing. The new evaluator rechecked all 400 pilot baselines; maximum absolute deviation from archived scores was 5.96 x 10^-7 native, below the configured 10^-5 tolerance. The full 997-item baseline was not regenerated.

## 2  GPT 4o Mini development results

Model gpt-4o-mini-2024-07-18 returned 1,200 distinct response IDs and the expected model identifier on every row. All 1,200 outputs parsed; 1,192 were usable. Each table row includes all 100 planned items, including baseline fallback.

| Dir | Strategy | BLEU | chrF++ | COMET | Delta | 95% dev CI | FB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| En to Tl | Zero shot | 36.910 | 61.240 | 85.203 | +0.761 | [+0.147, +1.608] | 0 |
| En to Tl | One shot | 37.757 | 62.087 | 85.905 | +1.463 | [+0.710, +2.396] | 0 |
| En to Tl | Reason edit | 36.052 | 60.822 | 84.698 | +0.255 | [-0.726, +1.259] | 3 |
| Tl to En | Zero shot | 47.144 | 68.470 | 87.988 | +0.870 | [+0.396, +1.425] | 0 |
| Tl to En | One shot | 46.989 | 68.790 | 88.158 | +1.039 | [+0.471, +1.662] | 0 |
| Tl to En | Reason edit | 47.408 | 68.467 | 87.736 | +0.617 | [+0.154, +1.169] | 4 |
| En to Es | Zero shot | 28.672 | 54.627 | 86.741 | +0.664 | [+0.238, +1.216] | 0 |
| En to Es | One shot | 28.260 | 54.475 | 86.695 | +0.619 | [-0.077, +1.295] | 0 |
| En to Es | Reason edit | 27.946 | 54.180 | 86.077 | +0.001 | [-0.251, +0.298] | 1 |
| Es to En | Zero shot | 30.297 | 58.418 | 87.846 | +0.018 | [-0.182, +0.194] | 0 |
| Es to En | One shot | 29.821 | 58.671 | 88.131 | +0.303 | [-0.048, +0.698] | 0 |
| Es to En | Reason edit | 29.486 | 57.846 | 87.601 | -0.228 | [-0.591, +0.084] | 0 |

Delta is edited minus split baseline in COMET points. FB is the fallback count out of 100. Confidence intervals use 10,000 paired percentile bootstrap resamples with seed 42; no confirmatory p-values or multiplicity-adjusted claims are made on dev.

The strongest En-to-Tl point estimate is retrieved one-shot (+1.463). Both Tagalog directions show positive zero-shot and one-shot point estimates, but the sample does not establish a universal resource-level advantage. Spanish-to-English changes are small and its three intervals include zero. Strategy superiority requires the predeclared main comparisons; overlapping or separate baseline intervals are not a strategy-vs-strategy test.

A post hoc influence check removes dev item 983 only for diagnosis: En-to-Tl one-shot changes from +1.463 to +1.151 points over the remaining 99 items. The primary result retains all 100. This single terminology case materially affects several strategies; it does not justify deleting the item or tuning on devtest.

## 3  Llama development results

Model meta-llama/Meta-Llama-3-8B-Instruct generated 1,200 outcomes on an A100 80 GB. Zero-shot and one-shot were usable on all 400 items each. Reason-then-edit was usable on 173/400, with 227 baseline fallbacks. The model checkpoint, prompt version and validation policy were retained from the reviewed candidate v2.

| Dir | Strategy | BLEU | chrF++ | COMET | Delta | 95% dev CI | FB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| En to Tl | Zero shot | 34.201 | 58.363 | 84.348 | -0.094 | [-1.158, +1.071] | 0 |
| En to Tl | One shot | 33.799 | 59.280 | 84.529 | +0.087 | [-0.997, +1.303] | 0 |
| En to Tl | Reason edit | 34.222 | 59.139 | 83.806 | -0.637 | [-1.405, +0.389] | 39 |
| Tl to En | Zero shot | 45.269 | 66.959 | 87.131 | +0.013 | [-0.456, +0.500] | 0 |
| Tl to En | One shot | 45.659 | 66.896 | 87.471 | +0.352 | [-0.115, +0.932] | 0 |
| Tl to En | Reason edit | 45.224 | 66.686 | 86.574 | -0.544 | [-0.959, -0.217] | 62 |
| En to Es | Zero shot | 27.125 | 53.821 | 86.431 | +0.355 | [-0.037, +0.797] | 0 |
| En to Es | One shot | 27.381 | 53.815 | 86.527 | +0.450 | [-0.050, +0.979] | 0 |
| En to Es | Reason edit | 26.558 | 53.267 | 85.864 | -0.212 | [-0.570, +0.153] | 65 |
| Es to En | Zero shot | 29.776 | 57.955 | 87.636 | -0.192 | [-0.553, +0.128] | 0 |
| Es to En | One shot | 29.942 | 57.590 | 87.783 | -0.046 | [-0.476, +0.384] | 0 |
| Es to En | Reason edit | 29.202 | 57.240 | 87.267 | -0.562 | [-1.025, -0.192] | 61 |

Reason-then-edit has negative point estimates in all four directions. The Tl-to-En and Es-to-En dev intervals exclude zero on the negative side, but these remain exploratory and are not the main experiment. The estimate describes the complete operational condition, including its failures and fallback. It does not isolate an intrinsic effect of reasoning from the effect of strict diagnostic validation.

Low observed editing under reason-then-edit cannot be interpreted as successful restraint: 56.75% of those jobs fell back to the baseline. Reporting only usable responses would condition on model success and produce a selected sample. The report therefore keeps all planned items in its primary population.

The En-to-Tl one-shot mean is +0.087 points with a wide interval. Its leave-item-983-out diagnostic becomes -0.285 points. This illustrates sensitivity in a 100-item pilot and supports keeping the full main-evaluation design rather than declaring an early strategy winner.

## 4  Validity failures and execution accounting

| Model | Strategy | N | JSON parse | Usable | Fallback |
| --- | --- | --- | --- | --- | --- |
| GPT Mini | Zero shot | 400 | 400 | 400 | 0 |
| GPT Mini | One shot | 400 | 400 | 400 | 0 |
| GPT Mini | Reason edit | 400 | 400 | 392 | 8 |
| Llama 3 | Zero shot | 400 | 400 | 400 | 0 |
| Llama 3 | One shot | 400 | 400 | 400 | 0 |
| Llama 3 | Reason edit | 400 | 399 | 173 | 227 |

All failures occurred in reason-then-edit. JSON structure and diagnostic semantics are distinct checks: vLLM or API structured decoding supplies a JSON contract; Pydantic checks unique categories, NONE exclusivity, note length and nonempty translations afterward. Neither mechanism guarantees factual correctness of a diagnostic or translation.

| Failure screen on unusable responses | Llama | GPT |
| --- | --- | --- |
| Repeated diagnostic category | 184 | 8 |
| Empty or over 25 word diagnostic note | 45 | 0 |
| NONE combined with another category | 23 | 0 |
| Diagnostic count outside one to six | 3 | 0 |
| Unparseable JSON | 1 | 0 |
| Non stop finish reason | 1 | 0 |

The screens overlap, so these rows must not be added to obtain the failure total. The one Llama unparseable response also ended abnormally. No invalid content was repaired or selectively regenerated. All raw completions and baseline fallback outcomes remain in the evidence.

One GPT response used NONE while changing only the spacing in half- miler to half-miler (Tl-to-En item 549). It passed the existing structural validators and is reported as an instruction-consistency flag, not retroactively reclassified as a fallback. No acceptance rule was changed after observing the outputs.

### Cost and reproducibility

The GPT pilot used 643,126 input tokens and 53,095 output tokens, with no cached input tokens and no recorded retries. Applying the recorded uncached rates gives an estimated token charge of $0.1283259, approximately $0.13, not an invoice or total account purchase. Six server system_fingerprint values occurred within the same dated model snapshot; they are retained in the audit. Seed and temperature settings do not establish bit-identical server behavior.

The 1,200 Llama records contain 78 unique generation batches with summed logged batch wall time of 249.83 seconds, including reused smoke records. The latest full invocation logged 96.98 seconds of model initialization separately. GPT median request wall time was 1,057 ms. GPT request latency and Llama batch-amortized timing are different measures and are not compared as isolated per-item speeds.

## 5  Editing harm and preservation screens

Improved means native COMET delta > +0.02; harmed means delta < -0.02; the inclusive middle band is [-0.02, +0.02]. A native difference of 0.02 is 2 reported COMET points. Textual editing is measured separately. These metric bands are not human quality labels or equivalence tests.

| Model | Strategy | Edited | Improve | Band | Harm | Protect over | Rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT Mini | Zero shot | 143 | 38 | 354 | 8 | 3/116 | 2.59% |
| GPT Mini | One shot | 320 | 67 | 314 | 19 | 6/116 | 5.17% |
| GPT Mini | Reason edit | 97 | 26 | 354 | 20 | 3/116 | 2.59% |
| Llama 3 | Zero shot | 260 | 37 | 331 | 32 | 9/116 | 7.76% |
| Llama 3 | One shot | 326 | 49 | 314 | 37 | 11/116 | 9.48% |
| Llama 3 | Reason edit | 158 | 8 | 344 | 48 | 16/116 | 13.79% |

Rows pool four directions descriptively, each with 400 outcomes. Protect-pool over-editing requires an original baseline score at least 0.90, a textual change, and native COMET loss exceeding 0.02. Each strategy has 116 protect observations across the four directions: En-to-Tl 22, Tl-to-En 45, En-to-Es 21 and Es-to-En 28. The rate shown uses all 116; the condition CSV also records the edited-protect denominator. No pooled inferential claim is made.

Retrieved one-shot edits more often than zero-shot in both models. GPT one-shot has more metric-harmed items than GPT zero-shot (19 versus 8 out of 400), despite larger mean gains in several directions. Improvement and protection are separate outcomes; neither the mean nor the edit rate alone answers the over-editing question.

| Heuristic screen across 1200 outcomes | Llama | GPT |
| --- | --- | --- |
| Digit multiset changed | 11 | 5 |
| Baseline digit token newly absent | 6 | 2 |
| Capitalized source token newly absent | 28 | 12 |
| Target language mismatch flag | 0 | 0 |
| Length ratio anomaly flag | 0 | 0 |

These are screening counts, not confirmed corruption rates. Three of Llama's six digit-loss flags and both GPT digit-loss flags arise from correcting the duplicated 100-foot-long [100 m] baseline in item 296 to 100-meter-long. Legitimate translated titles, transliteration, inflection and numeral scaling also trigger screens. Conversely, a predominantly English output may contain an untranslated word without a language-ID mismatch. Zero language/length flags do not establish zero semantic errors.

Only three Spanish-to-English pilot items lie below baseline COMET 0.80. Subgroup effects in that improve pool are consequently too sparse for broad conclusions. All numerical flags remain available for systematic source review in the evidence.

## 6  Source based case review

The following cases were inspected from saved source, draft, completion and reference text. They illustrate mechanisms and metric limitations; they are not independent bilingual ratings or estimates of a population error frequency. All remain in the quantitative results.

### Useful terminology correction  En to Tl item 983

The source distinguishes bird flu from its formal name avian influenza. The baseline repeats trangkaso ng ibon for both. GPT zero-shot and one-shot restore avian influenza and gain 32.361 segment COMET points; Llama reason-then-edit gains 36.763. This case explains part of the pilot mean and is disclosed in the influence analysis.

### Name corruption despite a valid schema  Tl to En item 849

Llama reason-then-edit changes Hangi Meal to The Last Meal and asserts that a different name is correct. The saved baseline COMET is 0.916; the edited score is 0.776, a loss of 13.998 points. The response is schema-valid and belongs to the protect-pool over-edit count. Valid JSON and a plausible-looking diagnosis do not establish semantic fidelity.

### Unsupported placeholder  En to Es item 233

The source and draft retain Aleisk. A schema-valid Llama reason-then-edit response replaces it with [correct city name] after claiming that the source city is invalid. The output loses 9.213 COMET points. The visible placeholder shows that structural validity alone cannot establish a usable scientific translation in the ordinary linguistic sense; usable in the tables means operational validator acceptance.

### Digit corruption with a metric gain  En to Tl item 429

Llama one-shot changes the source-backed area 23,764 to 27,874 square kilometres. This is a concrete unsupported numeric change, yet its COMET score increases by 0.950 points. A primary neural metric can miss a factual corruption; the preservation analysis is therefore necessary even when mean quality increases.

### Metric harm without obvious meaning loss  En to Es item 825

GPT one-shot rewrites a bajo costo as de manera económica and adds ya sea in an otherwise source-consistent sentence about low-cost travel. COMET falls by 21.483 points. Inspection does not reveal a clear semantic loss commensurate with that penalty. It is retained as a metric-harmed item and treated as a case requiring linguistic confirmation, not automatically called hallucination.

### Meaning changing reinterpretation  Es to En item 81

GPT zero-shot changes the source relationship prima del Velocirráptor from a cousin of the Velociraptor to prior to the Velociraptor. The relationship becomes temporal and COMET drops 6.057 points. This is an example of a fluent edit introducing a source interpretation error.

## 7  Comparison with the final ICAI paper

The supplied 16-page paper is Large Language Model-Based Automatic Post-Editing for Test-Time Domain Adaptation in Neural Machine Translation, by Benyamin Ahmadnia, Shazan Mohammed, Sahar Hooshmand and Li Zhou. The comparison below uses its stated methods and experiments; its underlying datasets, code and reported results were not independently reproduced here.

| Dimension | ICAI paper | Norris study |
| --- | --- | --- |
| Objective and data | Four EN-to-DE domain-adaptation corpora; 20k/2k/2k split per corpus (p. 6). | En/Tl and En/Es in four directions; FLORES+ dev/devtest; gains and over-editing. |
| Baseline and editors | OPUS-MT EN-DE and GPT-4 Turbo snapshot (pp. 4, 6-7). | Split NLLB-200 3.3B; GPT-4o Mini and Llama 3 8B. |
| Substantive shared method | Frozen NMT anchor plus source-conditioned LLM editing; no extra training (pp. 3-4). | Same broad APE architecture; cite as established prior work. |
| Substantive shared retrieval | Multilingual Sentence-BERT cosine top-3 exemplars (p. 4). | LaBSE/FAISS top-1 dev exemplar with pilot and duplicate-source exclusions. |
| Prompt contrast | No exemplars; exemplars; exemplars plus a second terminology-verification call (pp. 4-7). | Zero shot; one shot; single-call diagnostic reason-then-edit. No domain cue or second verifier. |
| Evaluation | BLEU, COMET, ablation BERTScore, human ratings and terminology/hallucination analysis (pp. 8-13). | COMET, BLEU, chrF++, protect-pool harm, schema/fallback accounting; no external raters. |
| Research extension | Lower-resource pairs, NLLB and open LLMs identified as future work (p. 14). | Empirical extension addressing these axes, with explicit failure and over-editing measurement. |

The overlap is substantial at the level of NMT anchoring and semantic exemplar retrieval. A different encoder, exemplar count or output schema does not make retrieval-based APE a new invention. The separate overlap document provides a page-level crosswalk and proposed manuscript disclosure. J.UCS is excluded from the comparison as instructed.

Recommended positioning: Norris evaluates established APE components under a distinct four-direction, two-editor design with a stronger baseline, resource/direction analysis, strict failure accounting and protect-pool over-editing. It should not claim the first hybrid NMT-LLM pipeline, first semantic exemplar retrieval, or first training-free APE method. No direct numeric superiority comparison with ICAI is justified because data, models and evaluation differ.

## 8  Reviewed candidate configuration

The exact candidate snapshot is included as Reviewed_Candidate_Configuration.json. Its status is reviewed candidate pending PI decisions, and freeze_declared is false. No model, prompt, validation rule, fallback policy or sample was silently changed after the pilot.

| Setting | Measured configuration |
| --- | --- |
| Prompts | candidate_v2_explicit_diagnostics_not_frozen; exact system/instruction bytes and JSON schemas retained. |
| Llama decoding | BF16, temperature 0, top_p 1, top_k -1, seed 42, output cap 1024, context 8192. |
| Llama engine | vLLM 0.11.2, GPU utilization .70, up to 16 sequences, eager execution and prefix caching. |
| GPT decoding | Exact gpt-4o-mini-2024-07-18; Chat Completions; strict JSON schema, temperature 0, top_p 1, seed 42, output cap 1024, store false. |
| GPT execution | Four workers, four request starts per second; five HTTP retries allowed; none used. Transport uncertainty stops rather than repeating a possible paid call. |
| Retrieval | 997 rows per source language, normalized float32 LaBSE, exact FAISS inner product/cosine, top-1, deterministic ID tie break; 100 pilot IDs excluded. |
| Output policy | Reject duplicate JSON keys, schema failures, empty translations and abnormal completion. Retain raw output and use the unchanged baseline draft; no selective content repair. |

| Artifact | Pinned revision |
| --- | --- |
| NLLB-200 3.3B | 1a07f7d195896b2114afcb79b7b57ab512e7b43e |
| LaBSE | 836121a0533e5664b21c7aacc5d22951f2b8b25b |
| Llama 3 8B | 8afb486c1db24fe5011ec46dfbe5b5dccdb575c2 |
| COMET-22 | 2760a223ac957f30acfb18c8aa649b01cf1d75f2 |

Generation and evaluation remain isolated environments. Llama used Python 3.11.17, torch metadata 2.9.0 and Transformers 4.57.1; evaluation used torch 2.6.0+cu124, Transformers 4.49.0, unbabel-comet 2.2.7, NumPy 1.26.4 and SacreBLEU 2.6.0. Full resolved requirements and the COMET encoder configuration commit are in the raw evidence.

BLEU uses mixed case, 13a tokenization and exponential smoothing. chrF++ uses character order 6, word order 2 and beta 2. COMET native segment scores are retained alongside the x100 reporting scale. Source, hypothesis and reference determine every score-cache key together with the scoring configuration.

## 9  Numerical audit and acceptance disposition

The independent audit completed the following checks. These checks support the numbers and provenance in this report; they do not turn automatic flags into gold linguistic judgments.

• Prepared configuration and all preparation/code hashes; analysis signature

• 1200 unique prompt jobs, 400 offline query rows, query-field/reference isolation

• All 400 nearest-neighbor links independently reconstructed; all pilot IDs and duplicate sources excluded

• All 2400 raw-record hashes, prompt lineage, schema/fallback decisions; exact GPT snapshot; unique responses and usage accounting

• 1492 exact source-hypothesis-reference score-cache keys; all segment deltas, preservation flags and baseline recheck

• All 24 condition means, counts, editing/harm/protect denominators, 10000-resample CIs, and BLEU/chrF++ values independently recomputed

The audit independently recomputed BLEU and chrF++ from raw text, all 24 COMET means and paired intervals from the supplied segment scores, and the exact score-triplet alignment. It did not rerun neural COMET inference. The supplied Colab evaluator independently rechecked all 400 pilot baselines. Language-ID flags were retained from the pinned langdetect run rather than regenerated in this report review.

### Decisions brought to the PI before freeze

1. Review the substantial ICAI anchoring/retrieval overlap and the proposed contribution boundary, as required by the September 24 instruction. This is a disclosure and positioning decision; the current comparison does not claim the shared methods as new.

2. Confirm the disposition of reason-then-edit. The recommended measured configuration retains candidate v2, all three strategies and the original strict fallback policy, with its high Llama failure rate prominently reported. If the diagnostic contract is redesigned or a condition is removed, document that decision and validate the affected dev conditions before freeze.

After those items are resolved, record the final protocol configuration and its hashes, update the repository, and proceed under the PI's Phase 3 acceptance instructions. The approved-in-principle Phase 4/5 plan is not treated here as permission to start the main devtest run before those steps. No new main-experiment output, devtest score, Overleaf edit or remote repository commit is claimed in this report.

### Artifacts and remaining limits

The companion package contains the editable report, page-level ICAI audit, reviewed candidate snapshot, condition CSV, numeric segment scores, independent audit result and script, and a pilot LaTeX table for the existing ICNLP manuscript. The original 46 MB full-pilot evidence ZIP remains the authority for raw outputs and run logs. Store it privately; do not publish benchmark text or credentials.

The current evidence establishes Norris-only run paths and provenance but does not include ICAI or TRACE-MT repositories for a byte-level cross-project audit. The earlier original split-generation cell was not recovered in this review; its documented specification and output hashes remain available from the baseline evidence. These source-archival limits are retained rather than described as resolved.

Primary evidence analysis signature  9d6830a0b9c7cc97e2b372c78c2c700734fd5cf65ab30e6177e7ae8d531ddc90
