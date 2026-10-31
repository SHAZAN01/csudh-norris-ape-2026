"""Tests for src/analysis/phase5_extended.py. Stdlib only.
Reference values: scipy 1.17 (Wilson, Spearman, BH) and Newcombe (1998), Stat Med 17:873, Table II example (56/70 vs 48/80)."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'analysis'))
import phase5_extended as X  # noqa: E402


def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def test_wilson():
    assert close(X.wilson(10, 1179), (0.004613586758477718, 0.015542503174711064))
    assert close(X.wilson(247, 1179), (0.18723241265690976, 0.23365362841663156))
    assert all(math.isnan(v) for v in X.wilson(0, 0))


def test_newcombe_published_example():
    lo, hi = X.newcombe_diff(56, 70, 48, 80)
    assert abs(lo - 0.0524) < 1e-4 and abs(hi - 0.3339) < 1e-4


def test_multiplicity():
    p = [0.01, 0.04, 0.03, 0.005, 0.2]
    assert close(X.holm(p), [0.04, 0.09, 0.09, 0.025, 0.2])
    assert close(X.benjamini_hochberg(p), [0.025, 0.05, 0.05, 0.025, 0.2])
    assert close(X.bonferroni(p), [0.05, 0.2, 0.15, 0.025, 1.0])


def test_rank_statistics():
    assert abs(X.spearman([1, 2, 3, 4, 5, 6.5, 2.2], [2, 1, 4, 3, 7, 5, 5]) - 0.7207499701564473) < 1e-12
    assert X.kendall_w([[1, 2, 3], [1, 2, 3]]) == 1.0 and X.kendall_w([[1, 2, 3], [3, 2, 1]]) == 0.0


def test_on_committed_evidence():
    res = json.loads((ROOT / 'docs/phase5/evidence/main_results.json').read_text())
    gs = json.loads((ROOT / 'docs/phase4/evidence/gpt4o-mini_run_summary.json').read_text())
    out = X.analyse(res, gs)
    assert X.check(out)
    # exact pool decomposition reproduces every frozen F1 delta
    assert out['checks']['decomposition_max_abs_error_points'] < 1e-9
    # Holm recomputation equals the frozen evaluator's adjusted p-values
    assert out['checks']['F1_holm_recomputed_maxdiff'] == 0 and out['checks']['F2_holm_recomputed_maxdiff'] == 0
    # committed file equals a fresh computation
    saved = json.loads((ROOT / 'docs/phase5/evidence/extended/extended_analyses.json').read_text())
    assert json.dumps(saved, sort_keys=True) == json.dumps(json.loads(json.dumps(out, ensure_ascii=False)), sort_keys=True)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
