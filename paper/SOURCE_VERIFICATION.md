# Manuscript source verification

Checked 19 October 2026. This is a focused source check for the working manuscript, not a systematic literature review. Bibliographic keys resolve to the primary sources below. No main Norris result is taken from an external source.

| Key | Primary source | Verified use |
|---|---|---|
| raunak2023 | https://aclanthology.org/2023.findings-emnlp.804/ | GPT-4 APE and hallucinated-edit risk; title, authors, venue and DOI |
| ki2024 | https://aclanthology.org/2024.findings-naacl.265/ | External MQM feedback, prompting/fine-tuning; not self-generated gold diagnostics |
| treviso2024 | https://aclanthology.org/2024.findings-emnlp.892/ | xTower explanations/corrections and expert explanation assessment |
| velazquez2025 | https://aclanthology.org/2025.acl-long.1569/ | LangMark human-post-edit triplets, including Spanish; not Norris data |
| vilar2023 | https://aclanthology.org/2023.acl-long.859/ | Translation prompting and example selection |
| feng2022 | https://aclanthology.org/2022.acl-long.62/ | LaBSE multilingual sentence representations |
| nllb2022 | https://arxiv.org/abs/2207.04672 | NLLB/FLORES-200 original work; actual 3.3B revision comes from run evidence |
| floresplus | https://huggingface.co/datasets/openlanguagedata/flores_plus | OLDI maintenance, data origins, 997/1012 splits and evaluation use |
| papineni2002 | https://aclanthology.org/P02-1040/ | BLEU |
| popovic2015 | https://aclanthology.org/W15-3049/ | chrF |
| popovic2017 | https://aclanthology.org/W17-4770/ | chrF++; the measured implementation uses word order 2 |
| post2018 | https://aclanthology.org/W18-6319/ | Reproducible scoring and signatures |
| rei2020 | https://aclanthology.org/2020.emnlp-main.213/ | COMET framework |
| rei2022 | https://aclanthology.org/2022.wmt-1.52/ | COMET-22 paper; not an assertion that the full ensemble was run |
| cometmodel | https://huggingface.co/Unbabel/wmt22-comet-da | Exact reference-based checkpoint used in Norris |
| meta2024 | https://github.com/meta-llama/llama3/blob/main/MODEL_CARD.md | Original April 2024 Llama 3; not substituted by Llama 3.1 |
| openai2024 | https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/ | Model introduction and recorded launch token rates; not an account invoice |
| ahmadnia2026icai | Supplied final ICAI manuscript, pp. 3–14; see overlap audit | Title/authors and described methods checked; publisher, DOI, pages and formal proceedings status remain unverified |

## Template correction

The actual project screenshot uses `conference_101719.tex` and IEEEtran. The official instructions at https://icnlp.net/sub.html specify 4–5 pages without additional page charges, reject papers over 10 pages and link a LaTeX conference template. The older role-file assumption of an ACL eight-page main text is therefore not used. Final page budget and any extra-page charge require confirmation before submission. The downloaded IEEEtran files retain their original notices.

## Remaining bibliographic limits

The ICAI entry is explicitly a supplied manuscript, not a fabricated proceedings citation. The current FLORES+ bibliography file is access-controlled and was not available without accepting dataset access conditions; no new access agreement was accepted here. The dataset card and original NLLB reference are cited. Reconcile the maintainers' recommended citations with the pinned dataset version before submission. Refresh the focused related-work search before the final manuscript; no exhaustive novelty claim is made.
