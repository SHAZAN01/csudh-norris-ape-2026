import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/phase3/post_editing'))
import pydantic
import pilot_common as m
import run_llama_pilot as runner

assert pydantic.__version__ == '2.12.3'
query = dict(sentence_id=7, src='eng_Latn', tgt='spa_Latn',
    source_text='Alice paid 15 dollars.', draft='Alice pagó 15 dólares.',
    reference_text='QUERY_REFERENCE_MUST_NEVER_BE_VISIBLE', baseline_comet_native=0.9)
example = dict(sentence_id=101, src='eng_Latn', tgt='spa_Latn',
    source_text='Bob left.', draft='Bob salió.', reference_text='DEMO_REFERENCE_ALLOWED')
for strategy in m.STRATEGIES:
    messages = m.build_messages(query, strategy, example if strategy == 'knn-oneshot' else None)
    text = json.dumps(messages)
    assert 'QUERY_REFERENCE_MUST_NEVER_BE_VISIBLE' not in text
    assert ('DEMO_REFERENCE_ALLOWED' in text) == (strategy == 'knn-oneshot')
    assert ('baseline_comet_native' in text) is False
    assert messages[-1]['role'] == 'user'
try:
    m.build_messages(query, 'knn-oneshot', {**example, 'sentence_id': 7})
    raise AssertionError('Self exemplar accepted')
except ValueError:
    pass
print('PASS: query-reference isolation, demonstration-reference rule, self-exemplar rejection')

ids = list(range(105))
scores = [1.0] * len(ids)
texts = {i: f'Unique source {i}' for i in ids}
texts[100] = query['source_text']
selected, score = m.select_top1(ids, scores, set(range(100)), query['source_text'], texts)
assert selected == 101 and score == 1.0
print('PASS: all 100 pilot IDs and duplicate source text excluded; tie-break deterministic')
assert m.choose_smoke_ids([1,2,3], {1,2}) == [1,3]
assert m.choose_smoke_ids([1,2,3], {2}) == [1,2]
assert m.choose_smoke_ids([1,2,3], {1,2,3}) == [1,2]
print('PASS: two distinct smoke IDs when the first sampled ID is already multi-sentence')

plain = json.dumps(dict(edited_translation='  Hola.  '))
result = m.extract_response(plain, 'zero-shot', 'baseline', 'stop')
assert result['usable'] and result['edited_translation'] == 'Hola.'
reason = json.dumps(dict(diagnostics=[dict(error_type='NONE', note='No correction needed.')],
                         edited_translation='Hola.'))
result = m.extract_response(reason, 'reason-then-edit', 'baseline', 'stop')
assert result['usable'] and result['schema_valid']
reversed_reason = json.dumps(dict(edited_translation='Hola.',
    diagnostics=[dict(error_type='NONE', note='No correction needed.')]))
result = m.extract_response(reversed_reason, 'reason-then-edit', 'baseline', 'stop')
assert result['schema_valid'] and not result['usable'] and result['fallback_used']
for raw, strategy in [
    ('{"edited_translation":"x","edited_translation":"y"}', 'zero-shot'),
    ('```json\n{"edited_translation":"x"}\n```', 'zero-shot'),
    ('{"edited_translation":""}', 'zero-shot'),
    ('{"edited_translation":"x","commentary":"extra"}', 'zero-shot'),
    (json.dumps(dict(diagnostics=[], edited_translation='x')), 'reason-then-edit'),
    (json.dumps(dict(diagnostics=[dict(error_type='NONE',note='fine'),
        dict(error_type='OMISSION',note='missing')], edited_translation='x')), 'reason-then-edit'),
    (json.dumps(dict(diagnostics=[dict(error_type='OMISSION',note='word '*26)],
                    edited_translation='x')), 'reason-then-edit'),
]:
    value = m.extract_response(raw, strategy, 'baseline', 'stop')
    assert not value['usable'] and value['edited_translation'] == 'baseline'
length = m.extract_response(plain, 'zero-shot', 'baseline', 'length')
assert length['json_parse_success'] and length['schema_valid'] and not length['usable']
assert list(m.schema_for('reason-then-edit')['properties']) == ['diagnostics', 'edited_translation']
print('PASS: valid schemas, duplicate/extra key rejection, NONE exclusivity, brief notes, diagnostic order, truncation fallback')

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    jobs = []
    for i in range(1200):
        job = dict(job_key=f'fixture/{i}', query={'draft': 'baseline'})
        job['job_sha256'] = m.digest(job)
        jobs.append(job)
    m.write_jsonl(root / 'jobs.jsonl', jobs)
    manifest = dict(file_sha256={'jobs.jsonl': __import__('hashlib').sha256(
        (root/'jobs.jsonl').read_bytes()).hexdigest()})
    m.atomic_json(root / 'prepared_manifest.json', manifest)
    pointer = root / 'pointer.json'
    m.atomic_json(pointer, dict(prepared_dir=str(root), manifest_sha256=m.digest(manifest)))
    _, _, loaded = m.load_prepared(pointer)
    assert loaded == jobs
    record = dict(run_sha256='run', job_sha256=jobs[0]['job_sha256'],
                  job_key=jobs[0]['job_key'], edited_translation='baseline', fallback_used=True)
    record['content_sha256'] = m.digest(record)
    runner.validate_record(record, jobs[0], 'run')
    damaged = dict(record, edited_translation='wrong')
    try:
        runner.validate_record(damaged, jobs[0], 'run')
        raise AssertionError('Corrupted model record accepted')
    except ValueError:
        pass
    (root / 'jobs.jsonl').write_text('[]')
    try:
        m.load_prepared(pointer)
        raise AssertionError('Corrupted prepared file accepted')
    except ValueError:
        pass
print('PASS: 1,200-job plan integrity, checkpoint reuse validation, corrupted data rejection')
print('No model generation or GPU execution was performed in these local tests.')
