"""Recompute numeric evidence; does not claim lexical rescoring or GPU execution."""
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/phase3/evaluation'))
from evaluate_dev_baselines import digest,paired_mean_ci
E=ROOT/'docs/phase3/evidence'
spec=json.loads((E/'evaluation/evaluation_spec.json').read_text())
report=json.loads((E/'evaluation/dev_baseline_metrics.json').read_text())
assert digest(spec)==report['evaluation_sha256']
generation=json.loads((E/'generation/run_spec.json').read_text())
assert digest(generation)==spec['generation_run_sha256']
assert hashlib.sha256((E/'code/generating_evaluator_source.py').read_bytes()).hexdigest()==spec['evaluator_script_sha256']
freeze=(E/'evaluation/requirements_resolved.txt').read_text().splitlines()
assert digest(freeze)==spec['resolved_packages_sha256']
changed=0;bands=np.zeros(3,dtype=int)
for key,r in report['results'].items():
 src,tgt=key.split('->')
 c=json.loads((E/f'evaluation/scores_{src}_{tgt}_dev.json').read_text())
 sha=c.pop('content_sha256');assert digest(c)==sha
 assert c['evaluation_sha256']==report['evaluation_sha256']
 assert len(c['sentence_ids'])==len(set(c['sentence_ids']))==997
 u=np.array(c['unsplit_scores_native'],dtype=np.float64)
 s=np.array(c['split_scores_native'],dtype=np.float64)
 assert u.shape==s.shape==(997,) and np.isfinite(u).all() and np.isfinite(s).all()
 assert abs(u.mean()*100-r['current_unsplit']['COMET_points'])<1e-8
 assert abs(s.mean()*100-r['sentence_split']['COMET_points'])<1e-8
 actual=paired_mean_ci(s-u)
 assert np.allclose(actual['ci95_points'],r['paired_delta_all_items']['ci95_points'],rtol=0,atol=1e-8)
 assert abs(actual['mean_difference_points']-r['paired_delta_all_items']['mean_difference_points'])<1e-8
 b=r['metric_change_bins_native_threshold_002']
 counts=np.array([(s-u>0.02).sum(),(abs(s-u)<=0.02).sum(),(s-u< -0.02).sum()])
 assert counts.tolist()==[b['increased_gt_0.02'],b['within_inclusive_plus_minus_0.02'],b['decreased_gt_0.02']]
 bands+=counts;changed+=r['text_outputs_changed']
 print('PASS',key,'mean, paired interval, cache hash and change bands')
assert changed==377 and bands.tolist()==[120,3833,35]
print('PASS: generation and evaluation signatures, scorer source hash and package hash')
print('No lexical rescoring, model inference or devtest access performed.')
