"""Score the dev reason-then-edit v3 rerun and assemble the revised dev evidence.

Run in the pinned evaluation environment (Python 3.11, torch 2.6.0+cu124,
transformers 4.49.0, unbabel-comet 2.2.7, numpy 1.26.4, sacrebleu 2.6.0,
langdetect 1.0.9, pydantic 2.12.3). Metric/flag definitions are imported from the
measured analyze_pilots.py so v2 and v3 rows are computed identically.

Checks performed:
  * measured v2 analysis signature and v2 run records (both models)
  * frozen output contract reproduces every stored v2 zero-shot/one-shot outcome (1,600 records)
  * v3 condition files: 4 x 100 per model, record/job hashes, fallback = baseline draft
  * baseline COMET recheck within 1e-5 native of the original pilot scores
Outputs a revised 24-condition dev table (ZS/OS from v2; RTE from v3), a v2-vs-v3
reason-then-edit comparison, failure accounting and the predeclared reliability gate.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'common'))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'post_editing'))
import norris_protocol as P  # noqa: E402
import analyze_pilots as A  # noqa: E402  measured definitions: aggregate, preservation_flags, paired_ci
import run_main_experiments as E  # noqa: E402  record validation

COMET_ID, COMET_REV = 'Unbabel/wmt22-comet-da', P.REVISIONS['comet']
LANG = {'eng_Latn': 'en', 'tgl_Latn': 'tl', 'spa_Latn': 'es'}


def load_v2(state_dir):
    ptr = P.read_json(state_dir / 'analysis_latest_run.json')
    P.require(ptr['analysis_sha256'] == P.V2_PILOT_ANALYSIS_SHA, 'Latest analysis is not the measured v2 analysis.')
    adir = Path(ptr['output_dir'])
    summary = P.read_json(adir / 'pilot_summary.json')
    P.require(summary['analysis_sha256'] == P.V2_PILOT_ANALYSIS_SHA, 'v2 summary signature differs.')
    runs = {}
    for model, name in [('llama3-8b', 'llama_latest_run.json'), ('gpt4o-mini', 'gpt_latest_run.json')]:
        rp = P.read_json(state_dir / name)
        P.require(rp['stage'] == 'full', 'v2 full run pointer required for ' + model)
        runs[model] = P.read_jsonl(Path(rp['output_dir']) / 'full_outputs.jsonl')
        P.require(len(runs[model]) == 1200, 'v2 run incomplete: ' + model)
    segs = P.read_jsonl(adir / 'segment_analysis.jsonl')
    P.require(len(segs) == 2400, 'v2 segment analysis must contain 2,400 rows.')
    return adir, summary, runs, segs


def verify_plain_equivalence(runs, v2_jobs):
    jmap = {j['job_key']: j for j in v2_jobs}
    checked = 0
    for model, records in runs.items():
        for r in records:
            if r['strategy'] == 'reason-then-edit':
                continue
            P.require(r['content_sha256'] == P.digest({k: v for k, v in r.items() if k != 'content_sha256'}),
                      'v2 record checksum differs.')
            j = jmap[r['job_key']]
            P.require(r['job_sha256'] == j['job_sha256'], 'v2 job link differs.')
            v = P.extract_response(r['raw_completion'], r['strategy'], j['query']['draft'], r['finish_reason'])
            for k in ['json_parse_success', 'schema_valid', 'usable', 'edited_translation', 'fallback_used']:
                P.require(v[k] == r[k], f'Frozen contract changes a measured v2 outcome: {model} {r["job_key"]} {k}')
            checked += 1
    P.require(checked == 1600, 'Expected 1,600 plain v2 outcomes.')
    return checked


def comet_scores(triplets, cache_dir, env):
    import numpy as np
    cache_dir.mkdir(parents=True, exist_ok=True)
    cfg = P.digest(dict(model=COMET_ID, revision=COMET_REV, environment=env))
    key = lambda t: P.digest(dict(src=t['src'], mt=t['mt'], ref=t['ref'], scoring=cfg))
    out, pending = {}, []
    for t in triplets:
        k = key(t)
        f = cache_dir / (k + '.json')
        if f.exists():
            x = P.read_json(f)
            P.require(x['key'] == k and math.isfinite(x['score']), 'COMET cache differs.')
            out[k] = x['score']
        elif k not in {p[0] for p in pending}:
            pending.append((k, t))
    if pending:
        import torch
        from comet import load_from_checkpoint
        from huggingface_hub import snapshot_download
        P.require(torch.cuda.is_available(), 'Use the A100 for COMET.')
        snap = Path(snapshot_download(repo_id=COMET_ID, revision=COMET_REV,
                                      allow_patterns=['checkpoints/model.ckpt', 'hparams.yaml']))
        model = load_from_checkpoint(str(snap / 'checkpoints/model.ckpt'))
        model.eval()
        for s in range(0, len(pending), 128):
            chunk = pending[s:s + 128]
            pred = model.predict([c[1] for c in chunk], batch_size=64, gpus=1, progress_bar=False,
                                 num_workers=2, length_batching=True, mc_dropout=0)
            vals = np.asarray(pred.scores, dtype=np.float64)
            P.require(len(vals) == len(chunk) and np.isfinite(vals).all(), 'Invalid COMET output.')
            for (k, _), v in zip(chunk, vals):
                out[k] = float(v)
                P.atomic_json(cache_dir / (k + '.json'), dict(key=k, score=float(v)))
            print('COMET', s + len(chunk), '/', len(pending), flush=True)
    return {(t['src'], t['mt'], t['ref']): out[key(t)] for t in triplets}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    args = ap.parse_args()
    from sacrebleu.metrics import BLEU, CHRF
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    root = Path(args.root)
    state = root / 'outputs/phase3_post_editing'
    jobs_dir = Path(P.read_json(state / 'rte_v3_latest.json')['jobs_dir'])
    _, manifest, jobs = E.load_jobs(jobs_dir)
    v2_dir = Path(manifest['v2_prepared_dir'])
    v2_jobs = P.read_jsonl(v2_dir / 'jobs.jsonl')
    v2_adir, v2_summary, v2_runs, v2_segs = load_v2(state)
    plain_checked = verify_plain_equivalence(v2_runs, v2_jobs)
    gold = {(g['direction'], g['sentence_id']): g for g in P.read_jsonl(jobs_dir / 'evaluation_gold.jsonl')}
    jmap = {j['job_key']: j for j in jobs}

    v3 = {}
    for model in P.MODELS:
        latest = P.read_json(jobs_dir / f'{model}_latest_run.json')
        run_sha = latest['run_sha256']
        rows = []
        for d in P.DIRECTION_KEYS:
            f = Path(latest.get('generations_dir', jobs_dir / 'generations')) / f'{model}_reason-then-edit_{P.SHORT[d]}.jsonl'
            recs = P.read_jsonl(f)
            P.require(len(recs) == 100 and len({r['sentence_id'] for r in recs}) == 100, 'Incomplete v3 condition.')
            for r in recs:
                E.validate_record(r, jmap[r['job_key']], run_sha)
            rows.extend(recs)
        v3[model] = rows

    env = {k: version(k) for k in ['torch', 'transformers', 'unbabel-comet', 'numpy', 'sacrebleu',
                                   'langdetect', 'huggingface-hub']}
    spec = dict(stage='phase3_rte_v3_dev_analysis', jobs_manifest_sha256=P.digest(manifest),
                v2_analysis_sha256=P.V2_PILOT_ANALYSIS_SHA, COMET_model=COMET_ID, COMET_revision=COMET_REV,
                environment=env, seed=42, bootstrap_resamples=10000, chrF=dict(char_order=6, word_order=2, beta=2),
                BLEU_tokenizer='13a', definitions_source_sha256=P.file_sha256(Path(A.__file__)),
                scorer_sha256=P.file_sha256(Path(__file__)), reliability_gate=manifest['reliability_gate'])
    sha = P.digest(spec)
    out = jobs_dir / 'analysis' / sha[:16]
    out.mkdir(parents=True, exist_ok=True)
    P.atomic_json(out / 'analysis_spec.json', spec)

    triplets = []
    for g in gold.values():
        triplets.append(dict(src=g['source_text'], mt=g['baseline_translation'], ref=g['reference_text']))
    for rows in v3.values():
        for r in rows:
            g = gold[(r['direction'], r['sentence_id'])]
            triplets.append(dict(src=g['source_text'], mt=r['edited_translation'], ref=g['reference_text']))
    scores = comet_scores(triplets, out / 'comet_cache', env)
    recheck = max(abs(scores[(g['source_text'], g['baseline_translation'], g['reference_text'])] -
                      g['baseline_comet_native']) for g in gold.values())
    P.atomic_json(out / 'baseline_recheck.json', dict(n=400, max_abs_difference_native=recheck, tolerance=1e-5))
    P.require(recheck <= 1e-5, f'Baseline COMET recheck differs ({recheck:.2e}); stop for review.')

    lidc = {}

    def lid(t):
        if t not in lidc:
            try:
                lidc[t] = detect(t)
            except Exception:
                lidc[t] = 'unknown'
        return lidc[t]

    details, groups = [], {}
    for model, rows in v3.items():
        for r in rows:
            g = gold[(r['direction'], r['sentence_id'])]
            hyp = r['edited_translation']
            bs = scores[(g['source_text'], g['baseline_translation'], g['reference_text'])]
            sc = scores[(g['source_text'], hyp, g['reference_text'])]
            tgt = LANG[r['direction'].split('->')[1]]
            ratio = len(hyp.split()) / max(1, len(g['source_text'].split()))
            details.append(dict(
                model=model, job_key=r['job_key'], direction=r['direction'], strategy=r['strategy'],
                sentence_id=r['sentence_id'], edited_translation=hyp, diagnosis=r['diagnosis'],
                diagnosis_words=len(r['diagnosis'].split()) if r['diagnosis'] else None,
                baseline_comet_original_native=g['baseline_comet_native'], baseline_comet_native=bs,
                comet_native=sc, delta_comet_native=sc - bs, text_edited=hyp != g['baseline_translation'],
                json_parse_success=r['json_parse_success'], schema_valid=r['schema_valid'], usable=r['usable'],
                fallback_used=r['fallback_used'], validation_error=r['validation_error'],
                finish_reason=r['finish_reason'], failure_class=P.failure_class(r),
                language_predicted=lid(hyp), language_expected=tgt,
                language_mismatch_flag=lid(hyp) not in [tgt, 'unknown'],
                reference_language_mismatch_flag=lid(g['reference_text']) not in [tgt, 'unknown'],
                output_source_word_ratio=ratio, length_anomaly_flag=ratio > 2.5 or ratio < .4,
                NONE_with_text_change=False,  # not applicable: v3 has no NONE category
                analysis_latency_ms=r.get('request_latency_ms') or r.get('batch_amortized_ms'),
                latency_definition=r['latency_definition'],
                **A.preservation_flags(g['source_text'], g['baseline_translation'], hyp)))
        for d in P.DIRECTION_KEYS:
            sub = [x for x in details if x['model'] == model and x['direction'] == d]
            a = A.aggregate(sub)
            a['NONE_with_text_change'] = 'not_applicable_v3'
            hyp = [x['edited_translation'] for x in sub]
            refs = [[gold[(d, x['sentence_id'])]['reference_text'] for x in sub]]
            b, f = BLEU(tokenize='13a'), CHRF(char_order=6, word_order=2, beta=2)
            a.update(BLEU=b.corpus_score(hyp, refs).score, chrFpp=f.corpus_score(hyp, refs).score,
                     BLEU_signature=str(b.get_signature()), chrF_signature=str(f.get_signature()),
                     failure_classes={c: sum(x['failure_class'] == c for x in sub)
                                      for c in sorted({x['failure_class'] for x in sub})},
                     diagnosis_words_median=statistics.median([x['diagnosis_words'] for x in sub
                                                               if x['diagnosis_words']] or [0]))
            groups[f'{model}/{d}/reason-then-edit'] = a

    # Revised 24-condition dev table: ZS/OS = measured v2 (unchanged); RTE = v3.
    revised, compare = [], []
    for model in P.MODELS:
        for d in P.DIRECTION_KEYS:
            for s in P.STRATEGIES:
                key = f'{model}/{d}/{s}'
                row = groups[key] if s == 'reason-then-edit' else v2_summary['groups'][key]
                revised.append(dict(model=model, direction=d, strategy=s,
                                    contract=P.RTE_VERSION if s == 'reason-then-edit' else P.PLAIN_VERSION,
                                    **{k: row[k] for k in ['n', 'usable', 'fallbacks', 'text_edited', 'BLEU',
                                                           'chrFpp', 'COMET_points', 'delta_COMET_points',
                                                           'delta_COMET_95CI_points', 'improved', 'within_band',
                                                           'harmed', 'protect_n', 'overedited_protect_n']}))
            old, new = v2_summary['groups'][f'{model}/{d}/reason-then-edit'], groups[f'{model}/{d}/reason-then-edit']
            compare.append(dict(model=model, direction=d,
                                **{f'{tag}_{k}': src[k] for tag, src in [('v2', old), ('v3', new)]
                                   for k in ['usable', 'fallbacks', 'text_edited', 'delta_COMET_points',
                                             'delta_COMET_95CI_points', 'harmed', 'overedited_protect_n']}))
    gate_cfg = manifest['reliability_gate']
    gate = {}
    for model in P.MODELS:
        per_dir = {d: groups[f'{model}/{d}/reason-then-edit']['fallbacks'] for d in P.DIRECTION_KEYS}
        total = sum(per_dir.values())
        gate[model] = dict(fallbacks_total=total, fallbacks_by_direction=per_dir,
                           passes=total <= gate_cfg['max_fallback_per_model'] and
                           max(per_dir.values()) <= gate_cfg['max_fallback_per_direction'])
    gate_pass = all(v['passes'] for v in gate.values())
    pooled = {}
    for model in P.MODELS:
        sub = [x for x in details if x['model'] == model]
        pooled[model] = dict(n=len(sub), text_edited=sum(x['text_edited'] for x in sub),
                             improved=sum(x['delta_comet_native'] > .02 for x in sub),
                             harmed=sum(x['delta_comet_native'] < -.02 for x in sub),
                             protect_n=sum(x['baseline_comet_original_native'] >= .9 for x in sub),
                             overedited_protect_n=sum(x['baseline_comet_original_native'] >= .9 and x['text_edited']
                                                      and x['delta_comet_native'] < -.02 for x in sub))
    summary = dict(status='rte_v3_dev_scored', analysis_sha256=sha, gate=gate, gate_pass=gate_pass,
                   gate_rule=gate_cfg['rule'], plain_v2_outcomes_reproduced=plain_checked,
                   baseline_recheck_max_abs_native=recheck, groups_rte_v3=groups, pooled_rte_v3=pooled,
                   v2_vs_v3=compare, devtest_opened=False, freeze_declared=False,
                   next_step=('Build the freeze package and send to PI; then Phase 4.' if gate_pass else
                              'Gate failed: bring to PI (retain as explicit failure condition or remove). '
                              'Do not iterate on the prompt.'),
                   created_utc=datetime.now(timezone.utc).isoformat())
    P.atomic_json(out / 'rte_v3_summary.json', summary)
    P.write_jsonl(out / 'segment_analysis_rte_v3.jsonl', details)
    with (out / 'revised_dev_conditions.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(revised[0]))
        w.writeheader()
        for r in revised:
            w.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()})
    with (out / 'rte_v2_vs_v3.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(compare[0]))
        w.writeheader()
        for r in compare:
            w.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()})
    numeric = [{k: v for k, v in d.items() if k not in ('edited_translation', 'diagnosis', 'validation_error')}
               for d in details]
    P.write_jsonl(out / 'segment_scores_rte_v3_numeric.jsonl', numeric)
    P.atomic_json(state / 'rte_v3_analysis_latest.json', dict(output_dir=str(out), analysis_sha256=sha))
    print(json.dumps(dict(gate=gate, gate_pass=gate_pass, plain_reproduced=plain_checked,
                          recheck=recheck), indent=2))
    print('ANALYSIS:', out)


if __name__ == '__main__':
    main()
