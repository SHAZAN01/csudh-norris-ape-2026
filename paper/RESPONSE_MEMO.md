# Anticipated reviewer objections and responses (held-out evidence)

Internal preparation memo (7.txt), updated 30 October 2026 from the frozen Phase 5 results
(`docs/phase5/evidence/main_results.json`) and the exploratory robustness analyses of Report 5.1
(`docs/phase5/evidence/extended/extended_analyses.json`). It anticipates objections; it is not a response to an
actual review. Every number below is in the audited manuscript or in Report 5.

## 1. "Why GPT-4o Mini and an 8B Llama rather than stronger models? Is the Llama result just a weak model?"

**Response.** The matrix was fixed before the test set was opened: one dated commercial snapshot
(`gpt-4o-mini-2024-07-18`) and one pinned open-weight checkpoint (Llama 3 8B Instruct), chosen for
cost and reproducibility, not as frontier representatives. The paper therefore makes no claim about
model scale or families. The comparison is informative because both editors received identical
prompts, inputs, contracts and decoding settings:

* both edit most drafts under one-shot prompting (GPT-4o Mini 80% of 4,048), yet
* GPT-4o Mini over-edits 0.8–4.3% of 1,179 strong drafts, Llama 11.2–20.9%;
* GPT-4o Mini improves all 12 conditions (+0.26 to +1.00, Holm-significant); Llama improves none.

The difference lies in *whether edits to already-correct drafts preserve meaning*, not in
willingness to edit, which is practically relevant for anyone deploying a small open model as a
post-editor. **Manuscript:** Limitations states the two-model scope; Discussion frames the result
as editor-specific.

## 2. "Does FLORES+ reflect real translation noise, and do COMET gains mean real improvement?"

**Response.** FLORES+ is clean, mostly English-original benchmark text with independent reference
translations, not human post-edits; the paper claims neither reduced editing effort nor robustness
to real-world noise, and makes no claims about community or heritage Spanish. To avoid over-reading
one metric we report: (a) BLEU and chrF++ with signatures, which lie above S0 for all twelve
GPT-4o Mini conditions and below it for all twelve Llama conditions, including Llama conditions
whose COMET change is not significant; (b) paired intervals with Holm correction, flagging five GPT-4o Mini gains as within
±0.5 points; (c) gains by baseline quality, showing improvements come from weak drafts (positive in
23 of 24 conditions) while strong drafts are at best preserved; (d) model-independent error screens; (e) exploratory robustness (Report 5.1): no F1 decision changes under
Bonferroni, Benjamini–Hochberg or a joint Holm family of 48; all 18 significant F1 effects have the same sign in
COMET, BLEU and chrF++ (rank correlation of condition deltas: chrF++ 0.97, BLEU 0.94); the only metric
disagreements are three non-significant Llama conditions where COMET is flat and lexical metrics fall.
No human evaluation was run (PI decisions of 24 September and 31 October 2026); the 96-case review is a
source- and reference-based qualitative inspection, and the absence of human evaluation is a stated limitation.

## 3. "Does reason-then-edit (CoT) introduce hallucinated diagnoses, and was the condition handicapped?"

**Response.** The condition is single-call structured reason-then-edit, not free chain-of-thought,
and its diagnoses are treated as model outputs, never as verified explanations. On development data
the first strict contract made 227/400 Llama outputs fall back to the baseline; per the PI, the
contract was simplified to `diagnosis` then `edited_translation`, documented before the rerun, and
accepted through a predeclared operational gate (0/400 fallbacks for both editors). On held-out
data all 24,288 outputs were valid, so the condition was not handicapped by format. Even so,
reason-then-edit was never significantly better than zero-shot or one-shot (all 16 point estimates
lower), and for Llama it was the most harmful strategy in every direction (−0.51 to −1.44 vs. S0;
247 of 1,179 strong drafts over-edited). The rule-based source review confirms that confident
diagnoses accompany unsupported edits: Llama reason-then-edit rendered a plane's *secuestro* as
"kidnapping" with a diagnosis asserting that this was more accurate, called a correct Tagalog
word a non-word, and returned the untranslated source while claiming a one-word fix (language ID
places 20 of its 4,048 outputs in the source language). All 12 of Llama's largest strong-draft
over-edits were genuine errors, against 2 of 12 for GPT-4o Mini, whose others were acceptable or
source-supported changes that COMET penalized.

## Further likely questions

* **New method, or the ICAI system on new languages?** Anchoring and semantic exemplar retrieval are
  cited as established; contributions are the empirical setting, four directions, stronger split
  baseline, two-editor comparison, failure accounting and over-editing analysis (PI-approved boundary).
* **Resource level?** Two pairs cannot isolate it. The Tagalog pair has more weak drafts (183 and 82 vs.
  104 and 60 items below 0.80), but reweighting to a common quality mix narrows GPT-4o Mini's pair gap by
  only 16–23%; at least 73% of the remainder arises in mid-quality drafts (Report 5.1 §5). We therefore say
  baseline quality explains part of the difference and make no causal resource claim.
* **Is the over-editing gap just noise?** Wilson 95% intervals separate the pooled rates (GPT-4o Mini ≤ 5.6%,
  Llama ≥ 9.5%); among edited drafts every GPT-4o Mini harm rate (≤ 8.9%) is below every Llama rate (≥ 9.9%).
  Per direction, intervals overlap into English, which the paper does not claim otherwise.
* **Would gating fix Llama?** An oracle that skipped strong drafts (reference-based, not deployable) would still
  leave Llama below S0 in 6 of 12 conditions, because it also degrades mid-quality drafts.
* **Baseline reproduction?** Segmentation reproduced 2,991/2,991 dev items; regenerated unsplit drafts
  matched 3,988/3,988 (dev) and 4,048/4,048 (devtest); fragment translations matched 412/421 dev items
  (disclosed). All editors edit the same frozen S0 drafts.
