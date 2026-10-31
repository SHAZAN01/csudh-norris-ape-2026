"""Frozen Phase 5 statistics (numpy only; validated by tests/phase5/test_stats.py).

Paired unit: FLORES+ sentence ID within one direction. For a comparison, d_i is the
native segment COMET of system A minus system B on the same ID.
  * Point estimate: 100 * mean(d).
  * 95% CI: percentile of 100 * mean(d[idx_b]) over B = 10,000 paired resamples.
  * p-value (two-sided, centered): z = d - mean(d); p = (1 + #{|mean(z[idx_b])| >= |mean(d)|}) / (B + 1).
  * One resample index matrix, generated once from numpy default_rng(42), is shared by
    every comparison, so results are deterministic and resumable.
  * Holm step-down within each declared family at alpha 0.05 (adjusted p reported).
"""
import numpy as np

B = 10_000
SEED = 42
ALPHA = 0.05
PRACTICAL_BAND_POINTS = 0.5   # +/-0.5 reported COMET points (= +/-0.005 native)
_TOL = 1e-12


def resample_index(n, b=B, seed=SEED):
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(b, n), dtype=np.int32)


def _means(values, idx, chunk=1000):
    out = np.empty(idx.shape[0], dtype=np.float64)
    for s in range(0, idx.shape[0], chunk):
        out[s:s + chunk] = values[idx[s:s + chunk]].mean(axis=1)
    return out


def paired_test(a, b, idx):
    """a, b: native segment scores aligned by ID. Returns dict on the x100 scale."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1 or idx.shape[1] != a.shape[0]:
        raise ValueError('Paired arrays and resample index must align.')
    d = a - b
    obs = float(d.mean())
    boot = _means(d, idx)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    null = _means(d - obs, idx)
    extreme = int(np.sum(np.abs(null) >= abs(obs) - _TOL))
    p = (1 + extreme) / (idx.shape[0] + 1)
    lo100, hi100 = float(lo * 100), float(hi * 100)
    return dict(n=int(d.size), delta_points=obs * 100, ci95_points=[lo100, hi100], p_raw=float(p),
                within_practical_band=bool(-PRACTICAL_BAND_POINTS <= lo100 and hi100 <= PRACTICAL_BAND_POINTS),
                resamples=int(idx.shape[0]), seed=SEED)


def holm(pvalues):
    """Holm step-down adjusted p-values (monotone, capped at 1), input order preserved."""
    p = np.asarray(pvalues, dtype=np.float64)
    m = p.size
    order = np.argsort(p, kind='mergesort')
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def marker(p_adj):
    """Significance symbols from Holm-adjusted p: dagger < .05, double dagger < .01."""
    if p_adj < 0.01:
        return r'$^\ddagger$'
    if p_adj < 0.05:
        return r'$^\dagger$'
    return ''
