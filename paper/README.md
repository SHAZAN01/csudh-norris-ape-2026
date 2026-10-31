# ICNLP manuscript (anonymous working draft, 31 October 2026)

Main file: `conference_101719.tex` (IEEEtran, matching the shared Overleaf template). ICNLP: 4–5 pages without extra charge; target **5 pages including references**.

Structure is final: Abstract, Introduction (RQs verbatim from `config/frozen/protocol_freeze.json`), Related Work and ICAI contribution boundary, Method, Experimental Protocol (pilot only as the protocol-development paragraph), Held-out Results, Discussion, Limitations and Ethics, Conclusions and Future Work. The author block is blank (anonymous submission); the audit enforces anonymity.

* Red `[PENDING: ...]` markers show text that must be written from Phase 4/5 evidence only. Final mode of the audit fails while any remain.
* `generated/` is written by `src/evaluation/evaluate_main_experiments.py --repo`; never hand-edit. Until it exists, `tables/main_results_placeholder.tex` shows the final layout.
* Figures for the held-out results come from `src/analysis/generate_main_figures.py` (copy `fig_bands.pdf` into `figures/`).
* The 19 October development draft and its pilot tables are archived in `legacy_dev/` and `tables/pilot_*.tex` (not part of the main text).
* ICAI reference is "to appear", cited in the third person; update metadata when published.

Build: `pdflatex`, `bibtex`, `pdflatex` ×2 (or Overleaf). Audit: `python scripts/audit_manuscript.py` (draft) and `python scripts/audit_manuscript.py --final --phase5-results <main_results.json>` (submission).
