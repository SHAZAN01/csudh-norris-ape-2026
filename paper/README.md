# ICNLP development manuscript

Main file: `conference_101719.tex`, matching the existing shared Overleaf IEEEtran template. Compile with pdfLaTeX, BibTeX, then pdfLaTeX twice. This is a working draft with completed development pilot evidence, not a submission-ready main-results paper. The project author block is deliberately provisional; the PI must confirm the final byline, order, affiliations, and funding.

The existing Overleaf project remains the master manuscript workspace. Upload these files into that project; do not create a separate project. Preserve its original template files/history. Set `conference_101719.tex` as the main document if needed. IEEEtran class and bibliography style are standard on Overleaf. The official conference template was checked at https://icnlp.net/sub.html on 19 October 2026; it specifies 4–5 pages without additional page charges and rejects papers above 10 pages. The current working draft includes development tables that can move to supplementary material during final editing; do not apply the old ACL 8-pages-plus-references assumption.

Sections 1–4 contain verified framing, related work, methods and evaluation design. Sections 5–6 report only the actual dev pilot. Ethics, limitations and a development conclusion are included. Main results and final conclusions must be revised after the frozen Phase 4/5 experiment.

Tables are generated from the numeric evidence by `scripts/update_manuscript_tables.py`; do not hand-edit their numbers. The manuscript audit checks exact table regeneration, cited BibTeX keys, freeze status, and the numeric claims linked in `claims_manifest.json`. It does not certify every number in arbitrary prose or validate the scientific truth of external references.

Open items before submission: PI overlap disposition; diagnostic-contract decision; final freeze including test contrasts/multiplicity/retrieval pool; main experiment and analysis; final author list; ICAI proceedings metadata; references refreshed for related work; venue disclosure and formatting checks. `SOURCE_VERIFICATION.md` records verified source URLs and remaining limits.


## Rebuild and verify

From the repository root:

```bash
python scripts/update_manuscript_tables.py
python scripts/generate_pilot_figures.py
python scripts/audit_manuscript.py
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build conference_101719.tex
```

The numeric audit uses only the Python standard library. Figure generation additionally needs NumPy and Matplotlib; the reviewed render used NumPy 2.3.5 and Matplotlib 3.10.8. The generation/evaluation experiment environments remain separately pinned in the candidate snapshot. `src/analysis/audit_manuscript.py` and `src/analysis/generate_plots.py` contain the implementations. The plot is an empirical CDF, which preserves zero-change atoms rather than smoothing fallback into a density.

The reviewed development PDF is seven pages including references and its reproducibility appendix. It is within the venue's ten-page ceiling, but exceeds the five-page no-additional-charge range. This is a development draft; final length and any extra-page charges must be settled before submission. All 24 pilot rows are retained for review and can be relocated when integrating main results.

## Existing Overleaf project

Use the project already shared by the PI. Its screenshot shows the IEEEtran template and `conference_101719.tex`. Preserve the original template/history. The supplied compiled PDF is a local verification, not proof of a successful live Overleaf upload. Live synchronization is pending authenticated project access. No new project, byline approval or submission is implied by this package.
