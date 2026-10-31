"""Named held-out facts derived from Phase 5 results (and committed cost evidence) for the manuscript audit.
Every number written in the manuscript prose is registered in paper/claims_manifest.json against one fact."""
import json
from pathlib import Path

D = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn', 'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
TL, ES = D[:2], D[2:]
S = ['zero-shot', 'knn-oneshot', 'reason-then-edit']
WORDS = {5: 'five', 6: 'six', 12: 'twelve'}


def facts(res, repo):
    C = res['conditions']
    f1 = {(r['model'], r['strategy'], r['direction']): r for r in res['F1_primary']}
    f2 = {(r['model'], r['direction'], r['contrast']): r for r in res['F2_strategy']}
    dg = {r['direction']: r for r in res['diagnostic_segmentation']}
    met = {(m['model'], m['strategy'], m['direction']): m for m in res['metrics'] if m['model']}
    base = {m['direction']: m for m in res['metrics'] if m['system'] == 'S0 split NLLB'}
    g = lambda m: [f1[(m, s, d)] for s in S for d in D]
    cond = lambda m, s, d: C[f'{m}/{d}/{s}']
    pooled = lambda m, s, key: sum(cond(m, s, d)[key] for d in D)
    oe = lambda m, s, t='0.02': sum(cond(m, s, d)['overedit'][t]['numerator'] for d in D)
    prot = sum(res['baseline_pools'][d]['protect'] for d in D)
    F = {}
    F['outputs_total'] = sum(v['n'] for v in res['coverage'].values())
    F['gpt_f1_min'] = min(r['delta_points'] for r in g('gpt4o-mini'))
    F['gpt_f1_max'] = max(r['delta_points'] for r in g('gpt4o-mini'))
    F['gpt_f1_all_sig_positive'] = WORDS[sum(r['significant_holm'] and r['delta_points'] > 0 for r in g('gpt4o-mini'))]
    F['gpt_f1_in_band'] = WORDS[sum(r['within_practical_band'] for r in g('gpt4o-mini'))]
    F['gpt_band_all_spanish'] = all(r['direction'] in ES for r in g('gpt4o-mini') if r['within_practical_band'])
    F['llama_sig_negative'] = WORDS[sum(r['significant_holm'] and r['delta_points'] < 0 for r in g('llama3-8b'))]
    F['llama_sig_positive'] = sum(r['significant_holm'] and r['delta_points'] > 0 for r in g('llama3-8b'))
    F['llama_nonsig_in_band'] = all(r['within_practical_band'] for r in g('llama3-8b') if not r['significant_holm'])
    for d, k in zip(['eng_Latn->tgl_Latn', 'eng_Latn->spa_Latn', 'tgl_Latn->eng_Latn'], ['EnTl', 'EnEs', 'TlEn']):
        F['segdiag_' + k] = dg[d]['delta_points']
    F['segdiag_EsEn_inconclusive'] = dg['spa_Latn->eng_Latn']['ci95_points'][0] <= 0 <= dg['spa_Latn->eng_Latn']['ci95_points'][1]
    F['gpt_bleu_above'] = WORDS[sum(met[k]['BLEU'] > base[k[2]]['BLEU'] and met[k]['chrFpp'] > base[k[2]]['chrFpp'] for k in met if k[0] == 'gpt4o-mini')]
    F['llama_bleu_below'] = WORDS[sum(met[k]['BLEU'] < base[k[2]]['BLEU'] and met[k]['chrFpp'] < base[k[2]]['chrFpp'] for k in met if k[0] == 'llama3-8b')]
    tg = [f1[('gpt4o-mini', s, d)]['delta_points'] for s in S for d in TL]
    eg = [f1[('gpt4o-mini', s, d)]['delta_points'] for s in S for d in ES]
    F.update(gpt_tl_min=min(tg), gpt_tl_max=max(tg), gpt_es_min=min(eg), gpt_es_max=max(eg))
    for d, k in zip(D, ['EnTl', 'TlEn', 'EnEs', 'EsEn']):
        F['improve_pool_' + k] = res['baseline_pools'][d]['improve']
    imp = [cond('gpt4o-mini', 'knn-oneshot', d)['pool_mean_delta_points']['improve'] for d in D]
    F.update(gpt_one_improve_min=min(imp), gpt_one_improve_max=max(imp))
    pg = [cond('gpt4o-mini', s, d)['pool_mean_delta_points']['protect'] for s in S for d in D]
    F.update(gpt_protect_min=min(pg), gpt_protect_max=max(pg))
    pl = [cond('llama3-8b', s, d)['pool_mean_delta_points']['protect'] for s in S for d in D]
    F.update(llama_protect_max=max(pl), llama_protect_min=min(pl))
    F['llama_improve_positive'] = sum(cond('llama3-8b', s, d)['pool_mean_delta_points']['improve'] > 0 for s in S for d in D)
    F['improve_positive_all'] = sum(c['pool_mean_delta_points']['improve'] > 0 for c in C.values())
    sig = lambda m, c: [d for d in D if f2[(m, d, c)]['significant_holm']]
    one_zero = [f2[('gpt4o-mini', d, 'knn-oneshot - zero-shot')]['delta_points'] for d in sig('gpt4o-mini', 'knn-oneshot - zero-shot')]
    r_one = [f2[('gpt4o-mini', d, 'reason-then-edit - knn-oneshot')]['delta_points'] for d in sig('gpt4o-mini', 'reason-then-edit - knn-oneshot')]
    r_zero = [(d, f2[('gpt4o-mini', d, 'reason-then-edit - zero-shot')]['delta_points']) for d in sig('gpt4o-mini', 'reason-then-edit - zero-shot')]
    F.update(gpt_one_zero_min=min(one_zero), gpt_one_zero_max=max(one_zero), gpt_one_zero_nsig=len(one_zero),
             gpt_reason_one_hi=max(r_one), gpt_reason_one_lo=min(r_one),
             gpt_reason_one_same_dirs=sig('gpt4o-mini', 'reason-then-edit - knn-oneshot') == sig('gpt4o-mini', 'knn-oneshot - zero-shot'),
             gpt_reason_zero_only=r_zero[0][1] if len(r_zero) == 1 and r_zero[0][0] == 'tgl_Latn->eng_Latn' else None,
             llama_one_zero_nsig=len(sig('llama3-8b', 'knn-oneshot - zero-shot')))
    lr = [f2[('llama3-8b', d, c)]['delta_points'] for d in D for c in ['reason-then-edit - zero-shot', 'reason-then-edit - knn-oneshot']]
    F.update(llama_reason_contrast_hi=max(lr), llama_reason_contrast_lo=min(lr),
             llama_reason_all_sig=all(f2[('llama3-8b', d, c)]['significant_holm'] for d in D for c in ['reason-then-edit - zero-shot', 'reason-then-edit - knn-oneshot']))
    rc = [f2[(m, d, c)] for m in ['gpt4o-mini', 'llama3-8b'] for d in D for c in ['reason-then-edit - zero-shot', 'reason-then-edit - knn-oneshot']]
    F['reason_contrasts_all_negative'] = len(rc) if all(r['delta_points'] < 0 for r in rc) and not any(r['significant_holm'] and r['delta_points'] > 0 for r in rc) else None
    F['gpt_one_edited'] = pooled('gpt4o-mini', 'knn-oneshot', 'text_edited')
    F['gpt_one_edited_pct'] = 100 * F['gpt_one_edited'] / 4048
    F['protect_total'] = prot
    for m, s, k in [('gpt4o-mini', 'knn-oneshot', 'gpt_one'), ('gpt4o-mini', 'zero-shot', 'gpt_zero'), ('gpt4o-mini', 'reason-then-edit', 'gpt_reason'),
                    ('llama3-8b', 'zero-shot', 'llama_zero'), ('llama3-8b', 'knn-oneshot', 'llama_one'), ('llama3-8b', 'reason-then-edit', 'llama_reason')]:
        F[k + '_oe'] = oe(m, s)
        F[k + '_oe_pct'] = 100 * oe(m, s) / prot
    F['gpt_max_oe_pct'] = max(F[k] for k in ['gpt_one_oe_pct', 'gpt_zero_oe_pct', 'gpt_reason_oe_pct'])
    F['llama_reason_tlen_oe'] = cond('llama3-8b', 'reason-then-edit', 'tgl_Latn->eng_Latn')['overedit']['0.02']['numerator']
    F['tlen_protect'] = res['baseline_pools']['tgl_Latn->eng_Latn']['protect']
    F['llama_harm_gt_improve'] = sum(cond('llama3-8b', s, d)['harmed'] > cond('llama3-8b', s, d)['improved'] for s in S for d in D)
    F['gpt_improve_gt_harm'] = sum(cond('gpt4o-mini', s, d)['improved'] > cond('gpt4o-mini', s, d)['harmed'] for s in S for d in D)
    F['oe_order_all_thresholds'] = all(min(oe('llama3-8b', s, t) for s in S) > max(oe('gpt4o-mini', s, t) for s in S) for t in ['0.01', '0.02', '0.05'])
    dc = max((c['flags']['digit_change'], k) for k, c in C.items())
    F['max_digit_change'] = dc[0]
    F['max_digit_change_where'] = dc[1]
    lt = cond('llama3-8b', 'reason-then-edit', 'tgl_Latn->eng_Latn')['flags']
    F['llama_reason_tlen_lang'], F['llama_reason_tlen_lang_base'] = lt['language_mismatch'], lt['baseline_language_mismatch']
    p4 = json.loads((repo / 'docs/phase4/evidence/phase4_summary.json').read_text())['models']['gpt4o-mini']['estimated_cost_usd_uncached']
    rte = json.loads((repo / 'docs/phase3/evidence/rte_v3/gpt4o-mini_run_summary.json').read_text())
    pilot = json.loads((repo / 'docs/phase3/evidence/pilot/independent_numeric_audit.json').read_text())
    rv = repo / 'docs/phase5/evidence/source_review_summary.json'
    if rv.exists():
        R2 = json.loads(rv.read_text())
        A = R2['rule_A_summary']
        F['review_cases'] = R2['cases_reviewed']
        F['review_llama_genuine'] = A['llama3-8b'].get('genuine_error', 0)
        F['review_gpt_not_error'] = A['gpt4o-mini'].get('acceptable_penalized', 0) + A['gpt4o-mini'].get('source_supported_correction_penalized', 0)
        F['review_luxury_delta'] = next(c['delta_comet_points'] for c in R2['rule_A_classification']
                                        if c['model'] == 'gpt4o-mini' and c['sentence_id'] == 489)
        F['review_llama_reason_srclang'] = R2['source_language_outputs_langdetect']['llama3-8b/reason-then-edit']
    F['gpt_cost_total'] = p4 + sum(v.get('estimated_cost_usd_uncached', 0) for v in rte['conditions'].values()) + \
        next(v for k, v in _walk(pilot) if k == 'gpt_token_cost_estimate_usd')
    F.update(extended_facts(res, repo))
    return F


def extended_facts(res, repo):
    """Exploratory robustness facts (Report 5.1), computed by phase5_extended from the same committed evidence."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import phase5_extended as X
    o = X.analyse(res, json.loads((repo / 'docs/phase4/evidence/gpt4o-mini_run_summary.json').read_text()))
    X.check(o)
    mu = o['X1_multiplicity']
    F = {}
    F['ext_f1_unchanged_all_corrections'] = (not mu['F1']['changed_vs_holm']['bonferroni'] and not mu['F1']['changed_vs_holm']['bh_fdr']
                                             and not mu['pooled48_changed'])
    F['ext_f1_sig_n'] = mu['F1']['holm_frozen']
    F['ext_sig_sign_agree_all'] = o['X7_metric_concordance']['significant_sign_agree_all_three'] == mu['F1']['holm_frozen']
    F['ext_gpt_oe_upper_max'] = 100 * o['X5_summary']['gpt_max_upper_0.02']
    F['ext_llama_oe_lower_min'] = 100 * o['X5_summary']['llama_min_lower_0.02']
    F['ext_gpt_edit_harm_max'] = 100 * o['X6_summary']['gpt_harm_rate_max']
    F['ext_llama_edit_harm_min'] = 100 * o['X6_summary']['llama_harm_rate_min']
    F['ext_gap_reduction_min'] = o['X4_summary']['gpt_gap_reduction_min']
    F['ext_gap_reduction_max'] = o['X4_summary']['gpt_gap_reduction_max']
    F['ext_gap_middle_share_min'] = 100 * o['X4_summary']['gpt_std_gap_middle_share_min']
    lw = [r for r in o['X3_pool_decomposition'] if r['model'] == 'llama3-8b']
    neg = [r for r in lw if r['oracle_skip_strong'] < 0]
    F['ext_llama_skip_strong_negative'] = len(neg) if all(r['contribution']['middle'] < 0 for r in neg) else None
    return F


def _walk(d):
    if isinstance(d, dict):
        for k, v in d.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(d, list):
        for v in d:
            yield from _walk(v)
