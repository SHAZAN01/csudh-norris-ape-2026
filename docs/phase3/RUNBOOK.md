# Phase 3 execution and acceptance

## Completed evidence

Generation: `phase3_dev_f4a3af94ba1e72fd`; evaluation: `6d6e94fc2a8d3d8f`.
There are 997 dev IDs per direction, 7,976 final baseline records across two
conditions, and 377 changed hypotheses. All 3,988 unsplit hypotheses and their
rechecked COMET scores reproduced Phase 2 exactly.

The exact original split generation cell is absent from the supplied evidence.
Its run specification, segmentation fingerprint and output hashes are retained.
`evidence/code/generating_evaluator_source.py` is the scorer that produced the
evaluation signature, while `src/phase3/evaluation` contains the resume evaluator.
These must not be confused with the missing translation generator.

## Current candidate

Prompts and schemas: `src/phase3/post_editing/pilot_common.py`.
Preparation: `prepare_pilot.py`; execution: `run_llama_pilot.py`.
Use the Colab notebook, which restores the exact tested embedded modules into a
clean runtime directory and installs isolated pinned Python 3.11 environments.
The sibling `baseline_io.py` preserves the shared evaluator's exact validation
logic so the snapshot remains compatible; it is intentionally not refactored here.

The notebook resolves and pins gated `meta-llama/Meta-Llama-3-8B-Instruct`
and `sentence-transformers/LaBSE` revisions before execution. Access failures
stop execution; the notebook does not substitute another model.

1. Run `02_prompts_retrieval_llama.ipynb` with an A100 80 GB and Drive mounted.
2. It validates saved baselines, creates LaBSE/FAISS artifacts and 1,200 jobs,
   then runs 24 smoke outputs. Save the downloaded smoke evidence ZIP.
3. Review raw responses, retrieval exclusions, source revisions, token limits,
   JSON/schema/usable counts and fallbacks before the full pilot.
4. Once the smoke evidence is reviewed, run the saved runner with the same
   `--pointer` path shown by the notebook and `--stage full` instead of `smoke`.
   Do not guess a candidate hash or pointer path. Full stage resume reuses
   hash verified completed jobs; it never overwrites a different configuration.
5. Score the 1,200 Llama outputs on dev and implement summaries by direction and
   strategy: valid JSON, valid schema, usable output, fallback, edit frequency,
   COMET delta, strong baseline over editing, number/name flags and language flags.
   This pilot analysis module is still to be implemented. Keep unusable outputs in
   the denominator; label heuristic flags rather than treating them as gold errors.
6. Implement and execute the equivalent 1,200 GPT 4o Mini jobs when API access is
   available, or obtain a documented PI scope decision. No GPT runner is included yet.
7. Freeze all prompt bytes, schemas, revisions, retrieval and failure policies,
   decoding/chat templates, sample IDs and analysis definitions in a signed off
   protocol manifest. The current `candidate_v1_not_frozen` is not that manifest.

The shared sample has 100 aligned dev IDs per direction, seed 42. All 100 IDs are
excluded globally from retrieved demonstrations; exact duplicate source texts are
also excluded. Query references never enter model inputs. A nonpilot example's
gold reference may appear only as the solved retrieved demonstration.

## Efficient A100 use

Do not regenerate completed NLLB outputs or rescore identical COMET triplets.
Download and install once per session; use the independent retrieval environment
before loading Llama. The runner uses BF16, temperature 0, 16 sequences, prefix
caching and eager execution. Record startup separately from inference. Native
per request latency may be unavailable; batch amortized time is explicitly labeled.
The 24 output smoke check is the next runtime validation, not a promised success.

## Local checks

Use a separate environment; a GPU is not required for these checks:

```bash
python3 -m venv .venv-phase3-check
.venv-phase3-check/bin/pip install -r config/phase3/test_requirements.txt
.venv-phase3-check/bin/python tests/phase3/test_pilot.py
.venv-phase3-check/bin/python tests/phase3/audit_evidence.py
```

Synthetic tests do not establish real inference success. The evidence audit
recomputes whole-dev COMET means, paired bootstrap intervals, threshold bands and
numeric source/cache hashes. It cannot independently rescore BLEU/chrF++ without
private raw hypotheses, nor reconstruct multi sentence membership without raw rows.

## After Phase 3

Phase 4 target: 1,012 devtest IDs × four directions × two post editors × three
strategies = 24,288 outputs, conditional on the approved final system matrix.
Do not score devtest before freeze. Phase 5 performs the planned main evaluation
and paired statistical analyses. Use the existing ICNLP Overleaf project, adding
the included dev table only with its exploratory caption and scale definition.
