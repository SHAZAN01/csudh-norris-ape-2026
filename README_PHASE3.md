# Norris Phase 3 progress

Report date: 17 October 2026. **Phase 3 is open; the protocol is not frozen.**

The sentence split NLLB baseline was generated and evaluated on **dev only**.
Candidate prompts, retrieval and a Llama runner are implemented and locally tested.
Actual LaBSE indexing and Llama smoke/full pilot evidence are still pending.
No LLM post editing improvement or Phase 3 devtest result is claimed.

- [Report 3](docs/phase3/Norris_Phase_Report_3.pdf)
- [Editable report](docs/phase3/Norris_Phase_Report_3.docx)
- [Markdown report](docs/phase3/Norris_Phase_Report_3.md)
- [Current status](config/phase3/status.json)
- [Execution and next steps](docs/phase3/RUNBOOK.md)
- [Numeric baseline evidence](docs/phase3/evidence/evaluation/dev_baseline_metrics.json)

## Run next in Colab Pro

Open `notebooks/phase3/02_prompts_retrieval_llama.ipynb` on an A100 80 GB.
Keep the existing Drive root `/content/drive/MyDrive/norris`.
Use Colab Secrets for `HF_TOKEN`; never paste tokens into notebook source.
Run all cells to prepare retrieval and run the **24 output smoke check**.
The default notebook does not run the full 1,200 output Llama pilot.
Inspect the downloaded smoke evidence before proceeding to the full stage.
The separate resume evaluator notebook validates and reuses completed scores.

No NLLB regeneration is needed. Raw FLORES text, generations, vectors, weights and
credentials must stay out of Git. This update contains numeric score caches only.

## Scope

English ↔ Tagalog and English ↔ standard Spanish, four directions, three strategies.
No external human raters; no heritage Spanish or dialect specific claim.
Use the existing ICNLP Overleaf manuscript project. ICAI work is separate.
