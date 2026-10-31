"""Phase 3 revision: prepare dev reason-then-edit jobs under the minimal v3 contract.

Dev only. Same 100 pilot IDs, same queries/drafts, same system instruction, same
engine settings. The only change is the reason-then-edit suffix and schema.
Before writing anything, the frozen builder must reproduce all 1,200 measured
candidate-v2 job messages byte-for-byte (zero-shot, one-shot and v2 reason-then-edit).

  python prepare_rte_v3_dev.py --root /content/drive/MyDrive/norris
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'common'))
sys.path.insert(0, str(HERE))
import norris_protocol as P  # noqa: E402
import baseline_io  # noqa: E402  (measured Phase 3 module; validates dev baseline hashes)

RELIABILITY_GATE = dict(
    rule='Operationally reliable iff, for EACH model, fallbacks <= 20/400 (5.0%) overall AND '
         '<= 10/100 in every direction. Declared before the rerun; operational only, never a '
         'quality criterion. COMET is not used to accept or reject the revised contract.',
    max_fallback_per_model=20, max_fallback_per_direction=10, n_per_model=400, n_per_direction=100,
    single_revision='One contract revision only. No prompt iteration after observing the full rerun. '
                    'If the gate fails, the PI decides: retain as explicit failure condition or remove.')


def find_v2_dir(root):
    hits = []
    for mf in sorted((root / 'outputs/phase3_post_editing').glob('candidate_*/prepared_manifest.json')):
        if P.digest(P.read_json(mf)) == P.V2_PREPARED_MANIFEST_SHA:
            hits.append(mf.parent)
    P.require(len(hits) == 1, f'Expected exactly one measured v2 preparation, found {len(hits)}.')
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--v2-dir', default=None)
    args = ap.parse_args()
    root = Path(args.root)
    v2 = Path(args.v2_dir) if args.v2_dir else find_v2_dir(root)
    manifest = P.read_json(v2 / 'prepared_manifest.json')
    P.require(P.digest(manifest) == P.V2_PREPARED_MANIFEST_SHA, 'Not the measured v2 preparation.')
    for name, expected in manifest['file_sha256'].items():
        P.require(P.file_sha256(v2 / name) == expected, 'v2 prepared file differs: ' + name)
    cfg = manifest['config']
    P.require(cfg['prompt_version'] == P.PLAIN_VERSION, 'Prompt version differs.')
    P.require(cfg['system_base'] == P.SYSTEM_BASE, 'System instruction bytes differ from measured v2.')
    P.require(cfg['plain_suffix'] == P.PLAIN_SUFFIX, 'Plain suffix bytes differ from measured v2.')
    P.require(cfg['reason_suffix'] == P.REASON_SUFFIX_V2_MEASURED, 'v2 reason suffix differs.')
    for s in ['zero-shot', 'knn-oneshot']:
        P.require(cfg['schemas'][s] == P.schema_for(s), 'Plain schema differs from measured v2: ' + s)

    data, _ = baseline_io.load_inputs(root / 'outputs/generations/baselines/phase3_dev_f4a3af94ba1e72fd')
    jobs = P.read_jsonl(v2 / 'jobs.jsonl')
    P.require(len(jobs) == 1200, 'v2 must contain 1,200 jobs.')
    reproduced = 0
    for job in jobs:
        P.require(job['job_sha256'] == P.digest({k: v for k, v in job.items() if k != 'job_sha256'}),
                  'v2 job checksum differs.')
        example = None
        if job['strategy'] == 'knn-oneshot':
            row = {r['sentence_id']: r for r in data[job['direction']]['split']}[job['demonstration_id']]
            example = dict(sentence_id=row['sentence_id'], src=job['query']['src'], tgt=job['query']['tgt'],
                           source_text=row['source_text'], draft=row['nllb_translation'],
                           reference_text=row['reference_text'])
        suffix = P.REASON_SUFFIX_V2_MEASURED if job['strategy'] == 'reason-then-edit' else P.PLAIN_SUFFIX
        rebuilt = P.build_messages_with(job['query'], job['strategy'], example, suffix,
                                        cfg['schemas'][job['strategy']])
        P.require(rebuilt == job['messages'], 'Frozen builder does not reproduce v2 job ' + job['job_key'])
        reproduced += 1

    gold = P.read_jsonl(v2 / 'evaluation_gold.jsonl')
    new_jobs = []
    for job in sorted((j for j in jobs if j['strategy'] == 'reason-then-edit'),
                      key=lambda j: (P.DIRECTION_KEYS.index(j['direction']), j['sentence_id'])):
        query = dict(job['query'], partition='dev')
        new = dict(job_key=job['job_key'], partition='dev', direction=job['direction'],
                   sentence_id=job['sentence_id'], strategy='reason-then-edit', query=query,
                   example=None, demonstration_id=None,
                   messages=P.build_frozen_messages(query, 'reason-then-edit'),
                   schema=P.schema_for('reason-then-edit'), v2_job_sha256=job['job_sha256'])
        new['job_sha256'] = P.digest(new)
        new_jobs.append(new)
    P.require(len(new_jobs) == 400, 'Expected 400 reason-then-edit dev jobs.')
    P.require(all(j['messages'][-1] == old['messages'][-1] for j, old in zip(
        new_jobs, sorted((j for j in jobs if j['strategy'] == 'reason-then-edit'),
                         key=lambda j: (P.DIRECTION_KEYS.index(j['direction']), j['sentence_id'])))),
        'User payload must be unchanged from v2.')

    out = root / 'outputs/phase3_post_editing' / ('rte_v3_' + P.digest([j['job_sha256'] for j in new_jobs])[:16])
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'prepared_manifest.json').exists():  # idempotent: never rewrite a used preparation
        old = P.read_json(out / 'prepared_manifest.json')
        P.require(old['protocol_fingerprint'] == P.protocol_fingerprint() and
                  P.file_sha256(out / 'jobs.jsonl') == old['file_sha256']['jobs.jsonl'],
                  'Existing RTE v3 preparation differs; stop for review.')
        P.atomic_json(root / 'outputs/phase3_post_editing/rte_v3_latest.json', dict(jobs_dir=str(out)))
        print('v2 jobs reproduced byte-for-byte:', reproduced, '/ 1200')
        print('RTE v3 DEV JOBS (existing preparation reused, unchanged):', out)
        return
    P.write_jsonl(out / 'jobs.jsonl', new_jobs)
    P.write_jsonl(out / 'evaluation_gold.jsonl', gold)
    files = {n: P.file_sha256(out / n) for n in ['jobs.jsonl', 'evaluation_gold.jsonl']}
    m = dict(stage='phase3_rte_v3_dev_revalidation', partition='dev', protocol_id=P.PROTOCOL_ID,
             protocol_fingerprint=P.protocol_fingerprint(), rte_version=P.RTE_VERSION,
             planned_jobs=400, items_per_condition=100, models=list(P.MODELS),
             smoke_ids=manifest['smoke_ids'], pilot_ids_sha256=cfg['pilot_ids_sha256'],
             v2_prepared_manifest_sha256=P.V2_PREPARED_MANIFEST_SHA, v2_prepared_dir=str(v2),
             v2_jobs_reproduced_byte_for_byte=reproduced, reliability_gate=RELIABILITY_GATE,
             unchanged=['task', 'dev partition', '100 pilot IDs', 'queries and NLLB drafts',
                        'system instruction bytes', 'user payload bytes', 'model snapshots/revisions',
                        'decoding and engine settings', 'fallback policy (no repair, no selective retry)'],
             changed=['reason-then-edit suffix', 'reason-then-edit schema (diagnosis:str, edited_translation:str)',
                      'reason-then-edit validators reduced to JSON/no-duplicate-keys/schema/key order/'
                      'non-empty fields/normal stop'],
             devtest_opened=False, created_utc=datetime.now(timezone.utc).isoformat(), file_sha256=files)
    P.atomic_json(out / 'prepared_manifest.json', m)
    P.atomic_json(root / 'outputs/phase3_post_editing/rte_v3_latest.json', dict(jobs_dir=str(out)))
    print('v2 jobs reproduced byte-for-byte:', reproduced, '/ 1200')
    print('RTE v3 DEV JOBS:', out, '| 400 jobs per model | smoke IDs', manifest['smoke_ids'])


if __name__ == '__main__':
    main()
