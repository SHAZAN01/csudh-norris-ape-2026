# Schedule to the 24 November full draft, and report contents

Target: **full paper essentially complete by Tue 24 Nov 2026**; 25–30 Nov reserved for PI review, revision and submission (ICNLP deadline 30 Nov). Page budget: 5 pages including references (layout check with real-size tables and figure: 5 pages).

| Dates | Work | Output |
|---|---|---|
| Oct 23–24 | Notebook 03: RTE v3 dev rerun (both models), gate, splitter dev gates, freeze | Report 3.2 freeze package → PI |
| Oct 25–28 | Notebook phase4/01: S0 devtest, jobs, smoke, Llama full, GPT full (may span 2 days: Tier-1 RPD) | Report 4 (by Oct 29) |
| Oct 29–Nov 4 | Notebook phase5/01: evaluation, tables, figures; source review of flagged held-out cases | Report 5 (by Nov 6) |
| Oct 23–Nov 6 (parallel) | Manuscript: frozen sections (Intro, Related Work, Method, Protocol, Limitations) finalised now | Overleaf sync |
| Nov 6–14 | Write Results/Discussion/Abstract/Conclusion from Phase 5 only; remove all `\pending` | Draft v1 |
| Nov 15–19 | 7.txt: numerical audit (`--final`), reviewer-objection memo, figure polish, 5-page fit | Draft v2 |
| Nov 20–24 | 8.txt: environment files, README reproduction guide, repo sanitisation, executive summary | **Full draft to PI, Nov 24** |

## PI manuscript points → actions

1. **RQs aligned with the frozen protocol.** RQ text is stored verbatim in the freeze manifest; `audit_manuscript.py` fails if the introduction differs. No new claims are added during drafting.
2. **ICAI boundary.** Anchoring and semantic exemplar retrieval cited to ICAI as established; the audit checks the boundary sentence and rejects novelty wording.
3. **ICAI citation metadata.** Entry is `@inproceedings`, "to appear"; replace publisher/pages/DOI when the proceedings appear (check weekly; PI to confirm before submission).
4. **Pilot = development evidence.** The pilot is one labelled paragraph in §IV; Abstract, Results, Discussion and Conclusion are rewritten from held-out Phase 4/5 evidence only (`\pending` markers block final mode).
5. **Prioritise held-out results.** The 24-row pilot table, pilot harm table and pilot ECDF were removed from the main text (kept in `paper/tables/` and the repo). Main table, over-editing table and one figure are generated from Phase 5 records.

## Report 4 (Phase 4) contents
Freeze binding and code-hash check; S0 devtest generation (unsplit exact match to Phase 2 archive, multi-segment counts, fragments, timing); retrieval (pool, duplicate exclusions, similarity distribution, embedding reproduction vs pilot); job preparation (12,144 jobs, reference-leak check); smoke results; execution per model (records, usable, fallback, failure classes, retries, tokens, cost, latency definitions, batches, system fingerprints); completion checks; deviations/incidents; nothing scored.

## Report 5 (Phase 5) contents
Coverage audit; metric signatures and COMET provenance; main table (24 conditions + S0 + unsplit diagnostic); F1 and F2 with raw and Holm p; practical-band flags; pool-stratified deltas (RQ1); direction comparison (RQ4); bands, edit rates, edit distance; protect-pool over-editing with sensitivity (RQ3); failure classes; preservation screens with baseline rates; source-reviewed cases; runtime/cost; limitations; manuscript integration checklist.
