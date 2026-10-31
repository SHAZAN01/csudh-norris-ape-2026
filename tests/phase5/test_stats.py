"""Synthetic fixtures for the frozen Phase 5 bootstrap procedure (run before any devtest scoring)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'evaluation'))
import norris_stats as S

N = 1012
IDX = S.resample_index(N)


def test_index_deterministic():
    assert np.array_equal(IDX, S.resample_index(N))
    assert IDX.shape == (S.B, N) and IDX.min() >= 0 and IDX.max() < N


def test_identical_systems():
    a = np.random.default_rng(1).uniform(.6, .95, N)
    r = S.paired_test(a, a.copy(), IDX)
    assert r['delta_points'] == 0 and r['p_raw'] == 1.0 and r['ci95_points'] == [0.0, 0.0]
    assert r['within_practical_band']


def test_constant_effect_is_minimum_p():
    a = np.random.default_rng(2).uniform(.6, .95, N)
    r = S.paired_test(a + .01, a, IDX)
    assert abs(r['delta_points'] - 1.0) < 1e-9
    assert r['p_raw'] == 1 / (S.B + 1)
    assert abs(r['ci95_points'][0] - 1.0) < 1e-9 and abs(r['ci95_points'][1] - 1.0) < 1e-9


def test_sign_symmetry():
    rng = np.random.default_rng(3)
    a, b = rng.uniform(.6, .95, N), rng.uniform(.6, .95, N)
    r1, r2 = S.paired_test(a, b, IDX), S.paired_test(b, a, IDX)
    assert abs(r1['delta_points'] + r2['delta_points']) < 1e-12
    assert r1['p_raw'] == r2['p_raw']
    assert abs(r1['ci95_points'][0] + r2['ci95_points'][1]) < 1e-9


def test_null_calibration_roughly_uniform():
    rng = np.random.default_rng(4)
    idx = S.resample_index(200, b=999, seed=7)
    ps = []
    for _ in range(200):
        a = rng.normal(0, .05, 200)
        ps.append(S.paired_test(a, np.zeros(200), idx)['p_raw'])
    rate = np.mean(np.asarray(ps) < .05)
    assert 0.01 <= rate <= 0.11, rate


def test_detects_real_shift():
    rng = np.random.default_rng(5)
    b = rng.uniform(.6, .95, N)
    a = b + rng.normal(.01, .03, N)
    assert S.paired_test(a, b, IDX)['p_raw'] < .001


def test_holm():
    adj = S.holm([0.01, 0.04, 0.03, 0.5])
    assert np.allclose(adj, [0.04, 0.09, 0.09, 0.5])
    assert S.holm([0.9, 0.9]) == [1.0, 1.0]


def test_markers():
    assert S.marker(0.005) == r'$^\ddagger$' and S.marker(0.02) == r'$^\dagger$' and S.marker(0.2) == ''


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
