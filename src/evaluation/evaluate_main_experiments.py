"""Norris Phase 5: evaluate the frozen devtest matrix (S0, unsplit diagnostic, 24 PE conditions).

Primary metric COMET-22 (Unbabel/wmt22-comet-da, pinned revision), x100 for reporting.
Secondary: SacreBLEU (13a, mixed case, exp smoothing) and chrF++ (c6, w2, beta 2), descriptive.
Confirmatory families (Holm, alpha .05, two-sided centered paired bootstrap, B=10,000, seed 42):
  F1 primary: each of 24 PE conditions minus S0, per direction.
  F2 strategy: within model x direction: one-shot - zero-shot, reason - zero-shot, reason - one-shot.
Everything else is descriptive/exploratory and labelled as such.

Evaluation environment: Python 3.11, torch 2.6.0+cu124, transformers 4.49.0,
unbabel-comet 2.2.7, numpy 1.26.4, sacrebleu 2.6.0, langdetect 1.0.9, pydantic 2.12.3,
rapidfuzz 3.10.1, pysbd 0.3.4.
"""
import argparse
import csv
import json
import math
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
sys.path[:0] = [str(HERE), str(SRC / 'common'), str(SRC / 'post_editing'), str(SRC / 'phase3' / 'post_editing'),
                str(SRC / 'baselines')]
import norris_protocol as P  # noqa: E402
import norris_stats as ST  # noqa: E402
import run_main_experiments as E  # noqa: E402
import analyze_pilots as A  # noqa: E402  measured preservation-flag definitions

COMET_ID, COMET_REV = 'Unbabel/wmt22-comet-da', P.REVISIONS['comet']
LANG = {'eng_Latn': 'en', 'tgl_Latn': 'tl', 'spa_Latn': 'es'}
SENT_RULE = {'eng_Latn': 'en', 'tgl_Latn': 'en', 'spa_Latn': 'es'}
BAND = 0.02
PROTECT, IMPROVE = 0.90, 0.80
SENSITIVITY = [0.01, 0.02, 0.05]
DNAME = {'eng_Latn->tgl_Latn': r'En$\to$Tl', 'tgl_Latn->eng_Latn': r'Tl$\to$En',
         'eng_Latn->spa_Latn': r'En$\to$Es', 'spa_Latn->eng_Latn': r'Es$\to$En'}
SNAME = {'zero-shot': 'Zero', 'knn-oneshot': 'One', 'reason-then-edit': 'Reason'}
MNAME = {'gpt4o-mini': 'GPT-4o Mini', 'llama3-8b': 'Llama 3 8B'}
STRATEGY_CONTRASTS = [('knn-oneshot', 'zero-shot'), ('reason-then-edit', 'zero-shot'),
                      ('reason-then-edit', 'knn-oneshot')]


def norm(text):
    return unicodedata.normalize('NFC', text.strip())


def comet_scores(triplets, cache_dir, env):
    import numpy as np
    cache_dir.mkdir(parents=True, exist_ok=True)
    cfg = P.digest(dict(model=COMET_ID, revision=COMET_REV, environment=env))
    keyf = lambda t: P.digest(dict(src=t[0], mt=t[1], ref=t[2], scoring=cfg))
    scores, pending = {}, {}
    for t in triplets:
        k = keyf(t)
        f = cache_dir / (k + '.json')
        if f.exists():
            x = P.read_json(f)
            P.require(x['key'] == k and math.isfinite(x['score']), 'COMET cache differs.')
            scores[t] = x['score']
        else:
            pending[k] = t
    if pending:
        import torch
        from comet import load_from_checkpoint
        from huggingface_hub import snapshot_download
        P.require(torch.cuda.is_available(), 'Use the A100 for COMET.')
        snap = Path(snapshot_download(repo_id=COMET_ID, revision=COMET_REV,
                                      allow_patterns=['checkpoints/model.ckpt', 'hparams.yaml']))
        model = load_from_checkpoint(str(snap / 'checkpoints/model.ckpt'))
        model.eval()
        items = list(pending.items())
        for s in range(0, len(items), 512):
            chunk = items[s:s + 512]
            pred = model.predict([dict(src=t[0], mt=t[1], ref=t[2]) for _, t in chunk], batch_size=64, gpus=1,
                                 progress_bar=False, num_workers=2, length_batching=True, mc_dropout=0)
            vals = np.asarray(pred.scores, dtype=np.float64)
            P.require(len(vals) == len(chunk) and np.isfinite(vals).all(), 'Invalid COMET output.')
            for (k, t), v in zip(chunk, vals):
                scores[t] = float(v)
                P.atomic_json(cache_dir / (k + '.json'), dict(key=k, score=float(v)))
            print('COMET', s + len(chunk), '/', len(items), flush=True)
    return scores, cfg


_SEG = {}


def sentence_count(text, language):
    import pysbd
    rule = SENT_RULE[language]
    if rule not in _SEG:
        _SEG[rule] = pysbd.Segmenter(language=rule, clean=False)
    return len([s for s in _SEG[rule].segment(text) if s.strip()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--freeze', required=True)
    ap.add_argument('--repo', default=None, help='repo root to write paper/generated and outputs/tables')
    args = ap.parse_args()
    import numpy as np
    from sacrebleu.metrics import BLEU, CHRF
    from langdetect import detect, DetectorFactory
    from rapidfuzz.distance import Levenshtein
    DetectorFactory.seed = 0
    root = Path(args.root)
    freeze = P.read_json(args.freeze)
    P.require(freeze.get('freeze_declared') is True and freeze['protocol']['fingerprint'] == P.protocol_fingerprint(),
              'Evaluation requires the declared freeze with this protocol.')
    jobs_dir = Path(P.read_json(root / 'outputs/phase4/main_prepared_latest.json')['jobs_dir'])
    _, manifest, jobs = E.load_jobs(jobs_dir)
    P.require(manifest['partition'] == 'devtest' and manifest['freeze_sha256'] == P.file_sha256(args.freeze),
              'Prepared jobs are not bound to this freeze.')
    jmap = {j['job_key']: j for j in jobs}
    gold = {(g['direction'], g['sentence_id']): g for g in P.read_jsonl(jobs_dir / 'gold_devtest.jsonl')}
    P.require(len(gold) == 4048, 'Expected 4,048 gold rows.')
    ids = {d: sorted(sid for (dd, sid) in gold if dd == d) for d in P.DIRECTION_KEYS}
    P.require(all(len(v) == 1012 for v in ids.values()), 'Each direction needs 1,012 IDs.')

    # ---------------- coverage audit and records
    records, runs, coverage = {}, {}, {}
    for model in P.MODELS:
        latest = P.read_json(jobs_dir / f'{model}_latest_run.json')
        runs[model] = P.read_json(Path(latest['run_dir']) / 'run_spec.json')
        for d in P.DIRECTION_KEYS:
            for s in P.STRATEGIES:
                f = Path(latest.get('generations_dir', jobs_dir / 'generations')) / f'{model}_{s}_{P.SHORT[d]}.jsonl'
                P.require(f.exists(), 'Missing condition file: ' + f.name)
                recs = P.read_jsonl(f)
                for r in recs:
                    E.validate_record(r, jmap[r['job_key']], latest['run_sha256'])
                    P.require(r['direction'] == d and r['strategy'] == s, 'Condition labels differ.')
                got = sorted(r['sentence_id'] for r in recs)
                P.require(got == ids[d], f'{f.name}: IDs differ from the 1,012 planned IDs.')
                records[(model, s, d)] = {r['sentence_id']: r for r in recs}
                coverage[f'{model}/{d}/{s}'] = dict(n=len(recs), file_sha256=P.file_sha256(f))
    P.require(len(records) == 24, 'Exactly 24 post-editing conditions are required.')

    env = {k: version(k) for k in ['torch', 'transformers', 'unbabel-comet', 'numpy', 'sacrebleu',
                                   'langdetect', 'huggingface-hub', 'rapidfuzz', 'pysbd']}
    spec = dict(stage='phase5_main_evaluation', freeze_sha256=P.file_sha256(args.freeze),
                prepared_manifest_sha256=P.digest(manifest), run_specs={m: P.digest(v) for m, v in runs.items()},
                COMET=dict(model=COMET_ID, revision=COMET_REV), environment=env,
                stats=dict(B=ST.B, seed=ST.SEED, alpha=ST.ALPHA, practical_band_points=ST.PRACTICAL_BAND_POINTS,
                           families=['F1_primary_vs_S0_24', 'F2_strategy_24'], test='two-sided centered paired bootstrap'),
                thresholds=dict(band=BAND, protect=PROTECT, improve=IMPROVE, sensitivity=SENSITIVITY),
                evaluator_sha256=P.file_sha256(Path(__file__)), stats_sha256=P.file_sha256(Path(ST.__file__)))
    sha = P.digest(spec)
    out = root / 'outputs/phase5' / ('eval_' + sha[:16])
    out.mkdir(parents=True, exist_ok=True)
    P.atomic_json(out / 'evaluation_spec.json', spec)

    # ---------------- scoring
    triplets = set()
    for (d, sid), g in gold.items():
        triplets.add((g['source_text'], g['baseline_translation'], g['reference_text']))
        triplets.add((g['source_text'], g['unsplit_translation'], g['reference_text']))
    for (m, s, d), recs in records.items():
        for sid, r in recs.items():
            g = gold[(d, sid)]
            triplets.add((g['source_text'], r['edited_translation'], g['reference_text']))
    scores, score_cfg = comet_scores(sorted(triplets), out / 'comet_cache', env)
    C = lambda d, sid, mt: scores[(gold[(d, sid)]['source_text'], mt, gold[(d, sid)]['reference_text'])]

    lidc = {}

    def lid(t):
        if t not in lidc:
            try:
                lidc[t] = detect(t)
            except Exception:
                lidc[t] = 'unknown'
        return lidc[t]

    idx = ST.resample_index(1012)
    systems = {}
    metric_rows = []
    bleu, chrf = BLEU(tokenize='13a'), CHRF(char_order=6, word_order=2, beta=2)
    for d in P.DIRECTION_KEYS:
        refs = [[gold[(d, sid)]['reference_text'] for sid in ids[d]]]
        base_scores = np.array([C(d, sid, gold[(d, sid)]['baseline_translation']) for sid in ids[d]])
        uns_scores = np.array([C(d, sid, gold[(d, sid)]['unsplit_translation']) for sid in ids[d]])
        systems[('S0', d)] = base_scores
        systems[('S0u', d)] = uns_scores
        for name, key, sc in [('S0 split NLLB', 'baseline_translation', base_scores),
                              ('Unsplit NLLB (diagnostic)', 'unsplit_translation', uns_scores)]:
            hyp = [gold[(d, sid)][key] for sid in ids[d]]
            metric_rows.append(dict(system=name, model=None, strategy=None, direction=d, n=1012,
                                    COMET_points=float(sc.mean() * 100), BLEU=bleu.corpus_score(hyp, refs).score,
                                    chrFpp=chrf.corpus_score(hyp, refs).score))
        for (m, s, dd), recs in records.items():
            if dd != d:
                continue
            sc = np.array([C(d, sid, recs[sid]['edited_translation']) for sid in ids[d]])
            systems[((m, s), d)] = sc
            hyp = [recs[sid]['edited_translation'] for sid in ids[d]]
            metric_rows.append(dict(system=f'{MNAME[m]} {SNAME[s]}', model=m, strategy=s, direction=d, n=1012,
                                    COMET_points=float(sc.mean() * 100), BLEU=bleu.corpus_score(hyp, refs).score,
                                    chrFpp=chrf.corpus_score(hyp, refs).score))
    signatures = dict(BLEU=str(bleu.get_signature()), chrF=str(chrf.get_signature()))

    # ---------------- confirmatory families
    f1 = []
    for m in P.MODELS:
        for s in P.STRATEGIES:
            for d in P.DIRECTION_KEYS:
                r = ST.paired_test(systems[((m, s), d)], systems[('S0', d)], idx)
                f1.append(dict(family='F1_primary', model=m, strategy=s, direction=d,
                               contrast=f'{s} - S0', **r))
    for r, a in zip(f1, ST.holm([x['p_raw'] for x in f1])):
        r['p_holm'] = a
        r['significant_holm'] = a < ST.ALPHA
        r['marker'] = ST.marker(a)
    f2 = []
    for m in P.MODELS:
        for d in P.DIRECTION_KEYS:
            for a_s, b_s in STRATEGY_CONTRASTS:
                r = ST.paired_test(systems[((m, a_s), d)], systems[((m, b_s), d)], idx)
                f2.append(dict(family='F2_strategy', model=m, direction=d, contrast=f'{a_s} - {b_s}', **r))
    for r, a in zip(f2, ST.holm([x['p_raw'] for x in f2])):
        r['p_holm'] = a
        r['significant_holm'] = a < ST.ALPHA
        r['marker'] = ST.marker(a)
    diag = [dict(family='diagnostic_segmentation', direction=d, contrast='S0 split - unsplit',
                 **ST.paired_test(systems[('S0', d)], systems[('S0u', d)], idx)) for d in P.DIRECTION_KEYS]

    # ---------------- per-segment analysis, over-editing, failures, flags
    seg_rows, cond = [], {}
    for (m, s, d), recs in sorted(records.items()):
        rows = []
        tgt = d.split('->')[1]
        src = d.split('->')[0]
        for sid in ids[d]:
            g, r = gold[(d, sid)], recs[sid]
            hyp, base = r['edited_translation'], g['baseline_translation']
            bs, es = C(d, sid, base), C(d, sid, hyp)
            edited = norm(hyp) != norm(base)
            dist = Levenshtein.distance(norm(hyp), norm(base))
            ratio = len(hyp.split()) / max(1, len(g['source_text'].split()))
            n_src = g['input_segment_count']
            n_base = sentence_count(base, tgt) if n_src > 1 else None
            n_hyp = sentence_count(hyp, tgt) if n_src > 1 else None
            row = dict(model=m, strategy=s, direction=d, sentence_id=sid, baseline_comet_native=bs,
                       comet_native=es, delta_comet_native=es - bs, text_edited=edited, char_edit_distance=dist,
                       norm_edit_distance=dist / max(1, len(norm(hyp)), len(norm(base))),
                       usable=r['usable'], fallback_used=r['fallback_used'], failure_class=P.failure_class(r),
                       finish_reason=r['finish_reason'], pool=('protect' if bs >= PROTECT else
                                                               'improve' if bs < IMPROVE else 'middle'),
                       language_predicted=lid(hyp), language_expected=LANG[tgt],
                       language_mismatch_flag=lid(hyp) not in (LANG[tgt], 'unknown'),
                       baseline_language_mismatch_flag=lid(base) not in (LANG[tgt], 'unknown'),
                       output_source_word_ratio=ratio, length_anomaly_flag=ratio > 2.5 or ratio < .4,
                       source_segments=n_src, baseline_sentences=n_base, edited_sentences=n_hyp,
                       sentence_drop_flag=bool(n_src > 1 and n_base is not None and n_hyp < n_base),
                       sentence_restore_flag=bool(n_src > 1 and n_base is not None and n_base < n_src <= n_hyp),
                       prompt_tokens=r['prompt_token_count'], completion_tokens=r['completion_token_count'],
                       **{k: v for k, v in A.preservation_flags(g['source_text'], base, hyp).items()
                          if k != 'preservation_interpretation'})
            rows.append(row)
        seg_rows.extend(rows)
        protect = [x for x in rows if x['pool'] == 'protect']
        dl = [x['delta_comet_native'] for x in rows]
        c = dict(model=m, strategy=s, direction=d, n=len(rows), usable=sum(x['usable'] for x in rows),
                 fallback=sum(x['fallback_used'] for x in rows),
                 failure_classes={k: sum(x['failure_class'] == k for x in rows)
                                  for k in sorted({x['failure_class'] for x in rows})},
                 text_edited=sum(x['text_edited'] for x in rows),
                 mean_norm_edit_distance_edited=(statistics.mean(x['norm_edit_distance'] for x in rows if x['text_edited'])
                                                 if any(x['text_edited'] for x in rows) else None),
                 improved=sum(v > BAND for v in dl), within_band=sum(-BAND <= v <= BAND for v in dl),
                 harmed=sum(v < -BAND for v in dl),
                 protect_n=len(protect), improve_pool_n=sum(x['pool'] == 'improve' for x in rows),
                 middle_pool_n=sum(x['pool'] == 'middle' for x in rows),
                 overedit={str(t): dict(numerator=sum(x['text_edited'] and x['delta_comet_native'] < -t for x in protect),
                                        denominator=len(protect),
                                        rate_pct=(100 * sum(x['text_edited'] and x['delta_comet_native'] < -t
                                                            for x in protect) / len(protect)) if protect else None)
                           for t in SENSITIVITY},
                 pool_mean_delta_points={pool: (100 * statistics.mean(x['delta_comet_native'] for x in rows if x['pool'] == pool)
                                                if any(x['pool'] == pool for x in rows) else None)
                                         for pool in ['protect', 'middle', 'improve']},
                 flags=dict(digit_change=sum(x['digit_change_flag'] for x in rows),
                            digit_loss=sum(x['digit_loss_flag'] for x in rows),
                            capitalized_token_loss=sum(bool(x['newly_absent_capitalized_source_tokens']) for x in rows),
                            language_mismatch=sum(x['language_mismatch_flag'] for x in rows),
                            baseline_language_mismatch=sum(x['baseline_language_mismatch_flag'] for x in rows),
                            length_anomaly=sum(x['length_anomaly_flag'] for x in rows),
                            sentence_drop=sum(x['sentence_drop_flag'] for x in rows),
                            sentence_restore=sum(x['sentence_restore_flag'] for x in rows)),
                 tokens=dict(prompt=sum(x['prompt_tokens'] for x in rows), completion=sum(x['completion_tokens'] for x in rows)))
        cond[f'{m}/{d}/{s}'] = c

    base_pools = {d: dict(protect=int((systems[('S0', d)] >= PROTECT).sum()),
                          improve=int((systems[('S0', d)] < IMPROVE).sum()), n=1012) for d in P.DIRECTION_KEYS}
    results = dict(status='phase5_scored', evaluation_sha256=sha, coverage=coverage, metric_signatures=signatures,
                   COMET_score_config=score_cfg, unique_triplets=len(triplets), metrics=metric_rows,
                   F1_primary=f1, F2_strategy=f2, diagnostic_segmentation=diag, conditions=cond,
                   baseline_pools=base_pools,
                   interpretation_rules=dict(nonsignificant='inconclusive', practical_band='CI within +/-0.5 points; '
                                             'not proof of identical systems', pair_or_direction_differences=
                                             'not inferred from significance patterns; estimates with intervals only'),
                   created_utc=datetime.now(timezone.utc).isoformat())
    P.atomic_json(out / 'main_results.json', results)
    P.write_jsonl(out / 'segment_scores_numeric.jsonl', seg_rows)
    for name, rows in [('F1_primary.csv', f1), ('F2_strategy.csv', f2), ('metrics.csv', metric_rows)]:
        with (out / name).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()})
    P.atomic_json(root / 'outputs/phase5/latest.json', dict(output_dir=str(out), evaluation_sha256=sha))
    write_tables(results, out / 'tables')
    if args.repo:
        repo = Path(args.repo)
        write_tables(results, repo / 'outputs' / 'tables')
        write_tables(results, repo / 'paper' / 'generated')
    print('PHASE 5 COMPLETE:', out)


# ------------------------------------------------------------------ LaTeX
def write_tables(res, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    f1 = {(r['model'], r['strategy'], r['direction']): r for r in res['F1_primary']}
    met = {(r['model'], r['strategy'], r['direction']): r for r in res['metrics']}
    base = {r['direction']: r for r in res['metrics'] if r['system'] == 'S0 split NLLB'}
    L = [r'\begin{table*}[t]', r'\centering\footnotesize',
         r'\caption{Held-out FLORES+ devtest results (1{,}012 items per direction; all planned outputs, including '
         r'baseline fallback). C: COMET-22$\times$100; $\Delta$: post-edit minus sentence-split NLLB (S0) with paired '
         r'95\% bootstrap interval; markers use Holm-adjusted $p$ over the 24-test primary family '
         r'($^\dagger p<.05$, $^\ddagger p<.01$). FB: baseline fallbacks. BLEU/chrF++ are descriptive.}',
         r'\label{tab:main}', r'\setlength{\tabcolsep}{3pt}', r'\resizebox{\textwidth}{!}{%',
         r'\begin{tabular}{ll' + 'rrr' * 4 + '}', r'\toprule',
         r' & & ' + ' & '.join(r'\multicolumn{3}{c}{' + DNAME[d] + '}' for d in P.DIRECTION_KEYS) + r' \\',
         ''.join(r'\cmidrule(lr){' + f'{3 + 3 * i}-{5 + 3 * i}' + '}' for i in range(4)),
         r'Editor & Strategy & ' + ' & '.join(['C & $\\Delta$ [95\\% CI] & FB'] * 4) + r' \\', r'\midrule',
         r'\multicolumn{2}{l}{S0 split NLLB} & ' + ' & '.join(f"{base[d]['COMET_points']:.2f} & -- & --"
                                                            for d in P.DIRECTION_KEYS) + r' \\', r'\midrule']
    for m in ['gpt4o-mini', 'llama3-8b']:
        for s in P.STRATEGIES:
            cells = []
            for d in P.DIRECTION_KEYS:
                r, c = f1[(m, s, d)], res['conditions'][f'{m}/{d}/{s}']
                lo, hi = r['ci95_points']
                cells.append(f"{met[(m, s, d)]['COMET_points']:.2f} & {r['delta_points']:+.2f}{r['marker']} "
                             f"[{lo:+.2f}, {hi:+.2f}] & {c['fallback']}")
            L.append(f"{MNAME[m] if s == 'zero-shot' else ''} & {SNAME[s]} & " + ' & '.join(cells) + r' \\')
        L.append(r'\midrule')
    L[-1] = r'\bottomrule'
    L += [r'\end{tabular}}', r'\end{table*}']
    (outdir / 'main_results_matrix.tex').write_text('\n'.join(L) + '\n')

    O = [r'\begin{table}[t]', r'\centering\footnotesize',
         r'\caption{Protect-pool over-editing on devtest: over-edited items / protect-pool items per direction '
         r'(protect: S0 COMET$\geq$0.90; over-edit: text changed and native COMET loss $>$0.02).}', r'\label{tab:overedit}',
         r'\setlength{\tabcolsep}{3pt}', r'\begin{tabular}{ll' + 'r' * 4 + '}', r'\toprule',
         r'Editor & Strategy & ' + ' & '.join(DNAME[d] for d in P.DIRECTION_KEYS) + r' \\', r'\midrule']
    for m in ['gpt4o-mini', 'llama3-8b']:
        for s in P.STRATEGIES:
            cells = []
            for d in P.DIRECTION_KEYS:
                c = res['conditions'][f'{m}/{d}/{s}']
                o = c['overedit']['0.02']
                cells.append(f"{o['numerator']}/{o['denominator']}")
            O.append(f"{MNAME[m] if s == 'zero-shot' else ''} & {SNAME[s]} & " + ' & '.join(cells) + r' \\')
        O.append(r'\midrule')
    O[-1] = r'\bottomrule'
    O += [r'\end{tabular}', r'\end{table}']
    (outdir / 'overediting_table.tex').write_text('\n'.join(O) + '\n')

    S2 = [r'\begin{table}[t]', r'\centering\footnotesize',
          r'\caption{Strategy contrasts (COMET points, paired 95\% CI; Holm over the 24-test strategy family).}',
          r'\label{tab:strategy}', r'\setlength{\tabcolsep}{2.5pt}', r'\begin{tabular}{lll r}', r'\toprule',
          r'Editor & Dir. & Contrast & $\Delta$ [95\% CI] \\', r'\midrule']
    short = {'knn-oneshot - zero-shot': 'One$-$Zero', 'reason-then-edit - zero-shot': 'Reason$-$Zero',
             'reason-then-edit - knn-oneshot': 'Reason$-$One'}
    for r in res['F2_strategy']:
        lo, hi = r['ci95_points']
        S2.append(f"{MNAME[r['model']]} & {DNAME[r['direction']]} & {short[r['contrast']]} & "
                  f"{r['delta_points']:+.2f}{r['marker']} [{lo:+.2f}, {hi:+.2f}]" + r' \\')
    S2 += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    (outdir / 'strategy_contrasts.tex').write_text('\n'.join(S2) + '\n')

    # Macros for in-text numbers (audited by src/analysis/audit_manuscript.py)
    M = ['% Auto-generated by evaluate_main_experiments.py; do not edit by hand.']
    alpha = lambda s: ''.join(ch for ch in s.title() if ch.isalpha())
    for r in res['F1_primary']:
        k = alpha(r['model'].replace('4o', 'Four').replace('3', 'Three').replace('8b', 'Eight')) + \
            alpha(r['strategy']) + alpha(P.SHORT[r['direction']])
        M.append(f"\\newcommand{{\\D{k}}}{{{r['delta_points']:+.2f}}}")
        M.append(f"\\newcommand{{\\CIlo{k}}}{{{r['ci95_points'][0]:+.2f}}}")
        M.append(f"\\newcommand{{\\CIhi{k}}}{{{r['ci95_points'][1]:+.2f}}}")
        c = res['conditions'][f"{r['model']}/{r['direction']}/{r['strategy']}"]
        M.append(f"\\newcommand{{\\FB{k}}}{{{c['fallback']}}}")
        M.append(f"\\newcommand{{\\OE{k}}}{{{c['overedit']['0.02']['numerator']}/{c['overedit']['0.02']['denominator']}}}")
    M.append(f"\\newcommand{{\\NsigPrimary}}{{{sum(r['significant_holm'] for r in res['F1_primary'])}}}")
    M.append(f"\\newcommand{{\\NsigStrategy}}{{{sum(r['significant_holm'] for r in res['F2_strategy'])}}}")
    (outdir / 'results_macros.tex').write_text('\n'.join(M) + '\n')


if __name__ == '__main__':
    main()
