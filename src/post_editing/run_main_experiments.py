"""Norris Phase 4 execution engine (24 post-editing conditions on FLORES+ devtest).

The same engine runs the dev reason-then-edit revalidation (Phase 3 revision),
so the backend, schema handling, resumption and failure policy are validated on
dev before the protocol freeze.

Durable truth = one immutable JSON record per job on Drive. SQLite (local disk,
backed up to Drive) is the job ledger/index and is reconciled from the records on
every start. Invalid model content is never repaired or selectively regenerated;
it falls back to the unchanged baseline draft and stays in the population.

Usage (Colab):
  python run_main_experiments.py --jobs-dir DIR --model gpt4o-mini --stage smoke
  python run_main_experiments.py --jobs-dir DIR --model llama3-8b --strategy all --direction all --stage full
"""
import argparse
import asyncio
import hashlib
import logging
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version, distributions
from pathlib import Path

os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('VLLM_WORKER_MULTIPROC_METHOD', 'spawn')
os.environ.setdefault('VLLM_NO_USAGE_STATS', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
import norris_protocol as P  # noqa: E402

LLAMA_SAMPLING = dict(temperature=0.0, top_p=1.0, top_k=-1, max_tokens=1024, seed=42,
                      repetition_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0,
                      ignore_eos=False, stop_token_ids=[128009])
LLAMA_ENGINE = dict(dtype='bfloat16', tensor_parallel_size=1, max_model_len=8192,
                    gpu_memory_utilization=.70, max_num_seqs=16, enforce_eager=True,
                    enable_prefix_caching=True, seed=42, generation_config='vllm')
LLAMA_BATCH = 16
GPT_PAYLOAD = dict(temperature=0, top_p=1, seed=42, max_tokens=1024, store=False)
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}
NON_RETRY_CODES = {'insufficient_quota', 'credit_balance_exhausted',
                   'organization_spend_limit_exceeded', 'project_spend_limit_exceeded'}
GPT_PRICE_PER_M = dict(input=.15, output=.60)  # recorded uncached rate; not an invoice
SHORT_TO_KEY = {v: k for k, v in P.SHORT.items()}
LOG = logging.getLogger('phase4')


class FatalRunError(RuntimeError):
    pass


# --------------------------------------------------------------------------- jobs
def load_jobs(jobs_dir):
    jobs_dir = Path(jobs_dir)
    manifest = P.read_json(jobs_dir / 'prepared_manifest.json')
    for name, expected in manifest['file_sha256'].items():
        P.require(P.file_sha256(jobs_dir / name) == expected, 'Prepared file checksum differs: ' + name)
    P.require(manifest['protocol_fingerprint'] == P.protocol_fingerprint(),
              'Prepared jobs were built with a different protocol than this code.')
    jobs = P.read_jsonl(jobs_dir / 'jobs.jsonl')
    P.require(len(jobs) == manifest['planned_jobs'] and len({j['job_key'] for j in jobs}) == len(jobs),
              'Planned job count or uniqueness differs.')
    for job in jobs:
        P.require(job['job_sha256'] == P.digest({k: v for k, v in job.items() if k != 'job_sha256'}),
                  'Job checksum differs: ' + job['job_key'])
        P.require(job['messages'] == P.build_frozen_messages(
            job['query'], job['strategy'], job.get('example')), 'Job messages differ from frozen builder.')
        P.require(job['schema'] == P.schema_for(job['strategy']), 'Job schema differs.')
        P.require(job['partition'] == manifest['partition'], 'Mixed partitions.')
    return jobs_dir, manifest, jobs


def select_jobs(jobs, manifest, strategy, direction, stage):
    ids = set(manifest['smoke_ids']) if stage == 'smoke' else None
    out = [j for j in jobs
           if (strategy == 'all' or j['strategy'] == strategy)
           and (direction == 'all' or j['direction'] == SHORT_TO_KEY[direction])
           and (ids is None or j['sentence_id'] in ids)]
    P.require(bool(out), 'No jobs selected.')
    return sorted(out, key=lambda j: (P.STRATEGIES.index(j['strategy']),
                                     P.DIRECTION_KEYS.index(j['direction']), j['sentence_id']))


# --------------------------------------------------------------------------- ledger
class Ledger:
    """SQLite job index. Rebuilt from durable records each start; never the sole truth."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), isolation_level=None, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs(
            run_sha TEXT, job_key TEXT, model TEXT, strategy TEXT, direction TEXT,
            sentence_id INTEGER, state TEXT, attempts INTEGER DEFAULT 0,
            record_sha TEXT, updated_utc TEXT, PRIMARY KEY(run_sha, job_key))''')

    def upsert(self, run_sha, job, model, state, attempts=0, record_sha=None):
        self.db.execute('''INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_sha, job_key) DO UPDATE SET state=excluded.state,
            attempts=excluded.attempts, record_sha=excluded.record_sha, updated_utc=excluded.updated_utc''',
            (run_sha, job['job_key'], model, job['strategy'], job['direction'], job['sentence_id'],
             state, attempts, record_sha, datetime.now(timezone.utc).isoformat()))

    def counts(self, run_sha):
        return dict(self.db.execute('SELECT state, COUNT(*) FROM jobs WHERE run_sha=? GROUP BY state',
                                    (run_sha,)).fetchall())

    def backup_to(self, target):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        dest = sqlite3.connect(str(target))
        self.db.backup(dest)
        dest.close()


# --------------------------------------------------------------------------- records
def record_path(run_dir, job):
    return run_dir / 'records' / (P.digest(job['job_key']) + '.json')


def marker_path(run_dir, job):
    return run_dir / 'attempts' / (P.digest(job['job_key']) + '.json')


def validate_record(record, job, run_sha):
    P.require(record['run_sha256'] == run_sha, 'Saved run configuration differs: ' + job['job_key'])
    P.require(record['job_sha256'] == job['job_sha256'], 'Saved job differs: ' + job['job_key'])
    P.require(record['content_sha256'] == P.digest({k: v for k, v in record.items()
                                                    if k != 'content_sha256'}), 'Record checksum differs.')
    again = P.extract_response(record['raw_completion'], job['strategy'], job['query']['draft'],
                               record['finish_reason'])
    for key in ['json_parse_success', 'schema_valid', 'usable', 'edited_translation', 'fallback_used']:
        P.require(again[key] == record[key], 'Stored extraction differs: ' + job['job_key'])
    P.require(isinstance(record['edited_translation'], str) and record['edited_translation'].strip(),
              'Empty final translation.')
    if record['fallback_used']:
        P.require(record['edited_translation'] == job['query']['draft'], 'Fallback differs from baseline.')


def finalize_record(record):
    record['content_sha256'] = P.digest(record)
    return record


def base_record(job, run_sha, model_key, model_id, revision):
    return dict(run_sha256=run_sha, job_sha256=job['job_sha256'], job_key=job['job_key'],
                partition=job['partition'], direction=job['direction'], strategy=job['strategy'],
                sentence_id=job['sentence_id'], demonstration_id=job.get('demonstration_id'),
                model=model_key, model_id=model_id, model_revision=revision, seed=42,
                protocol_fingerprint=P.protocol_fingerprint(), messages=job['messages'])


# --------------------------------------------------------------------------- llama backend
def run_llama(jobs, run_dir, run_sha, ledger, hf_token):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    P.require(version('vllm') == '0.11.2', 'This engine is pinned to vLLM 0.11.2.')
    rev = P.REVISIONS['llama']
    tok = AutoTokenizer.from_pretrained(P.MODELS['llama3-8b'], revision=rev, token=hf_token)
    eot = tok.convert_tokens_to_ids('<|eot_id|>')
    P.require(eot is not None and eot != tok.unk_token_id, 'Llama end-of-turn token missing.')
    stop_ids = sorted({tok.eos_token_id, eot})
    P.require(stop_ids == LLAMA_SAMPLING['stop_token_ids'],
              'Llama stop tokens differ from the measured pilot ([128009]).')
    pending = [j for j in jobs if not record_path(run_dir, j).exists()]
    LOG.info('llama: %d pending of %d selected', len(pending), len(jobs))
    if not pending:
        return 0.0
    P.require(torch.cuda.is_available(), 'An A100 GPU runtime is required for Llama.')
    start = time.perf_counter()
    llm = LLM(model=P.MODELS['llama3-8b'], tokenizer=P.MODELS['llama3-8b'], revision=rev,
              tokenizer_revision=rev, trust_remote_code=False, **LLAMA_ENGINE)
    init_s = time.perf_counter() - start
    for strategy in P.STRATEGIES:
        todo = [j for j in pending if j['strategy'] == strategy]
        params = SamplingParams(**LLAMA_SAMPLING,
                                structured_outputs=StructuredOutputsParams(json=P.schema_for(strategy)))
        for offset in range(0, len(todo), LLAMA_BATCH):
            chunk = todo[offset:offset + LLAMA_BATCH]
            prompts, ids_list = [], []
            for job in chunk:
                prompt = tok.apply_chat_template(job['messages'], tokenize=False, add_generation_prompt=True)
                ids = tok.apply_chat_template(job['messages'], tokenize=True, add_generation_prompt=True)
                P.require(ids == tok(prompt, add_special_tokens=False).input_ids,
                          'Chat template/tokenization mismatch: ' + job['job_key'])
                P.require(len(ids) + LLAMA_SAMPLING['max_tokens'] <= LLAMA_ENGINE['max_model_len'],
                          'Context overflow (review before generation): ' + job['job_key'])
                prompts.append(prompt)
                ids_list.append(ids)
            for job in chunk:
                ledger.upsert(run_sha, job, 'llama3-8b', 'inflight')
            t0 = time.perf_counter()
            outputs = llm.generate([dict(prompt_token_ids=i) for i in ids_list],
                                   sampling_params=params, use_tqdm=False)
            wall_ms = (time.perf_counter() - t0) * 1000
            P.require(len(outputs) == len(chunk), 'Unexpected vLLM batch size.')
            batch_id = P.digest(dict(keys=[j['job_key'] for j in chunk],
                                     t=datetime.now(timezone.utc).isoformat()))[:20]
            for job, prompt, ids, output in zip(chunk, prompts, ids_list, outputs):
                P.require(len(output.outputs) == 1, 'Expected one completion.')
                comp = output.outputs[0]
                rec = base_record(job, run_sha, 'llama3-8b', P.MODELS['llama3-8b'], rev)
                rec.update(rendered_prompt=prompt, raw_completion=comp.text,
                           finish_reason=comp.finish_reason, stop_reason=getattr(comp, 'stop_reason', None),
                           prompt_token_count=len(ids), completion_token_count=len(comp.token_ids),
                           batch_id=batch_id, generation_batch_size=len(chunk), batch_wall_ms=wall_ms,
                           batch_amortized_ms=wall_ms / len(chunk), request_latency_ms=None,
                           latency_definition='batch-amortized generation time; model initialization excluded',
                           retry_count=0, transport_state='recorded',
                           created_utc=datetime.now(timezone.utc).isoformat(),
                           **P.extract_response(comp.text, strategy, job['query']['draft'], comp.finish_reason))
                finalize_record(rec)
                validate_record(rec, job, run_sha)
                P.atomic_json(record_path(run_dir, job), rec)
                ledger.upsert(run_sha, job, 'llama3-8b', 'complete', 1, rec['content_sha256'])
            LOG.info('llama %s: %d/%d saved', strategy, min(offset + LLAMA_BATCH, len(todo)), len(todo))
    return init_s


# --------------------------------------------------------------------------- GPT backend
class AsyncRateGate:
    def __init__(self, rps):
        self.interval = 1.0 / rps
        self.next_at = 0.0
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            slot = max(time.monotonic(), self.next_at)
            self.next_at = slot + self.interval
        await asyncio.sleep(max(0.0, slot - time.monotonic()))


def gpt_cost(usage):
    return (usage.get('prompt_tokens', 0) * GPT_PRICE_PER_M['input'] +
            usage.get('completion_tokens', 0) * GPT_PRICE_PER_M['output']) / 1e6


async def run_gpt(jobs, run_dir, run_sha, ledger, rps, concurrency, release_uncertain):
    import openai
    from openai import AsyncOpenAI
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    P.require(bool(key), 'OPENAI_API_KEY absent. Enable the Colab Secret; never paste it into code.')
    model_id = P.MODELS['gpt4o-mini']
    todo = []
    for job in jobs:
        if record_path(run_dir, job).exists():
            continue
        mp = marker_path(run_dir, job)
        if mp.exists():
            m = P.read_json(mp)
            if m.get('state') in ('inflight', 'transport_uncertain', 'model_mismatch', 'unexpected_response'):
                if not release_uncertain:
                    raise FatalRunError('Uncertain GPT request for ' + job['job_key'] + ' (' + m['state'] +
                                        '). Review the attempt marker; rerun with --release-uncertain '
                                        'only after recording the decision (possible duplicate charge).')
                m.setdefault('events', []).append(dict(event='released_for_retry_by_operator',
                                                       prior_state=m['state'],
                                                       utc=datetime.now(timezone.utc).isoformat()))
                m['state'] = 'released'
                P.atomic_json(mp, m)
        todo.append(job)
    LOG.info('gpt: %d pending of %d selected', len(todo), len(jobs))
    if not todo:
        return
    client = AsyncOpenAI(api_key=key, max_retries=0, timeout=180.0)
    gate, sem, halt = AsyncRateGate(rps), asyncio.Semaphore(concurrency), asyncio.Event()

    async def one(job):
        mp = marker_path(run_dir, job)
        prior = P.read_json(mp) if mp.exists() else {}
        events = prior.get('events', [])
        first = prior.get('attempt', -1) + 1 if prior.get('state') == 'http_error' else 0
        payload = dict(model=model_id, messages=job['messages'], **GPT_PAYLOAD,
                       response_format=dict(type='json_schema', json_schema=dict(
                           name='norris_' + job['strategy'].replace('-', '_'), strict=True,
                           schema=job['schema'])))
        async with sem:
            for attempt in range(first, 6):
                if halt.is_set():
                    raise FatalRunError('Stopped after another request failed; resume later.')
                await gate.wait()
                base = dict(job_key=job['job_key'], job_sha256=job['job_sha256'], run_sha256=run_sha,
                            attempt=attempt, created_utc=datetime.now(timezone.utc).isoformat())
                P.atomic_json(mp, dict(base, state='inflight', events=events))
                ledger.upsert(run_sha, job, 'gpt4o-mini', 'inflight', attempt + 1)
                t0 = time.perf_counter()
                try:
                    raw = await client.chat.completions.with_raw_response.create(**payload)
                    completion = raw.parse()
                    request_id = raw.headers.get('x-request-id')
                except openai.APIStatusError as e:
                    body = e.body if isinstance(e.body, dict) else {}
                    err = body.get('error', body) if isinstance(body, dict) else {}
                    code = err.get('code') if isinstance(err, dict) else None
                    etype = err.get('type') if isinstance(err, dict) else None
                    events.append(dict(http_status=e.status_code, error_type=etype, error_code=code,
                                       attempt=attempt))  # never log messages (may quote keys)
                    P.atomic_json(mp, dict(base, state='http_error', events=events))
                    ledger.upsert(run_sha, job, 'gpt4o-mini', 'http_error', attempt + 1)
                    if e.status_code in TRANSIENT_HTTP and code not in NON_RETRY_CODES and attempt < 5:
                        try:
                            delay = float(e.response.headers.get('retry-after', 0))
                        except (TypeError, ValueError):
                            delay = 0.0
                        await asyncio.sleep(min(60.0, max(delay, 2 ** attempt + random.random())))
                        continue
                    halt.set()
                    raise FatalRunError(f'GPT stopped: HTTP {e.status_code} type={etype} code={code}. '
                                        'Check limits/billing; no model substitution made.')
                except (openai.APITimeoutError, openai.APIConnectionError) as e:
                    P.atomic_json(mp, dict(base, state='transport_uncertain',
                                           error_class=type(e).__name__, events=events))
                    ledger.upsert(run_sha, job, 'gpt4o-mini', 'transport_uncertain', attempt + 1)
                    halt.set()
                    raise FatalRunError('Transport result uncertain for ' + job['job_key'] +
                                        '; review before any repeat (possible charge).')
                elapsed = (time.perf_counter() - t0) * 1000
                response = completion.model_dump(mode='json')
                if response.get('model') != model_id:
                    P.atomic_json(mp, dict(base, state='model_mismatch', returned_model=response.get('model'),
                                           request_id=request_id, events=events))
                    halt.set()
                    raise FatalRunError('API returned a different model identifier; protocol review.')
                choices = response.get('choices') or []
                if len(choices) != 1:
                    P.atomic_json(mp, dict(base, state='unexpected_response', response=response,
                                           request_id=request_id, events=events))
                    halt.set()
                    raise FatalRunError('Unexpected API response shape; raw response retained.')
                choice = choices[0]
                message = choice.get('message') or {}
                text = message.get('content') or ''
                usage = response.get('usage') or {}
                rec = base_record(job, run_sha, 'gpt4o-mini', model_id, model_id)
                rec.update(returned_model=response['model'], system_fingerprint=response.get('system_fingerprint'),
                           request_id=request_id, response_id=response.get('id'),
                           response_created=response.get('created'), raw_completion=text,
                           raw_response=response, refusal=message.get('refusal'),
                           finish_reason=choice.get('finish_reason'),
                           prompt_token_count=usage.get('prompt_tokens', 0),
                           completion_token_count=usage.get('completion_tokens', 0), usage=usage,
                           estimated_cost_usd_uncached=gpt_cost(usage), request_latency_ms=elapsed,
                           batch_amortized_ms=None, latency_definition='HTTP request wall time',
                           retry_count=attempt, transport_state='recorded',
                           created_utc=datetime.now(timezone.utc).isoformat(),
                           **P.extract_response(text, job['strategy'], job['query']['draft'],
                                                choice.get('finish_reason')))
                finalize_record(rec)
                validate_record(rec, job, run_sha)
                P.atomic_json(record_path(run_dir, job), rec)
                P.atomic_json(mp, dict(base, state='recorded', record_sha256=rec['content_sha256'],
                                       request_id=request_id, events=events))
                ledger.upsert(run_sha, job, 'gpt4o-mini', 'complete', attempt + 1, rec['content_sha256'])
                return
            halt.set()
            raise FatalRunError('Retries exhausted for ' + job['job_key'])

    await one(todo[0])  # access/schema check before concurrency
    LOG.info('gpt: exact snapshot responded; first job recorded')
    tasks = [asyncio.create_task(one(j)) for j in todo[1:]]
    done = 1
    try:
        for fut in asyncio.as_completed(tasks):
            await fut
            done += 1
            if done % 100 == 0:
                LOG.info('gpt saved %d/%d', done, len(todo))
    except Exception:
        halt.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        await client.close()


# --------------------------------------------------------------------------- run spec / outputs
def run_spec_for(model, manifest, rps, concurrency):
    common = dict(prepared_manifest_sha256=P.digest(manifest), partition=manifest['partition'],
                  protocol_fingerprint=P.protocol_fingerprint(), protocol_id=P.PROTOCOL_ID,
                  engine_sha256=P.file_sha256(__file__),
                  protocol_module_sha256=P.file_sha256(Path(P.__file__)),
                  invalid_output_policy='Retain raw output; unchanged baseline draft; no repair or selective retry.',
                  translation_normalization='Trim outer whitespace only after schema validation.')
    if model == 'llama3-8b':
        return dict(common, model=P.MODELS[model], revision=P.REVISIONS['llama'],
                    tokenizer_revision=P.REVISIONS['llama'], sampling=LLAMA_SAMPLING,
                    engine_settings=LLAMA_ENGINE, batch_size=LLAMA_BATCH,
                    environment={k: version(k) for k in ['vllm', 'torch', 'transformers', 'pydantic']})
    return dict(common, model=P.MODELS[model], endpoint='chat.completions (AsyncOpenAI)',
                payload=GPT_PAYLOAD, structured_output='json_schema strict',
                client=dict(openai=version('openai'), max_retries=0, timeout_s=180),
                retry_policy='Transient HTTP 408/409/429/5xx only, 5 retries, bounded exponential backoff; '
                             'timeouts/connection errors halt as transport-uncertain.',
                rate=dict(requests_per_second=rps, concurrency=concurrency),
                environment={k: version(k) for k in ['openai', 'pydantic']})


def condition_summary(records):
    classes = {}
    for r in records:
        c = P.failure_class(r)
        classes[c] = classes.get(c, 0) + 1
    lat = sorted(x for x in (r.get('request_latency_ms') or r.get('batch_amortized_ms') for r in records)
                 if x is not None)
    return dict(n=len(records), json_parse_success=sum(r['json_parse_success'] for r in records),
                schema_valid=sum(r['schema_valid'] for r in records), usable=sum(r['usable'] for r in records),
                fallback=sum(r['fallback_used'] for r in records), failure_classes=classes,
                prompt_tokens=sum(r['prompt_token_count'] for r in records),
                completion_tokens=sum(r['completion_token_count'] for r in records),
                retries=sum(r.get('retry_count', 0) for r in records),
                estimated_cost_usd_uncached=sum(r.get('estimated_cost_usd_uncached', 0) or 0 for r in records),
                median_latency_ms=lat[len(lat) // 2] if lat else None,
                latency_definition=records[0]['latency_definition'] if records else None)


def assemble(jobs_all, manifest, run_dir, run_sha, model, generations_dir):
    """Write every complete condition file; report incomplete ones. Never writes partial conditions."""
    by_cond = {}
    for j in jobs_all:
        by_cond.setdefault((j['strategy'], j['direction']), []).append(j)
    status = {}
    for (strategy, direction), cjobs in sorted(by_cond.items()):
        expected = manifest['items_per_condition']
        P.require(len(cjobs) == expected, 'Prepared condition size differs.')
        name = f'{model}_{strategy}_{P.SHORT[direction]}'
        if not all(record_path(run_dir, j).exists() for j in cjobs):
            status[name] = dict(state='incomplete', complete=sum(record_path(run_dir, j).exists() for j in cjobs),
                                expected=expected)
            continue
        recs = []
        for j in sorted(cjobs, key=lambda x: x['sentence_id']):
            r = P.read_json(record_path(run_dir, j))
            validate_record(r, j, run_sha)
            recs.append(r)
        ids = [r['sentence_id'] for r in recs]
        P.require(len(set(ids)) == expected == len(ids), 'Duplicate or missing IDs in ' + name)
        path = Path(generations_dir) / (name + '.jsonl')
        P.write_jsonl(path, recs)
        back = P.read_jsonl(path)  # reopen and validate before marking complete
        P.require([r['content_sha256'] for r in back] == [r['content_sha256'] for r in recs], 'Reopen differs.')
        status[name] = dict(state='complete', file=str(path), sha256=P.file_sha256(path),
                            **condition_summary(recs))
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs-dir', required=True)
    ap.add_argument('--model', choices=['llama3-8b', 'gpt4o-mini'], required=True)
    ap.add_argument('--strategy', choices=['all'] + P.STRATEGIES, default='all')
    ap.add_argument('--direction', choices=['all'] + list(P.SHORT.values()), default='all')
    ap.add_argument('--stage', choices=['smoke', 'full'], default='smoke')
    ap.add_argument('--generations-dir', default=None, help='default: <jobs-dir>/generations')
    ap.add_argument('--ledger', default='/content/norris_ledger.sqlite')
    ap.add_argument('--log', default=None)
    ap.add_argument('--gpt-rps', type=float, default=4.0)
    ap.add_argument('--gpt-concurrency', type=int, default=4)
    ap.add_argument('--max-estimated-usd', type=float, default=10.0)
    ap.add_argument('--release-uncertain', action='store_true')
    args = ap.parse_args()
    P.require(args.gpt_rps <= 10, 'Roadmap ceiling is 10 requests/second.')

    jobs_dir, manifest, jobs_all = load_jobs(args.jobs_dir)
    log_path = Path(args.log or (jobs_dir / 'logs' / 'phase4_execution.log'))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)])
    spec = run_spec_for(args.model, manifest, args.gpt_rps, args.gpt_concurrency)
    run_sha = P.digest(spec)
    run_dir = jobs_dir / 'runs' / args.model / run_sha[:16]
    (run_dir / 'records').mkdir(parents=True, exist_ok=True)
    (run_dir / 'attempts').mkdir(exist_ok=True)
    if (run_dir / 'run_spec.json').exists():
        P.require(P.read_json(run_dir / 'run_spec.json') == spec, 'Run spec on disk differs.')
    else:
        P.atomic_json(run_dir / 'run_spec.json', spec)
        freeze = sorted(f"{d.metadata['Name']}=={d.version}" for d in distributions() if d.metadata.get('Name'))
        (run_dir / 'requirements_resolved.txt').write_text('\n'.join(freeze) + '\n')
    selected = select_jobs(jobs_all, manifest, args.strategy, args.direction, args.stage)
    LOG.info('run %s | model=%s partition=%s stage=%s selected=%d', run_sha[:16], args.model,
             manifest['partition'], args.stage, len(selected))

    ledger = Ledger(args.ledger)
    for job in selected:  # reconcile ledger from durable records
        rp = record_path(run_dir, job)
        if rp.exists():
            rec = P.read_json(rp)
            validate_record(rec, job, run_sha)
            ledger.upsert(run_sha, job, args.model, 'complete', rec.get('retry_count', 0) + 1, rec['content_sha256'])
        else:
            ledger.upsert(run_sha, job, args.model, 'pending')
    if args.model == 'gpt4o-mini':
        reserve = sum((len(P.canonical(j['messages'])) / 3 + 1024) * GPT_PRICE_PER_M['input'] / 1e6 +
                      1024 * GPT_PRICE_PER_M['output'] / 1e6
                      for j in selected if not record_path(run_dir, j).exists())
        P.require(reserve <= args.max_estimated_usd,
                  f'Conservative estimate ${reserve:.2f} exceeds --max-estimated-usd.')
        LOG.info('gpt conservative preflight estimate $%.2f (account limits remain authoritative)', reserve)
    init_s = 0.0
    try:
        if args.model == 'llama3-8b':
            init_s = run_llama(selected, run_dir, run_sha, ledger, os.environ.get('HF_TOKEN'))
        else:
            asyncio.run(run_gpt(selected, run_dir, run_sha, ledger, args.gpt_rps,
                                args.gpt_concurrency, args.release_uncertain))
    finally:
        ledger.backup_to(run_dir / 'ledger_backup.sqlite')
        LOG.info('ledger states: %s', ledger.counts(run_sha))
    gen_dir = Path(args.generations_dir or (jobs_dir / 'generations'))
    status = assemble(jobs_all, manifest, run_dir, run_sha, args.model, gen_dir)
    summary = dict(model=args.model, run_sha256=run_sha, partition=manifest['partition'],
                   stage=args.stage, model_initialization_seconds_this_invocation=init_s,
                   conditions=status, ledger_states=ledger.counts(run_sha),
                   all_conditions_complete=all(v['state'] == 'complete' for v in status.values()),
                   created_utc=datetime.now(timezone.utc).isoformat())
    P.atomic_json(run_dir / 'run_summary.json', summary)
    P.atomic_json(jobs_dir / f'{args.model}_latest_run.json', dict(run_dir=str(run_dir), run_sha256=run_sha,
                                                                    generations_dir=str(gen_dir)))
    if args.stage == 'smoke':
        smoke = [P.read_json(record_path(run_dir, j)) for j in selected]
        smoke_summary = condition_summary(smoke)
        P.atomic_json(run_dir / 'smoke_summary.json', smoke_summary)
        LOG.info('SMOKE: %s', smoke_summary)
    LOG.info('complete conditions: %d/%d', sum(v['state'] == 'complete' for v in status.values()), len(status))
    print('RUN DIR:', run_dir)


if __name__ == '__main__':
    try:
        main()
    except FatalRunError as exc:
        LOG.error(str(exc))
        print(str(exc), file=sys.stderr)
        sys.exit(2)
