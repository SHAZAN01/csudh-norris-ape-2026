import argparse
import hashlib
import os
import random
import sys
from pathlib import Path
from importlib.metadata import version, distributions
import numpy as np
import faiss
import torch
from sentence_transformers import SentenceTransformer
import baseline_io as baseline
from pilot_common import *


def prepare(pointer_path, revisions_path):
    data, generation_summary = baseline.load_inputs(BASELINE_RUN)
    evaluation_spec = read_json(BASELINE_EVALUATION / 'evaluation_spec.json')
    report = read_json(BASELINE_EVALUATION / 'dev_baseline_metrics.json')
    require(digest(evaluation_spec) == BASELINE_EVALUATION_SHA == report['evaluation_sha256'],
            'Baseline evaluation signature differs.')
    require(evaluation_spec['input_file_hashes'] == baseline.EXPECTED_HASHES,
            'Baseline evaluation inputs differ.')
    scores = {}
    for src, tgt in baseline.DIRECTIONS:
        direction = f'{src}->{tgt}'
        cache = read_json(BASELINE_EVALUATION / f'scores_{src}_{tgt}_dev.json')
        _, values = baseline.validate_score_cache(cache, BASELINE_EVALUATION_SHA, data[direction])
        scores[direction] = dict(zip(cache['sentence_ids'], values))
    ids = [r['sentence_id'] for r in data['eng_Latn->tgl_Latn']['split']]
    pilot_ids = sorted(random.Random(42).sample(ids, 100))
    require(digest(pilot_ids) == PILOT_IDS_SHA, 'Pilot sample differs from the recorded seed-42 sample.')
    excluded = set(pilot_ids)
    revisions = read_json(revisions_path)
    require(revisions['llama_model'] == LLAMA_ID and revisions['labse_model'] == LABSE_ID,
            'Model IDs differ from the funded protocol.')
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob('*.py'))}
    environment = dict(python=sys.version.split()[0], **{name: version(name) for name in
        ['torch', 'transformers', 'sentence-transformers', 'faiss-cpu', 'numpy', 'pydantic']})
    config = dict(prompt_version=PROMPT_VERSION, baseline_evaluation_sha256=BASELINE_EVALUATION_SHA,
        model_revisions=revisions, pilot_ids=pilot_ids, pilot_ids_sha256=digest(pilot_ids),
        sampling='Uniform random sample of 100 aligned dev IDs, Python Random(42); same IDs in all directions.',
        balance='100 query IDs per direction and strategy; not stratified by quality.',
        retrieval='Normalized LaBSE embeddings; exact FAISS inner-product search; dev only.',
        pilot_exclusion='All 100 pilot IDs excluded from demonstrations in every direction; exact duplicate source texts also excluded.',
        reference_rule='Query reference never sent. Only the retrieved non-pilot demonstration may include its own gold dev reference.',
        labse_max_sequence_length=512, schemas={s: schema_for(s) for s in STRATEGIES},
        system_base=SYSTEM_BASE, plain_suffix=PLAIN_SUFFIX, reason_suffix=REASON_SUFFIX,
        environment=environment, code_sha256=source_hashes,
        protocol_status='candidate_not_frozen', GPT_status='pending_API_access')
    config_sha = digest(config)
    directory = ROOT / 'outputs/phase3_post_editing' / f'candidate_{config_sha[:16]}'
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / 'prepared_manifest.json').exists():
        manifest = read_json(directory / 'prepared_manifest.json')
        require(manifest['config'] == config, 'Prepared configuration differs.')
        atomic_json(pointer_path, dict(prepared_dir=str(directory), manifest_sha256=digest(manifest)))
        load_prepared(pointer_path)
        print('PREPARATION RESUMED:', directory, flush=True)
        return

    torch.manual_seed(42)
    require(torch.cuda.is_available(), 'Use the A100 runtime for embedding preparation.')
    encoder = SentenceTransformer(LABSE_ID, revision=revisions['labse_revision'], device='cuda')
    encoder.max_seq_length = 512
    encoder.eval()
    source_rows = {
        'eng_Latn': data['eng_Latn->tgl_Latn']['split'],
        'tgl_Latn': data['tgl_Latn->eng_Latn']['split'],
        'spa_Latn': data['spa_Latn->eng_Latn']['split'],
    }
    neighbors = {}
    embedding_audit = {}
    corpus_map = {}
    for language, rows in source_rows.items():
        texts = [r['source_text'] for r in rows]
        lengths = [len(x) for x in encoder.tokenizer(texts, truncation=False,
                   add_special_tokens=True, padding=False)['input_ids']]
        over = [r['sentence_id'] for r, n in zip(rows, lengths) if n > 512]
        require(not over, f'LaBSE would truncate {language} dev IDs {over}; stopped for review.')
        matrix = np.asarray(encoder.encode(texts, batch_size=64, show_progress_bar=True,
                            convert_to_numpy=True, normalize_embeddings=True), dtype=np.float32)
        require(matrix.shape == (997, 768) and np.isfinite(matrix).all(), 'Invalid LaBSE embeddings.')
        require(np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-5), 'Embeddings are not normalized.')
        with (directory / f'embeddings_{language}.npy').open('wb') as stream:
            np.save(stream, matrix, allow_pickle=False)
        index = faiss.IndexFlatIP(768)
        index.add(np.ascontiguousarray(matrix))
        faiss.write_index(index, str(directory / f'index_{language}.faiss'))
        row_ids = [r['sentence_id'] for r in rows]
        by_id = {r['sentence_id']: r['source_text'] for r in rows}
        corpus_map[language] = [dict(sentence_id=sid, stripped_source_sha256=
            hashlib.sha256(by_id[sid].strip().encode('utf-8')).hexdigest()) for sid in row_ids]
        positions = {sid: i for i, sid in enumerate(row_ids)}
        for sid in pilot_ids:
            similarities, indices = index.search(matrix[positions[sid]:positions[sid]+1], 997)
            ranked_ids = [row_ids[int(i)] for i in indices[0]]
            selected, similarity = select_top1(ranked_ids, similarities[0].tolist(),
                                               excluded, by_id[sid], by_id)
            require(selected not in excluded, 'Pilot reference leakage detected.')
            neighbors[(language, sid)] = (selected, similarity)
        embedding_audit[language] = dict(index_items=int(index.ntotal), embedding_dimension=768,
            eligible_nonpilot_ids=997-len(excluded), max_input_tokens=max(lengths),
            query_count=100, excluded_pilot_demonstrations=100)

    jobs, gold, retrieval_audit, pools = [], [], [], {}
    for src, tgt in baseline.DIRECTIONS:
        direction = f'{src}->{tgt}'
        by_id = {r['sentence_id']: r for r in data[direction]['split']}
        sample_scores = []
        for sid in pilot_ids:
            row = by_id[sid]
            query = dict(sentence_id=sid, src=src, tgt=tgt,
                         source_text=row['source_text'], draft=row['nllb_translation'])
            demo_id, similarity = neighbors[(src, sid)]
            demo_row = by_id[demo_id]
            example = dict(sentence_id=demo_id, src=src, tgt=tgt,
                source_text=demo_row['source_text'], draft=demo_row['nllb_translation'],
                reference_text=demo_row['reference_text'])
            require(demo_id not in excluded, 'A pilot ID was used as an exemplar.')
            sample_scores.append(scores[direction][sid])
            gold.append(dict(direction=direction, sentence_id=sid,
                source_text=row['source_text'], reference_text=row['reference_text'],
                baseline_translation=row['nllb_translation'],
                baseline_comet_native=scores[direction][sid],
                input_segment_count=row['input_segment_count']))
            retrieval_audit.append(dict(direction=direction, query_id=sid,
                demonstration_id=demo_id, cosine_similarity=similarity,
                demonstration_is_pilot=False))
            for strategy in STRATEGIES:
                job = dict(job_key=f'{direction}/{strategy}/{sid}', direction=direction,
                    sentence_id=sid, strategy=strategy, query=query,
                    demonstration_id=demo_id if strategy == 'knn-oneshot' else None,
                    messages=build_messages(query, strategy,
                                            example if strategy == 'knn-oneshot' else None),
                    schema=schema_for(strategy))
                job['job_sha256'] = digest(job)
                jobs.append(job)
        array = np.asarray(sample_scores)
        pools[direction] = dict(n=100, baseline_COMET_lt_080=int((array < .8).sum()),
                               baseline_COMET_ge_090=int((array >= .9).sum()))
    require(len(jobs) == 1200 and len(gold) == 400 and len(retrieval_audit) == 400,
            'Prepared condition counts differ.')
    # Two distinct smoke IDs, including a sampled multi-sentence item.
    multi_ids = {r['sentence_id'] for r in gold if r['input_segment_count'] > 1}
    smoke_ids = choose_smoke_ids(pilot_ids, multi_ids)
    require(len(smoke_ids) == 2, 'Could not select two smoke IDs including a multi-sentence item.')
    write_jsonl(directory / 'jobs.jsonl', jobs)
    write_jsonl(directory / 'evaluation_gold.jsonl', gold)
    atomic_json(directory / 'retrieval_audit.json', retrieval_audit)
    atomic_json(directory / 'retrieval_corpus_map.json', corpus_map)
    atomic_json(directory / 'candidate_protocol.json', config)
    freeze = sorted({f"{d.metadata['Name']}=={d.version}" for d in distributions()
                     if d.metadata.get('Name')})
    (directory / 'requirements_retrieval_resolved.txt').write_text('\n'.join(freeze) + '\n')
    names = ['jobs.jsonl', 'evaluation_gold.jsonl', 'retrieval_audit.json', 'retrieval_corpus_map.json',
             'candidate_protocol.json', 'requirements_retrieval_resolved.txt']
    names += [f'{kind}_{lg}.{ext}' for lg in source_rows
              for kind, ext in [('embeddings', 'npy'), ('index', 'faiss')]]
    manifest = dict(config=config, config_sha256=config_sha, planned_Llama_outputs=1200,
        directions=4, strategies=3, pilot_items_per_direction=100,
        embedding_audit=embedding_audit, pilot_quality_pools=pools, smoke_ids=smoke_ids,
        planned_smoke_outputs=24, file_sha256={name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
                                             for name in names})
    atomic_json(directory / 'prepared_manifest.json', manifest)
    atomic_json(pointer_path, dict(prepared_dir=str(directory), manifest_sha256=digest(manifest)))
    load_prepared(pointer_path)
    print('PREPARATION COMPLETE:', directory, flush=True)
    print('PILOT QUALITY POOLS:', json.dumps(pools, indent=2), flush=True)
    print('SMOKE IDS:', smoke_ids, '| 24 planned outputs', flush=True)
    print('No devtest text or query reference was sent to a post-editor.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pointer', required=True)
    parser.add_argument('--revisions', required=True)
    args = parser.parse_args()
    prepare(args.pointer, args.revisions)
