# Norris Phase 3 — measured development pilots

Updated 19 October 2026. Empirical pilot work is complete; Phase 3 sign-off and
protocol freeze remain pending. Main devtest experiments have not started.

- [Updated Report 3 PDF](docs/phase3/Norris_Phase_Report_3.pdf)
- [Editable report](docs/phase3/Norris_Phase_Report_3.docx)
- [Markdown report](docs/phase3/Norris_Phase_Report_3.md)
- [All 24 pilot conditions](docs/phase3/evidence/pilot/pilot_condition_results.csv)
- [Independent numeric audit](docs/phase3/evidence/pilot/independent_numeric_audit.json)
- [Measured candidate configuration](config/phase3/Reviewed_Candidate_Configuration.json)
- [ICAI overlap review](docs/phase3/ORIGINALITY_OVERLAP_AUDIT.md)
- [Development manuscript](paper/README.md)
- [Remaining actions](docs/phase3/RUNBOOK.md)

Actual retrieval, 24 smoke outcomes, and 1,200 full outcomes per editor are evidenced.
The same 100 aligned IDs are repeated over conditions: 2,400 outcomes are not
2,400 independent sentences. GPT one-shot English→Tagalog gains 1.463 COMET points
(descriptive 95% dev interval [0.710,2.396]); Llama reason-then-edit falls back on
227/400 outcomes and GPT on 8/400. All planned outcomes remain in the results.

Next: PI overlap/contract review, final freeze and acceptance, then Phases 4/5.
Use the existing shared ICNLP Overleaf project, with IEEEtran rather than the
ACL assumption in the older role text. No new project is needed. Raw benchmark
text, full generations, model weights, keys and private API records remain excluded.
