# ICNLP manuscript (working draft, 23 October 2026)

Main file: `conference_101719.tex` (IEEEtran, matching the shared Overleaf template). ICNLP: 4–5 pages without extra charge; target **5 pages including references**.

Structure is final: Abstract, Introduction (RQs verbatim from `config/frozen/protocol_freeze.json`), Related Work and ICAI contribution boundary, Method, Experimental Protocol (pilot as one labelled development-evidence paragraph), Held-out Results, Discussion, Limitations and Ethics, Conclusion.

* Red `[PENDING: ...]` markers show text that must be written from Phase 4/5 evidence only. Final mode of the audit fails while any remain.
* `generated/` is written by `src/evaluation/evaluate_main_experiments.py --repo`; never hand-edit. Until it exists, `tables/main_results_placeholder.tex` shows the final layout.
* Figures for the held-out results come from `src/analysis/generate_main_figures.py` (copy `fig_bands.pdf` into `figures/`).
* The 19 October development draft and its pilot tables are archived in `legacy_dev/` and `tables/pilot_*.tex` (not part of the main text).
* ICAI reference is "to appear"; update metadata when published (PI to confirm).

Build: `pdflatex`, `bibtex`, `pdflatex` ×2 (or Overleaf). Audit: `python scripts/audit_manuscript.py` (draft) and `python scripts/audit_manuscript.py --final --phase5-results <main_results.json>` (submission).
