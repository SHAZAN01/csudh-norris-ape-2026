"""Phase 5 extended analyses (Report 5.1). EXPLORATORY, declared after the confirmatory analysis.

Inputs are committed numeric evidence only, so this runs anywhere without Colab, GPU, benchmark text or generations:
  docs/phase5/evidence/main_results.json        (frozen evaluator output, Phase 5)
  docs/phase4/evidence/gpt4o-mini_run_summary.json  (token usage and list-rate cost estimates, Phase 4)

Nothing here enters or alters the confirmatory families F1/F2 (Holm over 24 each), the thresholds or the frozen code.
Every quantity is either a re-expression of frozen results (multiplicity sensitivity, band sensitivity, exact pool
decomposition) or an interval/summary of committed counts (Wilson, Newcombe). Analyses that use reference-based S0
COMET as a gate are labelled ORACLE: they need the reference and cannot be deployed.

Usage: python src/analysis/phase5_extended.py [--out docs/phase5/evidence/extended] [--figures docs/phase5/figures_extended]
"""
import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn', 'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
DLAB = {'eng_Latn->tgl_Latn': 'En→Tl', 'tgl_Latn->eng_Latn': 'Tl→En', 'eng_Latn->spa_Latn': 'En→Es', 'spa_Latn->eng_Latn': 'Es→En'}
DSHORT = {'eng_Latn->tgl_Latn': 'eng-tag', 'tgl_Latn->eng_Latn': 'tag-eng', 'eng_Latn->spa_Latn': 'eng-spa', 'spa_Latn->eng_Latn': 'spa-eng'}
TL, ES = D[:2], D[2:]
S = ['zero-shot', 'knn-oneshot', 'reason-then-edit']
SLAB = {'zero-shot': 'Zero-shot', 'knn-oneshot': 'One-shot', 'reason-then-edit': 'Reason-then-edit'}
M = ['gpt4o-mini', 'llama3-8b']
MLAB = {'gpt4o-mini': 'GPT-4o Mini', 'llama3-8b': 'Llama 3 8B'}
POOLS = ['improve', 'middle', 'protect']  # weak (<0.80), middle, strong (>=0.90) S0 COMET
ALPHA = 0.05
Z = 1.959963984540054  # standard normal 97.5% quantile


# ---------------------------------------------------------------- statistics (stdlib only; tested against scipy)
def holm(p):
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    adj, run = [0.0] * m, 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * p[i]))
        adj[i] = run
    return adj


def bonferroni(p):
    return [min(1.0, len(p) * x) for x in p]


def benjamini_hochberg(p):
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i], reverse=True)
    adj, run = [0.0] * m, 1.0
    for k, i in enumerate(order):
        rank = m - k
        run = min(run, p[i] * m / rank)
        adj[i] = min(1.0, run)
    return adj


def wilson(x, n, z=Z):
    if n == 0:
        return (float('nan'), float('nan'))
    ph = x / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_diff(x1, n1, x2, n2):
    """Newcombe (1998) method 10 hybrid score interval for p1 - p2, independent samples."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den


def kendall_w(rank_rows):
    """Kendall's coefficient of concordance; rank_rows = one list of ranks per rater (no ties expected)."""
    m, n = len(rank_rows), len(rank_rows[0])
    R = [sum(r[j] for r in rank_rows) for j in range(n)]
    mean = sum(R) / n
    s = sum((x - mean) ** 2 for x in R)
    return 12 * s / (m * m * (n ** 3 - n))


# ---------------------------------------------------------------- analyses
def analyse(res, gpt_summary):
    C = res['conditions']
    cond = lambda m, s, d: C[f'{m}/{d}/{s}']
    f1 = {(r['model'], r['strategy'], r['direction']): r for r in res['F1_primary']}
    f2 = {(r['model'], r['direction'], r['contrast']): r for r in res['F2_strategy']}
    met = {(x['model'], x['strategy'], x['direction']): x for x in res['metrics'] if x['model']}
    base = {x['direction']: x for x in res['metrics'] if x['system'] == 'S0 split NLLB'}
    pools = res['baseline_pools']
    out = {'status': 'phase5_extended_exploratory', 'source_evaluation_sha256': res['evaluation_sha256'],
           'declaration': 'Exploratory; declared after the confirmatory analysis; does not modify F1/F2, thresholds or frozen code.'}
    checks = {}

    # X1 multiplicity sensitivity -----------------------------------------------------------------
    mult = {}
    for fam, rows in [('F1', res['F1_primary']), ('F2', res['F2_strategy'])]:
        p = [r['p_raw'] for r in rows]
        h = holm(p)
        checks[f'{fam}_holm_recomputed_maxdiff'] = max(abs(a - r['p_holm']) for a, r in zip(h, rows))
        dec = {'holm_frozen': [r['significant_holm'] for r in rows],
               'bonferroni': [x < ALPHA for x in bonferroni(p)],
               'bh_fdr': [x < ALPHA for x in benjamini_hochberg(p)]}
        mult[fam] = {k: sum(v) for k, v in dec.items()}
        mult[fam]['changed_vs_holm'] = {k: [i for i, (a, b) in enumerate(zip(v, dec['holm_frozen'])) if a != b]
                                       for k, v in dec.items() if k != 'holm_frozen'}
        mult[fam]['raw_p_below_alpha'] = sum(x < ALPHA for x in p)
        mult[fam]['raw_p_at_floor'] = sum(abs(x - 1 / 10001) < 1e-12 for x in p)
    allrows = res['F1_primary'] + res['F2_strategy']
    h48 = holm([r['p_raw'] for r in allrows])
    mult['pooled48_holm'] = {'F1': sum(x < ALPHA for x in h48[:24]), 'F2': sum(x < ALPHA for x in h48[24:])}
    mult['pooled48_changed'] = [f"{r['family']}:{r['model']}:{r['direction']}:{r.get('contrast')}"
                                for r, x in zip(allrows, h48) if (x < ALPHA) != r['significant_holm']]
    nearest = sorted(((r['p_holm'], r) for r in allrows if not r['significant_holm']), key=lambda t: t[0])[0][1]
    mult['closest_nonsignificant'] = {'family': nearest['family'], 'model': nearest['model'], 'direction': nearest['direction'],
                                      'contrast': nearest['contrast'], 'delta': nearest['delta_points'],
                                      'p_raw': nearest['p_raw'], 'p_holm': nearest['p_holm']}
    mult['p_floor'] = 1 / 10001
    out['X1_multiplicity'] = mult

    # X2 practical-band sensitivity (F1) --------------------------------------------------------------
    band = {}
    for b in [0.25, 0.5, 1.0]:
        for m in M:
            cat = {'beyond': 0, 'within': 0, 'straddles': 0}
            for s in S:
                for d in D:
                    lo, hi = f1[(m, s, d)]['ci95_points']
                    cat['beyond' if (lo > b or hi < -b) else 'within' if (lo >= -b and hi <= b) else 'straddles'] += 1
            band[f'{m}@{b}'] = cat
    checks['band_0.5_matches_frozen_flag'] = all(
        ((-0.5 <= f1[k]['ci95_points'][0]) and (f1[k]['ci95_points'][1] <= 0.5)) == f1[k]['within_practical_band'] for k in f1)
    out['X2_band_sensitivity'] = band

    # X3 exact decomposition of mean delta by baseline-quality pool; ORACLE gates ---------------------
    dec, maxerr = [], 0.0
    for m in M:
        for s in S:
            for d in D:
                c = cond(m, s, d)
                n = c['n']
                ns = {'improve': c['improve_pool_n'], 'middle': c['middle_pool_n'], 'protect': c['protect_n']}
                contrib = {p: ns[p] / n * c['pool_mean_delta_points'][p] for p in POOLS}
                total = sum(contrib.values())
                err = abs(total - f1[(m, s, d)]['delta_points'])
                maxerr = max(maxerr, err)
                dec.append({'model': m, 'strategy': s, 'direction': d, 'n_pool': ns, 'mean_pool': c['pool_mean_delta_points'],
                            'contribution': contrib, 'reconstructed': total, 'F1_delta': f1[(m, s, d)]['delta_points'],
                            'oracle_edit_weak_only': contrib['improve'],
                            'oracle_skip_strong': contrib['improve'] + contrib['middle']})
    checks['decomposition_max_abs_error_points'] = maxerr
    out['X3_pool_decomposition'] = dec
    lw = [r for r in dec if r['model'] == 'llama3-8b']
    out['X3_summary'] = {
        'llama_weak_only_positive': sum(r['oracle_edit_weak_only'] > 0 for r in lw),
        'llama_skip_strong_positive': sum(r['oracle_skip_strong'] > 0 for r in lw),
        'gpt_weak_share_of_gain': {f"{r['strategy']}|{r['direction']}": r['contribution']['improve'] / r['F1_delta']
                                   for r in dec if r['model'] == 'gpt4o-mini'},
    }
    gs = list(out['X3_summary']['gpt_weak_share_of_gain'].values())
    out['X3_summary']['gpt_weak_share_min'], out['X3_summary']['gpt_weak_share_max'] = min(gs), max(gs)
    out['X3_summary']['gpt_strong_contrib_abs_max'] = max(abs(r['contribution']['protect']) for r in dec if r['model'] == 'gpt4o-mini')

    # X4 quality-standardized pair comparison (RQ1, descriptive) --------------------------------------
    tot = {'improve': sum(pools[d]['improve'] for d in D), 'protect': sum(pools[d]['protect'] for d in D)}
    tot['middle'] = sum(pools[d]['n'] for d in D) - tot['improve'] - tot['protect']
    N = sum(tot.values())
    w = {p: tot[p] / N for p in POOLS}
    std = []
    for m in M:
        for s in S:
            row = {'model': m, 'strategy': s}
            for d in D:
                c = cond(m, s, d)
                row[d] = {'raw': f1[(m, s, d)]['delta_points'],
                          'standardized': sum(w[p] * c['pool_mean_delta_points'][p] for p in POOLS)}
            row['std_gap_by_pool'] = {p: w[p] * (sum(cond(m, s, d)['pool_mean_delta_points'][p] for d in TL) / 2
                                                 - sum(cond(m, s, d)['pool_mean_delta_points'][p] for d in ES) / 2) for p in POOLS}
            for kind in ['raw', 'standardized']:
                tl = sum(row[d][kind] for d in TL) / 2
                es = sum(row[d][kind] for d in ES) / 2
                row[f'pair_gap_{kind}'] = tl - es
            std.append(row)
    out['X4_standardization'] = {'weights': w, 'pool_totals': tot, 'rows': std}
    gg = [r for r in std if r['model'] == 'gpt4o-mini']
    out['X4_summary'] = {'gpt_gap_raw': {r['strategy']: r['pair_gap_raw'] for r in gg},
                         'gpt_gap_std': {r['strategy']: r['pair_gap_standardized'] for r in gg},
                         'gpt_gap_reduction_pct': {r['strategy']: 100 * (1 - r['pair_gap_standardized'] / r['pair_gap_raw']) for r in gg},
                         'gpt_std_gap_middle_share': {r['strategy']: r['std_gap_by_pool']['middle'] / r['pair_gap_standardized'] for r in gg}}
    rd = list(out['X4_summary']['gpt_gap_reduction_pct'].values())
    out['X4_summary'].update(gpt_gap_reduction_min=min(rd), gpt_gap_reduction_max=max(rd),
                             gpt_std_gap_middle_share_min=min(out['X4_summary']['gpt_std_gap_middle_share'].values()))

    # X5 over-editing uncertainty -------------------------------------------------------------------------
    oe = {}
    for t in ['0.01', '0.02', '0.05']:
        for m in M:
            for s in S:
                x = sum(cond(m, s, d)['overedit'][t]['numerator'] for d in D)
                n = sum(cond(m, s, d)['overedit'][t]['denominator'] for d in D)
                lo, hi = wilson(x, n)
                per_dir = {d: dict(zip(['x', 'n', 'lo', 'hi'], [cond(m, s, d)['overedit'][t]['numerator'],
                                                               cond(m, s, d)['overedit'][t]['denominator'],
                                                               *wilson(cond(m, s, d)['overedit'][t]['numerator'],
                                                                       cond(m, s, d)['overedit'][t]['denominator'])])) for d in D}
                oe[f'{m}|{s}|{t}'] = {'x': x, 'n': n, 'rate': x / n, 'lo': lo, 'hi': hi, 'per_direction': per_dir}
    gaps = {}
    for t in ['0.01', '0.02', '0.05']:
        for s in S:
            g, l = oe[f'gpt4o-mini|{s}|{t}'], oe[f'llama3-8b|{s}|{t}']
            gaps[f'{s}|{t}'] = {'diff_llama_minus_gpt': l['rate'] - g['rate'], 'ci': newcombe_diff(l['x'], l['n'], g['x'], g['n'])}
    out['X5_overediting'] = {'rates': oe, 'editor_gap_same_strategy': gaps}
    gpt_hi = max(oe[f'gpt4o-mini|{s}|0.02']['hi'] for s in S)
    llama_lo = min(oe[f'llama3-8b|{s}|0.02']['lo'] for s in S)
    out['X5_summary'] = {'gpt_max_upper_0.02': gpt_hi, 'llama_min_lower_0.02': llama_lo, 'intervals_separate_0.02': gpt_hi < llama_lo,
                         'all_gap_ci_exclude_zero': all(v['ci'][0] > 0 for v in gaps.values()),
                         'min_gap_lower_0.02': min(gaps[f'{s}|0.02']['ci'][0] for s in S)}
    # direction-level separation (strict check: every Llama per-direction lower bound above every GPT upper bound)
    sep = {}
    for d in D:
        gh = max(oe[f'gpt4o-mini|{s}|0.02']['per_direction'][d]['hi'] for s in S)
        ll = min(oe[f'llama3-8b|{s}|0.02']['per_direction'][d]['lo'] for s in S)
        sep[d] = {'gpt_max_upper': gh, 'llama_min_lower': ll, 'separate': gh < ll}
    out['X5_direction_separation'] = sep

    # X6 edit outcomes among edited items ------------------------------------------------------------
    eo = []
    for m in M:
        for s in S:
            for d in D:
                c = cond(m, s, d)
                e = c['text_edited']
                # unedited outputs have delta 0 and sit inside the band, so improved/harmed counts are all edited items
                eo.append({'model': m, 'strategy': s, 'direction': d, 'edited': e, 'improved': c['improved'], 'harmed': c['harmed'],
                           'precision': c['improved'] / e, 'precision_ci': wilson(c['improved'], e),
                           'harm_rate': c['harmed'] / e, 'harm_ci': wilson(c['harmed'], e),
                           'benefit_harm_ratio': c['improved'] / c['harmed'] if c['harmed'] else float('inf'),
                           'net_per_1000': 1000 * (c['improved'] - c['harmed']) / c['n']})
    checks['improved_plus_harmed_le_edited'] = all(r['improved'] + r['harmed'] <= r['edited'] for r in eo)
    out['X6_edit_outcomes'] = eo
    ge = [r for r in eo if r['model'] == 'gpt4o-mini']
    le = [r for r in eo if r['model'] == 'llama3-8b']
    out['X6_summary'] = {'gpt_ratio_min': min(r['benefit_harm_ratio'] for r in ge), 'gpt_ratio_max': max(r['benefit_harm_ratio'] for r in ge),
                         'llama_ratio_min': min(r['benefit_harm_ratio'] for r in le), 'llama_ratio_max': max(r['benefit_harm_ratio'] for r in le),
                         'llama_ratio_below_1': sum(r['benefit_harm_ratio'] < 1 for r in le),
                         'gpt_harm_rate_max': max(r['harm_rate'] for r in ge), 'llama_harm_rate_min': min(r['harm_rate'] for r in le)}

    # X7 metric concordance across the 24 conditions -------------------------------------------------
    keys = [(m, s, d) for m in M for s in S for d in D]
    dc = [f1[k]['delta_points'] for k in keys]
    db = [met[k]['BLEU'] - base[k[2]]['BLEU'] for k in keys]
    dh = [met[k]['chrFpp'] - base[k[2]]['chrFpp'] for k in keys]
    sig = lambda v: [(x > 0) - (x < 0) for v_ in [v] for x in v_]
    sign_dc, sign_db, sign_dh = sig(dc), sig(db), sig(dh)
    sigk = [k for k in keys if f1[k]['significant_holm']]
    out['X7_metric_concordance'] = {
        'spearman_comet_bleu': spearman(dc, db), 'spearman_comet_chrf': spearman(dc, dh), 'spearman_bleu_chrf': spearman(db, dh),
        'sign_agree_comet_bleu': sum(a == b for a, b in zip(sign_dc, sign_db)),
        'sign_agree_comet_chrf': sum(a == b for a, b in zip(sign_dc, sign_dh)),
        'sign_agree_all_three': sum(a == b == c for a, b, c in zip(sign_dc, sign_db, sign_dh)),
        'significant_n': len(sigk),
        'significant_sign_agree_all_three': sum((f1[k]['delta_points'] > 0) == (met[k]['BLEU'] > base[k[2]]['BLEU'])
                                                == (met[k]['chrFpp'] > base[k[2]]['chrFpp']) for k in sigk),
        'disagreements': [{'model': k[0], 'strategy': k[1], 'direction': k[2], 'dCOMET': a, 'dBLEU': b, 'dchrF': c}
                          for k, a, b, c in zip(keys, dc, db, dh) if not ((a > 0) == (b > 0) == (c > 0))],
        'per_condition': [{'model': k[0], 'strategy': k[1], 'direction': k[2], 'dCOMET': a, 'dBLEU': b, 'dchrF': c}
                          for k, a, b, c in zip(keys, dc, db, dh)]}

    # X8 strategy-ranking concordance across directions ----------------------------------------------
    rk = {}
    for m in M:
        rows = []
        for d in D:
            v = [f1[(m, s, d)]['delta_points'] for s in S]
            rows.append(_ranks([-x for x in v]))  # rank 1 = best
        rk[m] = {'W': kendall_w(rows), 'ranks_by_direction': {d: dict(zip(S, r)) for d, r in zip(D, rows)},
                 'reason_last_all': all(r[2] == 3 for r in rows)}
    out['X8_strategy_rank_concordance'] = rk

    # X9 cost and token efficiency -------------------------------------------------------------------
    ce = []
    for s in S:
        for d in D:
            g = gpt_summary['conditions'][f'gpt4o-mini_{s}_{DSHORT[d]}']
            cost = g['estimated_cost_usd_uncached']
            ce.append({'strategy': s, 'direction': d, 'cost_usd': cost, 'cost_per_1000_items': 1000 * cost / g['n'],
                       'prompt_tokens': g['prompt_tokens'], 'completion_tokens': g['completion_tokens'],
                       'delta_points': f1[('gpt4o-mini', s, d)]['delta_points'],
                       'points_per_dollar_per_1000': f1[('gpt4o-mini', s, d)]['delta_points'] / (1000 * cost / g['n'])})
            checks.setdefault('gpt_tokens_match_phase5', True)
            c = cond('gpt4o-mini', s, d)
            if c['tokens']['prompt'] != g['prompt_tokens'] or c['tokens']['completion'] != g['completion_tokens']:
                checks['gpt_tokens_match_phase5'] = False
    total_cost = sum(r['cost_usd'] for r in ce)
    by_s = {s: {'cost_usd': sum(r['cost_usd'] for r in ce if r['strategy'] == s),
                'mean_delta': sum(r['delta_points'] for r in ce if r['strategy'] == s) / 4} for s in S}
    tok = {m: {s: {'prompt_per_item': sum(cond(m, s, d)['tokens']['prompt'] for d in D) / 4048,
                   'completion_per_item': sum(cond(m, s, d)['tokens']['completion'] for d in D) / 4048} for s in S} for m in M}
    out['X9_cost'] = {'gpt_total_devtest_usd': total_cost, 'by_strategy': by_s, 'per_condition': ce, 'tokens_per_item': tok,
                      'pricing_basis': 'Phase 4 run summary estimated_cost_usd_uncached (list uncached token rates; not an invoice)'}

    # X10 edit rate versus harm (within editor) -------------------------------------------------------
    er = {}
    for m in M:
        xs = [cond(m, s, d)['text_edited'] / 1012 for s in S for d in D]
        ys = [cond(m, s, d)['overedit']['0.02']['numerator'] / cond(m, s, d)['overedit']['0.02']['denominator'] for s in S for d in D]
        hs = [cond(m, s, d)['harmed'] / 1012 for s in S for d in D]
        er[m] = {'spearman_edit_vs_overedit': spearman(xs, ys), 'spearman_edit_vs_harm': spearman(xs, hs),
                 'edit_rate_range': [min(xs), max(xs)], 'overedit_range': [min(ys), max(ys)]}
    # overlap of edit-rate ranges with disjoint over-edit ranges is the key descriptive fact
    out['X10_edit_rate_vs_harm'] = er
    out['X10_summary'] = {'overedit_ranges_disjoint': er['gpt4o-mini']['overedit_range'][1] < er['llama3-8b']['overedit_range'][0],
                          'edit_ranges_overlap': er['gpt4o-mini']['edit_rate_range'][1] > er['llama3-8b']['edit_rate_range'][0]}
    out['checks'] = checks
    return out


def check(out):
    c = out['checks']
    assert c['F1_holm_recomputed_maxdiff'] < 1e-12 and c['F2_holm_recomputed_maxdiff'] < 1e-12, c
    assert c['band_0.5_matches_frozen_flag'], c
    assert c['decomposition_max_abs_error_points'] < 1e-9, c
    assert c['improved_plus_harmed_le_edited'] and c['gpt_tokens_match_phase5'], c
    return True


# ---------------------------------------------------------------- tables and figures
def write_csvs(out, d):
    d.mkdir(parents=True, exist_ok=True)
    with (d / 'X3_pool_decomposition.csv').open('w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['model', 'strategy', 'direction', 'n_weak', 'n_middle', 'n_strong', 'mean_weak', 'mean_middle', 'mean_strong',
                    'contrib_weak', 'contrib_middle', 'contrib_strong', 'F1_delta', 'oracle_weak_only', 'oracle_skip_strong'])
        for r in out['X3_pool_decomposition']:
            w.writerow([r['model'], r['strategy'], r['direction'], *[r['n_pool'][p] for p in POOLS], *[f"{r['mean_pool'][p]:.6f}" for p in POOLS],
                        *[f"{r['contribution'][p]:.6f}" for p in POOLS], f"{r['F1_delta']:.6f}", f"{r['oracle_edit_weak_only']:.6f}",
                        f"{r['oracle_skip_strong']:.6f}"])
    with (d / 'X5_overediting_wilson.csv').open('w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['model', 'strategy', 'threshold', 'scope', 'x', 'n', 'rate', 'wilson_lo', 'wilson_hi'])
        for k, v in out['X5_overediting']['rates'].items():
            m, s, t = k.split('|')
            w.writerow([m, s, t, 'pooled', v['x'], v['n'], f"{v['rate']:.6f}", f"{v['lo']:.6f}", f"{v['hi']:.6f}"])
            for dd, pv in v['per_direction'].items():
                w.writerow([m, s, t, dd, pv['x'], pv['n'], f"{pv['x'] / pv['n']:.6f}", f"{pv['lo']:.6f}", f"{pv['hi']:.6f}"])
    with (d / 'X6_edit_outcomes.csv').open('w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['model', 'strategy', 'direction', 'edited', 'improved', 'harmed', 'precision', 'harm_rate', 'benefit_harm_ratio', 'net_per_1000'])
        for r in out['X6_edit_outcomes']:
            w.writerow([r['model'], r['strategy'], r['direction'], r['edited'], r['improved'], r['harmed'], f"{r['precision']:.6f}",
                        f"{r['harm_rate']:.6f}", f"{r['benefit_harm_ratio']:.6f}", f"{r['net_per_1000']:.3f}"])


def figures(out, res, fdir):
    import os
    os.environ['MPLBACKEND'] = 'Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fdir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 7.5, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'font.family': 'DejaVu Sans'})
    col = {'gpt4o-mini': '#1f5f99', 'llama3-8b': '#c0392b'}
    mk = {'zero-shot': 'o', 'knn-oneshot': 's', 'reason-then-edit': '^'}
    f1 = {(r['model'], r['strategy'], r['direction']): r for r in res['F1_primary']}

    # F-A forest plot of F1 with practical band
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    y, labels = 0, []
    for d in D:
        for m in M:
            for s in S:
                r = f1[(m, s, d)]
                lo, hi = r['ci95_points']
                ax.plot([lo, hi], [y, y], color=col[m], lw=1.4)
                ax.plot(r['delta_points'], y, mk[s], color=col[m], ms=4.2,
                        mfc=col[m] if r['significant_holm'] else 'white', mew=1.0)
                labels.append(f"{DLAB[d]}  {MLAB[m]} {SLAB[s]}")
                y += 1
        y += 0.8
    ax.axvspan(-0.5, 0.5, color='0.88', zorder=0)
    ax.axvline(0, color='0.35', lw=.7)
    ticks = []
    y = 0
    for d in D:
        for _ in range(6):
            ticks.append(y)
            y += 1
        y += .8
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=5.6)
    ax.invert_yaxis()
    ax.set_xlabel('ΔCOMET vs S0 (points, 95% paired bootstrap CI)')
    ax.grid(axis='x', alpha=.3, lw=.4)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=col[m], lw=1.4, label=MLAB[m]) for m in M] + \
        [Line2D([], [], marker=mk[s], ls='', color='0.3', label=SLAB[s]) for s in S] + \
        [Line2D([], [], marker='o', ls='', mfc='white', color='0.3', label='not Holm-significant')]
    ax.legend(handles=h, fontsize=6, frameon=False, loc='lower right')
    ax.set_title('F1: every condition minus S0 (grey: ±0.5-point practical band)', fontsize=8)
    fig.tight_layout()
    fig.savefig(fdir / 'figX1_forest_F1.pdf')
    fig.savefig(fdir / 'figX1_forest_F1.png', dpi=220)
    plt.close(fig)

    # F-B pool decomposition
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
    pc = {'improve': '#2e8b57', 'middle': '#b0b0b0', 'protect': '#8e44ad'}
    pl = {'improve': 'weak S0 (<0.80)', 'middle': 'middle', 'protect': 'strong S0 (≥0.90)'}
    for ax, m in zip(axes, M):
        rows = [r for r in out['X3_pool_decomposition'] if r['model'] == m]
        xs = list(range(len(rows)))
        pos = [0.0] * len(rows)
        neg = [0.0] * len(rows)
        for p in POOLS:
            v = [r['contribution'][p] for r in rows]
            bottom = [pos[i] if v[i] >= 0 else neg[i] for i in xs]
            ax.bar(xs, v, bottom=bottom, color=pc[p], width=.75, label=pl[p])
            for i in xs:
                if v[i] >= 0:
                    pos[i] += v[i]
                else:
                    neg[i] += v[i]
        ax.plot(xs, [r['F1_delta'] for r in rows], 'k_', ms=9, mew=1.6, label='total Δ (F1)')
        ax.axhline(0, color='0.3', lw=.6)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{SLAB[r['strategy']][0]}-{DLAB[r['direction']]}" for r in rows], rotation=90, fontsize=5.6)
        ax.set_title(MLAB[m], fontsize=8)
        ax.grid(axis='y', alpha=.3, lw=.4)
    axes[0].set_ylabel('contribution to mean ΔCOMET (points)')
    axes[1].legend(fontsize=6, frameon=False, loc='lower left')
    fig.tight_layout()
    fig.savefig(fdir / 'figX2_pool_decomposition.pdf')
    fig.savefig(fdir / 'figX2_pool_decomposition.png', dpi=220)
    plt.close(fig)

    # F-C edit rate vs protect over-edit rate (Wilson intervals)
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    C = res['conditions']
    for m in M:
        for s in S:
            for dd in D:
                c = C[f'{m}/{dd}/{s}']
                x = 100 * c['text_edited'] / c['n']
                o = c['overedit']['0.02']
                lo, hi = wilson(o['numerator'], o['denominator'])
                yv = 100 * o['numerator'] / o['denominator']
                ax.errorbar(x, yv, yerr=[[yv - 100 * lo], [100 * hi - yv]], fmt=mk[s], color=col[m], ms=4, lw=.7, capsize=1.5,
                            mfc=col[m] if dd in TL else 'white')
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=col[m], lw=2, label=MLAB[m]) for m in M] + \
        [Line2D([], [], marker=mk[s], ls='', color='0.3', label=SLAB[s]) for s in S] + \
        [Line2D([], [], marker='o', ls='', color='0.3', label='Tagalog pair (filled)'),
         Line2D([], [], marker='o', ls='', mfc='white', color='0.3', label='Spanish pair (open)')]
    ax.legend(handles=h, fontsize=5.8, frameon=False, loc='upper left')
    ax.set_xlabel('drafts edited (%)')
    ax.set_ylabel('strong drafts over-edited (%, Wilson 95% CI)')
    ax.grid(alpha=.3, lw=.4)
    fig.tight_layout()
    fig.savefig(fdir / 'figX3_edit_vs_overedit.pdf')
    fig.savefig(fdir / 'figX3_edit_vs_overedit.png', dpi=220)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=str(ROOT / 'docs/phase5/evidence/main_results.json'))
    ap.add_argument('--gpt-summary', default=str(ROOT / 'docs/phase4/evidence/gpt4o-mini_run_summary.json'))
    ap.add_argument('--out', default=str(ROOT / 'docs/phase5/evidence/extended'))
    ap.add_argument('--figures', default=str(ROOT / 'docs/phase5/figures_extended'))
    ap.add_argument('--no-figures', action='store_true')
    a = ap.parse_args()
    res = json.loads(Path(a.results).read_text())
    out = analyse(res, json.loads(Path(a.gpt_summary).read_text()))
    check(out)
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    (od / 'extended_analyses.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    write_csvs(out, od)
    if not a.no_figures:
        figures(out, res, Path(a.figures))
    print('PASS: extended analyses written; consistency checks:', json.dumps(out['checks']))


if __name__ == '__main__':
    main()
