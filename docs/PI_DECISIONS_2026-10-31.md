# PI decisions received 31 October 2026, and how they are applied

| # | Decision | Applied in |
|---|---|---|
| 1 | Approves the revised reason-then-edit contract, the Phase 3 protocol freeze, and the completed Phase 4 and Phase 5 work. | `config/phase3/status.json`; README status table |
| 2 | Approves the S0 reconstruction disposition (Report 3.2 §5). The limitation stays documented: segmentation and the unsplit baseline were reproduced exactly; the reconstructed fragment generation reproduced 412/421 multi-sentence development translations. The earlier development baseline is not regenerated. | Manuscript §IV (Freeze) and §VII (Limitations); both numbers audited from `docs/phase3/evidence/rte_v3/gate_dev_generation.json` |
| 3 | No external Tagalog or Spanish raters, no human-participant evaluation, no IRB process. The case analysis stays a source/reference-based qualitative inspection. | Manuscript Discussion wording; `docs/phase5/evidence/source_review_summary.json` note; the proposed Tagalog verification is withdrawn |
| 4 | Anonymous submission: the author block is blank. | `paper/conference_101719.tex`; anonymity check in `src/analysis/audit_manuscript.py` (fails on names, affiliation, location hints, repository links, first-person references to the ICAI paper, internal notes in the bibliography) |
| 5 | Held-out Phase 5 results drive the Abstract, Results, Discussion and Conclusions and Future Work; pilot findings only where needed to explain protocol development. | Pilot numbers removed from the Discussion; they remain only in §IV (protocol revision); section retitled "Conclusions and Future Work" |
| 6 | Schedule: complete manuscript 20 November; submission-ready 24 November; handoff 26 November; PI review and submission 26–30 November. | `docs/SCHEDULE_AND_REPORTS.md` |
| 7 | Phase 4/5 branch may be merged into `main`, preserving the frozen protocol and result history and keeping benchmark text and model outputs out of the public repository. | Fast-forward merge (no history rewritten); `scripts/audit_public_files.py` passes |

Supersedes: Report 5 §10 (Tagalog judgments "to be confirmed by a Tagalog speaker") and §11 (S0 disposition awaiting acknowledgement); Report 5.1 §12 is updated accordingly.
