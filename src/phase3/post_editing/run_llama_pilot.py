import argparse
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
os.environ['VLLM_NO_USAGE_STATS'] = '1'
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version, distributions
from pilot_common import *


def validate_record(record, job, run_sha):
    require(record['run_sha256'] == run_sha, 'Saved model run differs.')
    require(record['job_sha256'] == job['job_sha256'], 'Saved prompt job differs.')
    require(record['job_key'] == job['job_key'], 'Saved job key differs.')
    require(record['content_sha256'] == digest({k: v for k, v in record.items()
                                              if k != 'content_sha256'}),
            'Saved generation checksum differs.')
    require(isinstance(record['edited_translation'], str) and
            record['edited_translation'].strip(), 'Saved translation is empty.')
    if record['fallback_used']:
        require(record['edited_translation'] == job['query']['draft'], 'Fallback differs from baseline.')


def run(pointer_path, stage):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    directory, manifest, all_jobs = load_prepared(pointer_path)
    require(version('vllm') == '0.11.2', 'This runner is pinned to vLLM 0.11.2.')
    for strategy in STRATEGIES:
        require(schema_for(strategy) == manifest['config']['schemas'][strategy],
                'Runtime JSON schema differs from the prepared schema.')
    selected_ids = set(manifest['smoke_ids']) if stage == 'smoke' else set(manifest['config']['pilot_ids'])
    jobs = [j for j in all_jobs if j['sentence_id'] in selected_ids]
    expected = 24 if stage == 'smoke' else 1200
    require(len(jobs) == expected, 'Unexpected requested output count.')
    revisions = manifest['config']['model_revisions']
    tokenizer = AutoTokenizer.from_pretrained(LLAMA_ID,
        revision=revisions['llama_revision'], token=os.environ.get('HF_TOKEN'))
    eot_id = tokenizer.convert_tokens_to_ids('<|eot_id|>')
    require(eot_id is not None and eot_id != tokenizer.unk_token_id, 'LLaMA end-of-turn token missing.')
    stop_ids = sorted(set([tokenizer.eos_token_id, eot_id]))
    sampling = dict(temperature=0.0, top_p=1.0, top_k=-1, max_tokens=1024, seed=42,
                    repetition_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0,
                    stop_token_ids=stop_ids, ignore_eos=False)
    engine_settings = dict(dtype='bfloat16', tensor_parallel_size=1, max_model_len=8192,
        gpu_memory_utilization=.70, max_num_seqs=16, enforce_eager=True,
        enable_prefix_caching=True, seed=42, generation_config='vllm')
    freeze = sorted({f"{d.metadata['Name']}=={d.version}" for d in distributions()
                     if d.metadata.get('Name')})
    environment = dict(python=sys.version.split()[0], **{name: version(name) for name in
        ['vllm', 'torch', 'transformers', 'pydantic', 'huggingface-hub']},
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    spec = dict(prepared_manifest_sha256=digest(manifest), model=LLAMA_ID,
        revision=revisions['llama_revision'], tokenizer_revision=revisions['llama_revision'],
        chat_template_sha256=hashlib.sha256(str(tokenizer.chat_template).encode()).hexdigest(),
        sampling=sampling, engine_settings=engine_settings, environment=environment,
        requirements_sha256=digest(freeze), code_sha256=manifest['config']['code_sha256'],
        invalid_output_policy='Retain raw output; use baseline draft; no response repair or selective retry.',
        translation_normalization='Trim outer whitespace only after schema validation.',
        protocol_status='candidate_not_frozen', GPT_status='pending_API_access')
    run_sha = digest(spec)
    output_dir = directory / 'llama_runs' / run_sha[:16]
    record_dir = output_dir / 'records'
    record_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(output_dir / 'run_spec.json', spec)
    (output_dir / 'requirements_llama_resolved.txt').write_text('\n'.join(freeze) + '\n')

    records, pending = {}, []
    for job in jobs:
        path = record_dir / (digest(job['job_key']) + '.json')
        if path.exists():
            record = read_json(path)
            validate_record(record, job, run_sha)
            records[job['job_key']] = record
        else:
            pending.append(job)
    print(f'{stage.upper()}: {len(records)} completed, {len(pending)} pending; expected {expected}', flush=True)
    initialization_seconds = 0.0
    llm = None
    if pending:
        require(torch.cuda.is_available(), 'An A100 GPU runtime is required.')
        start = time.perf_counter()
        llm = LLM(model=LLAMA_ID, tokenizer=LLAMA_ID, revision=revisions['llama_revision'],
                  tokenizer_revision=revisions['llama_revision'], trust_remote_code=False,
                  **engine_settings)
        initialization_seconds = time.perf_counter() - start

    for strategy in STRATEGIES:
        matching = [j for j in pending if j['strategy'] == strategy]
        parameters = SamplingParams(**sampling,
            structured_outputs=StructuredOutputsParams(json=schema_for(strategy)))
        for start in range(0, len(matching), 16):
            chunk = matching[start:start+16]
            prompts, token_ids = [], []
            for job in chunk:
                prompt = tokenizer.apply_chat_template(job['messages'], tokenize=False,
                                                       add_generation_prompt=True)
                ids = tokenizer.apply_chat_template(job['messages'], tokenize=True,
                                                    add_generation_prompt=True)
                require(ids == tokenizer(prompt, add_special_tokens=False).input_ids,
                        'Chat template/tokenization mismatch.')
                require(len(ids) + sampling['max_tokens'] <= 8192,
                        f'Context overflow: {job["job_key"]}; prompt must be reviewed before generation.')
                prompts.append(prompt)
                token_ids.append(ids)
            before = time.perf_counter()
            outputs = llm.generate([dict(prompt_token_ids=ids) for ids in token_ids],
                                   sampling_params=parameters, use_tqdm=False)
            wall_ms = (time.perf_counter() - before) * 1000
            require(len(outputs) == len(chunk), 'Model returned an unexpected batch size.')
            batch_id = digest(dict(keys=[j['job_key'] for j in chunk],
                                   timestamp=datetime.now(timezone.utc).isoformat()))[:20]
            for job, prompt, ids, output in zip(chunk, prompts, token_ids, outputs):
                require(len(output.outputs) == 1, 'Expected one completion per request.')
                completion = output.outputs[0]
                extracted = extract_response(completion.text, strategy, job['query']['draft'],
                                             completion.finish_reason)
                metrics = getattr(output, 'metrics', None)
                arrival = getattr(metrics, 'arrival_time', None)
                finished = getattr(metrics, 'finished_time', None)
                request_latency = (finished-arrival)*1000 if arrival is not None and finished is not None else None
                record = dict(run_sha256=run_sha, job_sha256=job['job_sha256'],
                    job_key=job['job_key'], direction=job['direction'],
                    sentence_id=job['sentence_id'], strategy=strategy,
                    model_id=LLAMA_ID, model_revision=revisions['llama_revision'], seed=42,
                    messages=job['messages'], rendered_prompt=prompt,
                    raw_completion=completion.text, finish_reason=completion.finish_reason,
                    stop_reason=getattr(completion, 'stop_reason', None),
                    prompt_token_count=len(ids), completion_token_count=len(completion.token_ids),
                    batch_id=batch_id, generation_batch_size=len(chunk), batch_wall_ms=wall_ms,
                    batch_amortized_ms=wall_ms/len(chunk), request_latency_ms=request_latency,
                    latency_note='Batch amortized time is not isolated per-item latency; initialization excluded.',
                    created_utc=datetime.now(timezone.utc).isoformat(),
                    retry_count=0, **extracted)
                record['content_sha256'] = digest(record)
                validate_record(record, job, run_sha)
                atomic_json(record_dir / (digest(job['job_key']) + '.json'), record)
                records[job['job_key']] = record
            print(strategy, f'{min(start+16,len(matching))}/{len(matching)} new requests saved', flush=True)

    ordered = [records[j['job_key']] for j in jobs]
    require(len(ordered) == expected, 'Requested stage is incomplete.')
    groups = {}
    for direction in sorted({j['direction'] for j in jobs}):
        for strategy in STRATEGIES:
            subset = [r for r in ordered if r['direction'] == direction and r['strategy'] == strategy]
            groups[f'{direction}/{strategy}'] = dict(n=len(subset),
                json_parse_success=sum(r['json_parse_success'] for r in subset),
                schema_valid=sum(r['schema_valid'] for r in subset),
                usable=sum(r['usable'] for r in subset),
                fallback_count=sum(r['fallback_used'] for r in subset),
                mean_batch_amortized_ms=sum(r['batch_amortized_ms'] for r in subset)/len(subset),
                prompt_tokens=sum(r['prompt_token_count'] for r in subset),
                completion_tokens=sum(r['completion_token_count'] for r in subset))
    status = ('smoke_complete_review_required' if all(r['usable'] for r in ordered)
              else 'smoke_failed_review_required') if stage == 'smoke' else 'pilot_generated_evaluation_pending'
    summary = dict(stage=stage, status=status, expected_outputs=expected,
        completed_outputs=len(ordered), unusable_outputs=sum(not r['usable'] for r in ordered),
        run_sha256=run_sha, model_initialization_seconds_this_invocation=initialization_seconds,
        groups=groups, protocol_status='candidate_not_frozen', GPT_status='pending_API_access')
    write_jsonl(output_dir / f'{stage}_outputs.jsonl', ordered)
    atomic_json(output_dir / f'{stage}_summary.json', summary)
    atomic_json(Path(pointer_path).with_name('llama_latest_run.json'),
                dict(output_dir=str(output_dir), run_sha256=run_sha, stage=stage))
    print('\nLLAMA STAGE COMPLETE:', status, flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    print('OUTPUT DIRECTORY:', output_dir, flush=True)
    print('Devtest was not opened. The current query reference was not included in any prompt.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pointer', required=True)
    parser.add_argument('--stage', choices=['smoke', 'full'], default='smoke')
    args = parser.parse_args()
    run(args.pointer, args.stage)
