# ICNLP manuscript (anonymous working draft, 31 October 2026)

Main file: `conference_101719.tex` (IEEEtran, matching the shared Overleaf template). ICNLP: 4–5 pages without extra charge; target **5 pages including references**.

Structure (31 October revision): Abstract (problem, design, results, implication); Introduction (problem, approach, RQs verbatim from `config/frozen/protocol_freeze.json`, contribution boundary, contributions, central finding); Related Work and Research Gap; Study Design and Systems; Data, Protocol, and Analysis (pilot only as the protocol-development paragraph); Held-out Results (overall, RQ1–RQ4, robustness, summary); Discussion (preservation, decomposition with Fig. 2, reasoning, qualitative inspection, implications); Limitations and Ethical Considerations; Conclusions and Future Work. The author block is blank (anonymous submission); the audit enforces anonymity.

* Red `[PENDING: ...]` markers show text that must be written from Phase 4/5 evidence only. Final mode of the audit fails while any remain.
* `generated/` is written by `src/evaluation/evaluate_main_experiments.py --repo`; never hand-edit. Until it exists, `tables/main_results_placeholder.tex` shows the final layout.
* Figures for the held-out results come from `src/analysis/generate_main_figures.py` (copy `fig_bands.pdf` into `figures/`).
* The 19 October development draft and its pilot tables are archived in `legacy_dev/` and `tables/pilot_*.tex` (not part of the main text).
* ICAI reference is "to appear", cited in the third person; update metadata when published.

Build: `pdflatex`, `bibtex`, `pdflatex` ×2 (or Overleaf). Audit: `python scripts/audit_manuscript.py` (draft) and `python scripts/audit_manuscript.py --final --phase5-results <main_results.json>` (submission).
