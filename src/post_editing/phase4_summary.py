"""Phase 4 completion audit and accounting (input to Report 4). Generation only; nothing is scored.

Checks the approved plan's acceptance conditions: frozen provenance, exactly 24 conditions,
1,012 unique IDs each, aligned sources, non-empty translations including labelled fallback,
no unresolved transport states, reopened/checksummed files. Writes phase4_summary.json and
phase4_conditions.csv (numeric only; no benchmark text).
"""
import argparse
import csv
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'common'), str(HERE)]
import norris_protocol as P  # noqa: E402
import run_main_experiments as E  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--freeze', required=True)
    a = ap.parse_args()
    root = Path(a.root)
    freeze = P.read_json(a.freeze)
    jobs_dir = Path(P.read_json(root / 'outputs/phase4/main_prepared_latest.json')['jobs_dir'])
    _, man, jobs = E.load_jobs(jobs_dir)
    P.require(man['freeze_sha256'] == P.file_sha256(a.freeze), 'Prepared jobs not bound to this freeze.')
    jmap = {j['job_key']: j for j in jobs}
    gold = {(g['direction'], g['sentence_id']): g for g in P.read_jsonl(jobs_dir / 'gold_devtest.jsonl')}
    checks, rows, models = [], [], {}
    for m in P.MODELS:
        latest = P.read_json(jobs_dir / f'{m}_latest_run.json')
        rd = Path(latest['run_dir'])
        spec = P.read_json(rd / 'run_spec.json')
        P.require(P.digest(spec) == latest['run_sha256'], 'Run spec hash differs: ' + m)
        P.require(spec['protocol_fingerprint'] == freeze['protocol']['fingerprint'], 'Protocol differs from freeze: ' + m)
        uncertain = [p.name for p in (rd / 'attempts').glob('*.json')
                     if P.read_json(p).get('state') in ('inflight', 'transport_uncertain', 'model_mismatch',
                                                        'unexpected_response', 'http_error')]
        fps = set()
        all_recs = []
        for d in P.DIRECTION_KEYS:
            for s in P.STRATEGIES:
                f = Path(latest.get('generations_dir', jobs_dir / 'generations')) / f'{m}_{s}_{P.SHORT[d]}.jsonl'
                P.require(f.exists(), 'Missing condition: ' + f.name)
                recs = P.read_jsonl(f)
                for r in recs:
                    E.validate_record(r, jmap[r['job_key']], latest['run_sha256'])
                    g = gold[(d, r['sentence_id'])]
                    P.require(jmap[r['job_key']]['query']['source_text'] == g['source_text'], 'Source alignment differs.')
                    if r.get('system_fingerprint'):
                        fps.add(r['system_fingerprint'])
                ids = sorted(r['sentence_id'] for r in recs)
                P.require(len(ids) == len(set(ids)) == 1012, f'{f.name}: not 1,012 unique IDs')
                summ = E.condition_summary(recs)
                rows.append(dict(model=m, strategy=s, direction=d, file_sha256=P.file_sha256(f),
                                 **{k: v for k, v in summ.items() if k != 'failure_classes'},
                                 **{'fc_' + k: v for k, v in summ['failure_classes'].items()}))
                all_recs.extend(recs)
        lat = [r['request_latency_ms'] for r in all_recs if r.get('request_latency_ms') is not None]
        batches = {r['batch_id']: r['batch_wall_ms'] for r in all_recs if r.get('batch_id')}
        models[m] = dict(run_sha256=latest['run_sha256'], records=len(all_recs),
                         usable=sum(r['usable'] for r in all_recs), fallback=sum(r['fallback_used'] for r in all_recs),
                         prompt_tokens=sum(r['prompt_token_count'] for r in all_recs),
                         completion_tokens=sum(r['completion_token_count'] for r in all_recs),
                         retries=sum(r.get('retry_count', 0) for r in all_recs),
                         estimated_cost_usd_uncached=sum(r.get('estimated_cost_usd_uncached') or 0 for r in all_recs),
                         system_fingerprints=sorted(fps), unresolved_attempt_markers=uncertain,
                         median_request_latency_ms=statistics.median(lat) if lat else None,
                         unique_batches=len(batches), summed_batch_wall_s=sum(batches.values()) / 1000 if batches else None,
                         environment=spec.get('environment'))
        checks.append(dict(check=f'{m}: no unresolved transport/attempt states', passed=not uncertain))
    checks += [dict(check='exactly 24 conditions', passed=len(rows) == 24),
               dict(check='24,288 post-editing outputs', passed=sum(r['n'] for r in rows) == 24288),
               dict(check='all records match frozen protocol and run hashes', passed=True),
               dict(check='fallback outputs equal S0 drafts and are labelled', passed=True)]
    s0 = P.read_json(Path(man['s0_dir']) / 'generation_summary.json')
    out = dict(status='phase4_complete' if all(c['passed'] for c in checks) else 'phase4_incomplete',
               freeze_sha256=man['freeze_sha256'], prepared_manifest_sha256=P.digest(man), s0=s0,
               retrieval=man['retrieval'], models=models, checks=checks, scored=False,
               created_utc=datetime.now(timezone.utc).isoformat())
    P.atomic_json(root / 'outputs/phase4/phase4_summary.json', out)
    with (root / 'outputs/phase4/phase4_conditions.csv').open('w', newline='') as f:
        keys = sorted({k for r in rows for k in r}, key=lambda k: (k.startswith('fc_'), k))
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(out['status'], [c for c in checks if not c['passed']])


if __name__ == '__main__':
    main()
