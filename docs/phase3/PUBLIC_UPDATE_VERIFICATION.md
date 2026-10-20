# Public update verification — 19 October 2026

This update publishes measured development evidence and a working ICNLP manuscript. Phase 3 sign-off and protocol freeze remain pending. No main devtest generation or scoring was performed for this update.

## Completed checks

- The complete private full-pilot audit passed: preparation/code/raw-record hashes, 1,200 jobs per model, all 400 retrieval selections, reference isolation, all fallback decisions, 1,492 exact score-cache keys, 24 metric rows and 10,000-resample intervals. BLEU/chrF++ were recomputed from raw text; COMET inference and language ID were not rerun.
- The public manuscript audit passed: 2,400 numeric rows, the 24-condition matrix, aligned IDs, exact generated table bytes, specified inline claims, 18 cited bibliography keys, input-file existence and unfrozen status.
- The existing pinned Pydantic 2.12.3 synthetic tests passed: prompt/reference isolation, retrieval exclusions/ties, structural validation, fallback and record-integrity behavior. Local Python files compiled.
- The seven-page IEEEtran PDF compiled with pdfLaTeX/BibTeX through latexmk. No unresolved references/citations or overfull boxes remained. All pages were visually inspected. Pages 1–5 were byte-identical across the final layout refinement; final pages 6–7 were separately inspected.
- Public tracked/non-ignored files passed credential/invitation/personal-home-path and prohibited raw-artifact screens. This is a current-tree screen, not a claim that all historical Git commits have been audited.

## Publication boundaries

Only code, prompts/configuration, reports, source-verification notes, numeric evidence, manuscript sources and compiled manuscript/figure outputs are included. Full benchmark text, full model/API records, request identifiers, vectors/indexes, model weights, credentials and invitation screenshots/links are excluded. Short source-based examples in the scientific report are illustrative, not a release of the raw benchmark.

The existing shared Overleaf project remains the master manuscript workspace. Its screenshot confirms IEEEtran and `conference_101719.tex`. A local compiled manuscript is not evidence of a live project edit. Authenticated Overleaf access is required for synchronization and live compilation. The provisional project author block is not an approved submission byline.

## Before the main experiment

See `PROTOCOL_DECISIONS_PENDING.md`: disclose the ICAI overlap, resolve the diagnostic condition, specify main retrieval eligibility and statistical contrasts, reconcile screening/metric settings, then record the exact freeze and PI acceptance. The manuscript's results and conclusion currently describe the development pilot only.
