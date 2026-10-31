# Reason-then-edit contract revision (rte_v3) — change record

**Status:** predeclared before any rerun output exists. Dev only. Devtest unopened.
**Authority:** PI instruction, 22 October 2026: *simplify the diagnostic contract to the minimum structure necessary for the reason-then-edit strategy, document the change, and rerun the affected dev reason-then-edit conditions for both models. Do not change the underlying task or use devtest.*
**Record date:** 23 October 2026. Protocol fingerprint: `7547a429e81ae64bd8a5834903eb3492bfcb901f64c47e1ed9c1559f4375185d`.

## 1. Why

Measured candidate v2 (Report 3.1): Llama 3 8B Instruct reason-then-edit was usable on 173/400 dev items (227 baseline fallbacks); GPT-4o Mini on 392/400 (8). 399/400 Llama responses parsed as JSON. The failures came from the *diagnostic semantics* validators, not from JSON structure (screens overlap; do not add): repeated category 184 (GPT 8), empty or >25-word note 45, NONE combined with another category 23, category count outside 1–6 = 3, unparseable 1, non-stop finish 1. A 56.75% fallback rate means the measured condition mostly evaluates the baseline, so it cannot serve as a clean strategy comparison.

## 2. What is the minimum structure the strategy needs

Reason-then-edit requires exactly two things: (a) a diagnostic step generated **before** the edit, and (b) the final translation **isolated** from that diagnostic text so it can be scored. Everything else in v2 (a six-label taxonomy, label uniqueness, NONE exclusivity, 1–6 items, a 25-word per-note cap) was additional structure.

## 3. The change (only this)

| Element | v2 (measured) | v3 (frozen) |
|---|---|---|
| Schema | `diagnostics: [{error_type ∈ 6 labels, note}]`, `edited_translation` | `diagnosis: string`, `edited_translation: string` |
| Order | diagnostics first | diagnosis first (schema order + validator) |
| Validators | JSON, no duplicate keys, strict schema, 1–6 unique labels, NONE alone, notes 1–25 words, non-empty translation, key order, finish=stop | JSON, no duplicate keys, strict schema, non-empty diagnosis, non-empty translation, key order, finish=stop |
| Suffix | v2 text (taxonomy rules) | v3 text below |

v3 suffix (exact bytes):

```
Return diagnosis first and edited_translation second.
In diagnosis, briefly state the source-supported errors you find in the draft, or state that no correction is needed. Keep it to one or two short sentences.
Describe only defects actually visible when comparing this source and draft. Never invent an error or change a correct name or number to justify editing.
If no correction is needed, return the draft unchanged as edited_translation.
Put only the complete final target-language translation in edited_translation. Keep the diagnosis outside that field.
```

v3 schema:

```json
{
 "additionalProperties": false,
 "properties": {
  "diagnosis": {
   "title": "Diagnosis",
   "type": "string"
  },
  "edited_translation": {
   "title": "Edited Translation",
   "type": "string"
  }
 },
 "required": [
  "diagnosis",
  "edited_translation"
 ],
 "title": "ReasonEditV3",
 "type": "object"
}
```

## 4. Unchanged (verified mechanically before the rerun)

Task, dev partition, the same seed-42 sample of 100 aligned IDs, queries and split-NLLB drafts, the shared system instruction bytes, the user payload bytes, model snapshots/revisions (Llama `8afb486c1db2`, `gpt-4o-mini-2024-07-18`), decoding and engine settings, structured decoding (vLLM 0.11.2 `StructuredOutputsParams`; OpenAI strict `json_schema`), fallback policy (raw output kept; unchanged baseline; no repair; no selective regeneration). Zero-shot and retrieved one-shot are **not rerun**: their bytes are unchanged.

`prepare_rte_v3_dev.py` refuses to proceed unless the frozen builder reproduces all 1,200 measured v2 job prompts byte-for-byte. `analyze_rte_v3_dev.py` refuses unless the frozen output contract reproduces all 1,600 stored v2 zero-shot/one-shot outcomes exactly, and unless the 400 pilot baselines rescore within 1e-5 native COMET.

## 5. Predeclared reliability gate

For **each** model: fallbacks ≤ 20/400 (5.0%) overall **and** ≤ 10/100 in every direction. The gate is operational only; COMET or edit rates are never used to accept or reject v3. One revision only: no further prompt iteration after the full rerun is observed. If either model fails, the evidence goes to the PI, who decides whether to retain reason-then-edit as an explicit failure condition or remove it from the final matrix.

## 6. What changes in interpretation

* v3 diagnoses are free text. They are stored as observable outputs, not as verified error annotations, and are not analysed as an error taxonomy. The roadmap's six-category self-diagnosis (3.txt) is therefore a documented deviation. Error analysis in Phase 5 uses the programmatic, model-independent screens (5.txt): digits/names, length ratio, language ID, sentence counts.
* v2 results remain reported as development evidence (the measured history), and the v2→v3 comparison is reported for both models.
* Zero-shot/one-shot dev rows in the revised development table are the measured v2 rows; reason-then-edit rows are v3.

## 7. Files

`src/common/norris_protocol.py` (frozen prompts/schemas/contract), `src/phase3/post_editing/prepare_rte_v3_dev.py`, `src/post_editing/run_main_experiments.py` (same engine as Phase 4, validated here on dev), `src/phase3/post_editing/analyze_rte_v3_dev.py`, `tests/frozen/test_protocol.py`, `notebooks/phase3/03_rte_v3_revalidation_and_freeze.ipynb`.
