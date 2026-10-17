# Numerical interpretation

The authoritative full precision values are in
`evidence/evaluation/dev_baseline_metrics.json`.
COMET tables show native scores × 100. Deltas are split minus unsplit.
Bootstrap intervals: paired percentile, 10,000 resamples, seed 42; dev diagnostics.
The Tagalog to English whole-dev interval includes zero. Do not call that effect
confirmed, absent or equivalent on the basis of this interval.

The per item ±0.02 threshold is on the native scale: ±2 reported COMET points.
120 increases + 3,833 within band + 35 decreases = 3,988.
377 changed hypotheses + 3,611 identical hypotheses = 3,988.
222 changed hypotheses fall within the band. Neutral scores and identical text
are different concepts. The 7,976 final records are not independent inference
sequences: single fragment sources reuse their control outputs.

No devtest or post editor results have been supplied. Runtime dependency
resolution and synthetic tests are preparation, not a successful model pilot.
The observed generation wall time excludes the earlier model download/load.
