"""Offline end-to-end test of the Phase 4 GPT path with a mock HTTP transport (no key, no network).

Exercises: preparation checks, first-job access check, structured payload, transient 429 retry,
invalid content -> baseline fallback, transport uncertainty -> halt, refusal to repeat without
operator release, recorded release, resume with no duplicate calls, condition assembly,
corrupted-record detection.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import httpx
import openai

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src' / 'common'), str(ROOT / 'src' / 'post_editing')]
import norris_protocol as P
import run_main_experiments as E

CALLS = []
PLAN = {}


def handler(request):
    body = json.loads(request.content)
    user = json.loads(body['messages'][-1]['content'])
    key = (user['source'], body['response_format']['json_schema']['name'])
    CALLS.append(key)
    action = PLAN.get(key, 'ok')
    assert body['model'] == 'gpt-4o-mini-2024-07-18' and body['temperature'] == 0 and body['seed'] == 42
    assert body['response_format']['json_schema']['strict'] is True
    if action == 'rate_once':
        PLAN[key] = 'ok'
        return httpx.Response(429, headers={'retry-after': '0'}, json={'error': {'type': 'requests', 'code': 'rate_limit_exceeded', 'message': 'x'}})
    if action == 'drop':
        raise httpx.ConnectError('simulated network loss')
    if body['response_format']['json_schema']['name'] == 'norris_reason_then_edit':
        content = json.dumps({'diagnosis': 'No source-supported correction needed.', 'edited_translation': user['draft'] + ' (e)'})
    else:
        content = json.dumps({'edited_translation': user['draft'] + ' (e)'})
    if action == 'invalid':
        content = '{"edited_translation": ""}'
    return httpx.Response(200, headers={'x-request-id': 'req_test'}, json={
        'id': 'chatcmpl-x', 'object': 'chat.completion', 'created': 1, 'model': 'gpt-4o-mini-2024-07-18',
        'system_fingerprint': 'fp_test', 'choices': [{'index': 0, 'finish_reason': 'stop',
        'message': {'role': 'assistant', 'content': content, 'refusal': None}}],
        'usage': {'prompt_tokens': 500, 'completion_tokens': 30, 'total_tokens': 530}})


_Orig = openai.AsyncOpenAI
openai.AsyncOpenAI = lambda **kw: _Orig(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **kw)


def make_prepared(d):
    jobs = []
    for src, tgt in P.DIRECTIONS:
        dk = f'{src}->{tgt}'
        for sid in [1, 2]:
            q = dict(partition='devtest', sentence_id=sid, src=src, tgt=tgt, source_text=f'src {dk} {sid}', draft=f'draft {dk} {sid}')
            ex = dict(partition='dev', sentence_id=sid, src=src, tgt=tgt, source_text='demo', draft='demo d', reference_text='demo r')
            for s in P.STRATEGIES:
                e = ex if s == 'knn-oneshot' else None
                j = dict(job_key=f'{dk}/{s}/{sid}', partition='devtest', direction=dk, sentence_id=sid, strategy=s,
                         query=q, example=e, demonstration_id=sid if e else None,
                         messages=P.build_frozen_messages(q, s, e), schema=P.schema_for(s))
                j['job_sha256'] = P.digest(j)
                jobs.append(j)
    P.write_jsonl(d / 'jobs.jsonl', jobs)
    P.atomic_json(d / 'prepared_manifest.json', dict(partition='devtest', protocol_fingerprint=P.protocol_fingerprint(),
                  planned_jobs=len(jobs), items_per_condition=2, smoke_ids=[1], file_sha256={'jobs.jsonl': P.file_sha256(d / 'jobs.jsonl')}))


def run(d, release=False):
    jd, man, jobs = E.load_jobs(d)
    spec = E.run_spec_for('gpt4o-mini', man, 50, 4)
    sha = P.digest(spec)
    rd = jd / 'runs' / 'gpt4o-mini' / sha[:16]
    (rd / 'records').mkdir(parents=True, exist_ok=True)
    (rd / 'attempts').mkdir(exist_ok=True)
    ledger = E.Ledger(d / 'ledger.sqlite')
    sel = E.select_jobs(jobs, man, 'all', 'all', 'full')
    asyncio.run(E.run_gpt(sel, rd, sha, ledger, 50, 4, release))
    return jd, man, jobs, rd, sha, ledger


def test_engine():
    import os
    os.environ['OPENAI_API_KEY'] = 'sk-test-not-real'
    d = Path(tempfile.mkdtemp())
    make_prepared(d)
    PLAN[('src tgl_Latn->eng_Latn 1', 'norris_zero_shot')] = 'rate_once'
    PLAN[('src eng_Latn->spa_Latn 2', 'norris_knn_oneshot')] = 'invalid'
    PLAN[('src spa_Latn->eng_Latn 2', 'norris_reason_then_edit')] = 'drop'
    try:
        run(d)
        raise AssertionError('transport loss must halt')
    except E.FatalRunError as e:
        assert 'uncertain' in str(e).lower() or 'stopped' in str(e).lower()
    try:
        run(d)
        raise AssertionError('must refuse to repeat an uncertain call without release')
    except E.FatalRunError as e:
        assert 'Uncertain GPT request' in str(e)
    PLAN[('src spa_Latn->eng_Latn 2', 'norris_reason_then_edit')] = 'ok'
    n_before = len(CALLS)
    jd, man, jobs, rd, sha, ledger = run(d, release=True)
    new_calls = CALLS[n_before:]
    assert len(new_calls) == len(set(new_calls)), 'completed jobs were re-requested'
    recs = [P.read_json(p) for p in (rd / 'records').glob('*.json')]
    assert len(recs) == 24
    fb = [r for r in recs if r['fallback_used']]
    assert len(fb) == 1 and fb[0]['edited_translation'] == 'draft eng_Latn->spa_Latn 2'
    retried = [r for r in recs if r['job_key'] == 'tgl_Latn->eng_Latn/zero-shot/1'][0]
    assert retried['retry_count'] == 1 and retried['usable']
    rte = [r for r in recs if r['strategy'] == 'reason-then-edit' and r['usable']]
    assert all(r['diagnosis'] for r in rte)
    released = P.read_json(E.marker_path(rd, [j for j in jobs if j['job_key'] == 'spa_Latn->eng_Latn/reason-then-edit/2'][0]))
    assert any(ev.get('event') == 'released_for_retry_by_operator' for ev in released['events'])
    status = E.assemble(jobs, man, rd, sha, 'gpt4o-mini', d / 'generations')
    assert len(status) == 12 and all(v['state'] == 'complete' for v in status.values())
    assert ledger.counts(sha).get('complete') == 24
    # resume: nothing pending, no calls
    n = len(CALLS)
    run(d)
    assert len(CALLS) == n
    # corrupted record detected
    p = next((rd / 'records').glob('*.json'))
    r = P.read_json(p)
    r['edited_translation'] = 'tampered'
    P.atomic_json(p, r)
    try:
        E.assemble(jobs, man, rd, sha, 'gpt4o-mini', d / 'generations')
        raise AssertionError('tampering must be detected')
    except ValueError:
        pass
    # tampered prepared jobs rejected
    lines = (d / 'jobs.jsonl').read_text().splitlines()
    j = json.loads(lines[0]); j['query']['draft'] = 'changed'; lines[0] = json.dumps(j)
    (d / 'jobs.jsonl').write_text('\n'.join(lines) + '\n')
    try:
        E.load_jobs(d)
        raise AssertionError('changed jobs must be rejected')
    except ValueError:
        pass


if __name__ == '__main__':
    test_engine()
    print('PASS test_engine (24 jobs, retry, fallback, uncertain halt, release, resume, assembly, tamper checks)')
