# Protocol decisions before the freeze — disposition record

Updated 23 October 2026 after the PI's Phase 3 acceptance message (22 October 2026).

| # | Item | Disposition | Where recorded |
|---|---|---|---|
| 1 | ICAI contribution boundary | **Approved by PI.** Frozen-NMT anchoring and semantic exemplar retrieval are cited as established prior methodology (ICAI). Norris contributions: different empirical setting, four directions, stronger split baseline, two-editor comparison, explicit failure accounting, over-editing/preservation analysis. | `ORIGINALITY_OVERLAP_AUDIT.md`, manuscript §II-C, freeze `pi_instructions` |
| 2 | Reason-then-edit contract | **Revised per PI:** minimal contract rte_v3 (`diagnosis` → `edited_translation`), affected dev conditions rerun for both models under a predeclared reliability gate. If the gate fails, the PI decides retain-as-failure vs remove. | `RTE_CONTRACT_REVISION.md`, notebook 03 |
| 3 | Baseline | **Approved:** sentence-split NLLB primary (S0), unsplit diagnostic. Splitter reconstructed from the recorded run spec and accepted only by exact dev reproduction (segmentation and translation gates). | `src/baselines/`, freeze `baseline` |
| 4 | Held-out retrieval pool | All 997 dev IDs, exact stripped-source duplicates of the query excluded, smallest-ID tie break (as declared in the approved Phase 4/5 plan). | `prepare_main_jobs.py`, freeze `retrieval_main` |
| 5 | Statistics | F1: 24 PE-vs-S0 tests; F2: 24 strategy tests (one−zero, reason−zero, reason−one); two-sided centered paired bootstrap, B=10,000, seed 42; percentile CIs; Holm per family α=.05; ±0.5-point practical band flag; nonsignificant = inconclusive. Validated on synthetic fixtures. | `src/evaluation/norris_stats.py`, `tests/phase5/test_stats.py`, freeze `evaluation` |
| 6 | Roadmap discrepancies | langdetect 1.0.9 (not fastText); chrF++ word order 2; native thresholds ±0.02; protect ≥.90 / improve <.80 on devtest S0; harm and protect-pool over-editing reported separately; sensitivity .01/.05. | freeze `evaluation`, `deviations_from_roadmap` |
| 7 | Freeze artifact | `config/frozen/protocol_freeze.json` built by `src/freeze/build_freeze_manifest.py` only after the gates; records RQs verbatim, prompts, schemas, code hashes and git commit. | `config/frozen/` |
