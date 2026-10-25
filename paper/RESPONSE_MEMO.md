# Anticipated reviewer objections and responses (held-out evidence)

Internal preparation memo (7.txt), updated 25 October 2026 from the frozen Phase 5 results
(`docs/phase5/evidence/main_results.json`). It anticipates objections; it is not a response to an
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
23 of 24 conditions) while strong drafts are at best preserved; (d) model-independent error screens.
No bilingual human evaluation was run (PI decision, 24 September 2026); this is a stated limitation.

## 3. "Does reason-then-edit (CoT) introduce hallucinated diagnoses, and was the condition handicapped?"

**Response.** The condition is single-call structured reason-then-edit, not free chain-of-thought,
and its diagnoses are treated as model outputs, never as verified explanations. On development data
the first strict contract made 227/400 Llama outputs fall back to the baseline; per the PI, the
contract was simplified to `diagnosis` then `edited_translation`, documented before the rerun, and
accepted through a predeclared operational gate (0/400 fallbacks for both editors). On held-out
data all 24,288 outputs were valid, so the condition was not handicapped by format. Even so,
reason-then-edit was never significantly better than zero-shot or one-shot (all 16 point estimates
lower), and for Llama it was the most harmful strategy in every direction (−0.51 to −1.44 vs. S0;
247 of 1,179 strong drafts over-edited). The rule-based source review (pending) will show whether
confident diagnoses accompany unsupported edits.

## Further likely questions

* **New method, or the ICAI system on new languages?** Anchoring and semantic exemplar retrieval are
  cited as established; contributions are the empirical setting, four directions, stronger split
  baseline, two-editor comparison, failure accounting and over-editing analysis (PI-approved boundary).
* **Resource level?** Two pairs cannot isolate it; the Tagalog pair's larger GPT-4o Mini gains track
  its larger share of weak drafts (183 and 82 vs. 104 and 60 items below 0.80).
* **Baseline reproduction?** Segmentation reproduced 2,991/2,991 dev items; regenerated unsplit drafts
  matched 3,988/3,988 (dev) and 4,048/4,048 (devtest); fragment translations matched 412/421 dev items
  (disclosed). All editors edit the same frozen S0 drafts.
