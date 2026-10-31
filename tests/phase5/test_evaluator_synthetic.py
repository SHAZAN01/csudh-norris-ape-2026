"""Synthetic full-scale Phase 5 run: 24 conditions x 1,012 IDs, COMET replaced by a deterministic stub.
Checks coverage enforcement, family sizes, Holm, pools/over-editing denominators and table generation."""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src' / 'common'), str(ROOT / 'src' / 'post_editing'), str(ROOT / 'src' / 'evaluation')]
import norris_protocol as P
import run_main_experiments as E
import evaluate_main_experiments as EV

WORDS = 'the cat sat on a mat while rain fell over 12 green hills near Manila'.split()


def build(root):
    rng = random.Random(0)
    freeze = root / 'freeze.json'
    P.atomic_json(freeze, dict(freeze_declared=True, protocol=dict(fingerprint=P.protocol_fingerprint())))
    jd = root / 'outputs/phase4/main_prepared/main_test'
    jobs, gold = [], []
    for src, tgt in P.DIRECTIONS:
        d = f'{src}->{tgt}'
        for sid in range(1, 1013):
            s = ' '.join(rng.choice(WORDS) for _ in range(rng.randint(5, 14))) + '.'
            if sid % 9 == 0:
                s += ' Then it stopped.'
            draft, ref = 'D ' + s, 'R ' + s
            gold.append(dict(direction=d, sentence_id=sid, source_text=s, reference_text=ref, baseline_translation=draft,
                             unsplit_translation=draft if sid % 9 else 'U ' + s, input_segment_count=2 if sid % 9 == 0 else 1))
            q = dict(partition='devtest', sentence_id=sid, src=src, tgt=tgt, source_text=s, draft=draft)
            for st in P.STRATEGIES:
                ex = dict(partition='dev', sentence_id=5, src=src, tgt=tgt, source_text='x', draft='y', reference_text='z') if st == 'knn-oneshot' else None
                j = dict(job_key=f'{d}/{st}/{sid}', partition='devtest', direction=d, sentence_id=sid, strategy=st,
                         query=q, example=ex, demonstration_id=5 if ex else None,
                         messages=P.build_frozen_messages(q, st, ex), schema=P.schema_for(st))
                j['job_sha256'] = P.digest(j)
                jobs.append(j)
    P.write_jsonl(jd / 'jobs.jsonl', jobs)
    P.write_jsonl(jd / 'gold_devtest.jsonl', gold)
    P.atomic_json(jd / 'prepared_manifest.json', dict(partition='devtest', protocol_fingerprint=P.protocol_fingerprint(),
                  planned_jobs=len(jobs), items_per_condition=1012, smoke_ids=[1, 9], freeze_sha256=P.file_sha256(freeze),
                  file_sha256={'jobs.jsonl': P.file_sha256(jd / 'jobs.jsonl')}))
    P.atomic_json(root / 'outputs/phase4/main_prepared_latest.json', dict(jobs_dir=str(jd)))
    _, man, jobs = E.load_jobs(jd)
    for m in P.MODELS:
        spec = dict(model=m, test=True)
        sha = P.digest(spec)
        rd = jd / 'runs' / m / sha[:16]
        P.atomic_json(rd / 'run_spec.json', spec)
        P.atomic_json(jd / f'{m}_latest_run.json', dict(run_dir=str(rd), run_sha256=sha))
        by = {}
        for j in jobs:
            r = E.base_record(j, sha, m, P.MODELS[m], 'rev')
            k = rng.random()
            if j['strategy'] == 'reason-then-edit':
                raw = '{"diagnosis": "ok", "edited_translation": "%s"}' % (j['query']['draft'] + ' fixed') if k > .1 else 'bad'
            else:
                raw = '{"edited_translation": "%s"}' % (j['query']['draft'] if k < .5 else j['query']['draft'] + ' fixed')
            r.update(raw_completion=raw, finish_reason='stop', prompt_token_count=500, completion_token_count=20,
                     retry_count=0, transport_state='recorded', latency_definition='test', request_latency_ms=1.0,
                     **P.extract_response(raw, j['strategy'], j['query']['draft'], 'stop'))
            E.finalize_record(r)
            by.setdefault((j['strategy'], j['direction']), []).append(r)
        for (st, d), recs in by.items():
            P.write_jsonl(jd / 'generations' / f'{m}_{st}_{P.SHORT[d]}.jsonl', recs)
    return freeze


def fake_comet(triplets, cache_dir, env):
    out = {}
    for src, mt, ref in triplets:
        h = int(P.digest([src, ref])[:8], 16) / 16 ** 8
        base = .72 + .25 * h
        bonus = .015 if mt.endswith('fixed') else (-.03 if mt.startswith('U ') else 0)
        out[(src, mt, ref)] = min(.99, base + bonus * (1 if 'cat' in src else -0.5))
    return out, 'stub'


def test_synthetic():
    root = Path(tempfile.mkdtemp())
    freeze = build(root)
    EV.comet_scores = fake_comet
    EV.version = lambda name: 'test'  # GPU stack absent in CI sandbox
    sys.argv = ['x', '--root', str(root), '--freeze', str(freeze), '--repo', str(root / 'repo')]
    EV.main()
    res = P.read_json(next((root / 'outputs/phase5').glob('eval_*/main_results.json')))
    assert len(res['F1_primary']) == 24 and len(res['F2_strategy']) == 24 and len(res['conditions']) == 24
    assert all(0 < r['p_holm'] <= 1 and r['p_holm'] >= r['p_raw'] for r in res['F1_primary'] + res['F2_strategy'])
    for c in res['conditions'].values():
        assert c['n'] == 1012 and c['improved'] + c['within_band'] + c['harmed'] == 1012
        assert c['overedit']['0.02']['denominator'] == c['protect_n']
        assert c['protect_n'] + c['middle_pool_n'] + c['improve_pool_n'] == 1012
    rte = [c for k, c in res['conditions'].items() if k.endswith('reason-then-edit')]
    assert all(c['fallback'] > 0 for c in rte)
    for f in ['main_results_matrix.tex', 'overediting_table.tex', 'strategy_contrasts.tex', 'results_macros.tex']:
        assert (root / 'repo/paper/generated' / f).exists()
    print('tables at', root / 'repo/paper/generated')
    return root


if __name__ == '__main__':
    r = test_synthetic()
    print('PASS test_synthetic', r)
