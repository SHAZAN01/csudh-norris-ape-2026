"""Phase 4: prepare the 12,144 frozen devtest post-editing jobs (shared by both editors).

Retrieval (frozen): index the 997 dev SOURCES per source language with normalized
LaBSE (pinned revision) and exact FAISS inner product. For each devtest query, take
the top-1 dev item by cosine with deterministic smallest-ID tie break, excluding dev
items whose stripped source equals the stripped query source. The demonstration may
expose its own dev reference; devtest references never enter any prompt.

Retrieval environment: Python 3.11, torch 2.6.0+cu124, transformers 4.49.0,
sentence-transformers 3.4.1, faiss-cpu 1.9.0, numpy 1.26.4, pydantic 2.12.3.
"""
import argparse
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
sys.path.insert(0, str(HERE.parent / 'phase3' / 'post_editing'))
import norris_protocol as P  # noqa: E402
import baseline_io  # noqa: E402

SOURCE_DIRECTION = {'eng_Latn': 'eng_Latn->tgl_Latn', 'tgl_Latn': 'tgl_Latn->eng_Latn',
                    'spa_Latn': 'spa_Latn->eng_Latn'}


def select_top1(ranked_ids, sims, query_text, source_by_id):
    cands = [(float(s), sid) for sid, s in zip(ranked_ids, sims)
             if source_by_id[sid].strip() != query_text.strip()]
    P.require(bool(cands), 'No eligible dev exemplar remains.')
    score, sid = min(cands, key=lambda v: (-v[0], v[1]))
    return sid, score


def load_s0(root):
    ptr = P.read_json(root / 'outputs/phase4/devtest_baseline_latest.json')
    run = Path(ptr['run_dir'])
    summ = P.read_json(run / 'generation_summary.json')
    P.require(summ['run_spec_sha256'] == ptr['run_spec_sha256'] == P.digest(P.read_json(run / 'run_spec.json')),
              'Devtest baseline run spec differs.')
    out = {}
    for src, tgt in P.DIRECTIONS:
        d = f'{src}->{tgt}'
        rows = {}
        for cond in ['sentence_split', 'unsplit_control']:
            name = f'nllb3.3b_{src}_{tgt}_devtest_{cond}.jsonl'
            P.require(P.file_sha256(run / name) == summ['directions'][d]['file_sha256'][name], 'S0 checksum differs.')
            rows[cond] = sorted(P.read_jsonl(run / name), key=lambda r: r['sentence_id'])
            P.require(len(rows[cond]) == 1012, 'S0 must have 1,012 rows.')
        out[d] = rows
    return run, summ, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--freeze', required=True)
    args = ap.parse_args()
    import numpy as np
    import faiss
    import torch
    from sentence_transformers import SentenceTransformer
    root = Path(args.root)
    freeze = P.read_json(args.freeze)
    P.require(freeze.get('freeze_declared') is True, 'Freeze not declared.')
    P.require(freeze['protocol']['fingerprint'] == P.protocol_fingerprint(), 'Protocol differs from freeze.')
    s0_dir, s0_summary, s0 = load_s0(root)
    dev, _ = baseline_io.load_inputs(root / 'outputs/generations/baselines/phase3_dev_f4a3af94ba1e72fd')

    torch.manual_seed(42)
    P.require(torch.cuda.is_available(), 'Use the A100 runtime for LaBSE.')
    enc = SentenceTransformer('sentence-transformers/LaBSE', revision=P.REVISIONS['labse'], device='cuda')
    enc.max_seq_length = 512
    enc.eval()

    def embed(texts):
        lens = [len(x) for x in enc.tokenizer(texts, truncation=False, add_special_tokens=True,
                                               padding=False)['input_ids']]
        P.require(max(lens) <= 512, 'LaBSE would truncate an input; stop for review.')
        m = np.asarray(enc.encode(texts, batch_size=64, convert_to_numpy=True, normalize_embeddings=True,
                                  show_progress_bar=False), dtype=np.float32)
        P.require(np.isfinite(m).all() and np.allclose(np.linalg.norm(m, axis=1), 1, atol=1e-5), 'Bad embeddings.')
        return m

    v2_check = {}
    links, neighbors = [], {}
    for lang, d0 in SOURCE_DIRECTION.items():
        pool = dev[d0]['split']
        pool_ids = [r['sentence_id'] for r in pool]
        src_by_id = {r['sentence_id']: r['source_text'] for r in pool}
        mat = embed([r['source_text'] for r in pool])
        v2_emb = Path(P.read_json(root / 'outputs/phase3_post_editing/rte_v3_latest.json')['jobs_dir'])
        v2_dir = Path(P.read_json(v2_emb / 'prepared_manifest.json')['v2_prepared_dir'])
        old = np.load(v2_dir / f'embeddings_{lang}.npy')
        v2_check[lang] = float(np.abs(old - mat).max())
        P.require(v2_check[lang] <= 1e-5, f'Dev LaBSE embeddings differ from the measured pilot ({v2_check[lang]:.2e}).')
        index = faiss.IndexFlatIP(768)
        index.add(np.ascontiguousarray(mat))
        queries = s0['eng_Latn->tgl_Latn' if lang == 'eng_Latn' else d0]['sentence_split']
        qmat = embed([r['source_text'] for r in queries])
        sims, idx = index.search(np.ascontiguousarray(qmat), 997)
        for r, srow, irow in zip(queries, sims, idx):
            ranked = [pool_ids[int(i)] for i in irow]
            sid, score = select_top1(ranked, srow.tolist(), r['source_text'], src_by_id)
            excluded = [x for x in pool_ids if src_by_id[x].strip() == r['source_text'].strip()]
            neighbors[(lang, r['sentence_id'])] = sid
            links.append(dict(source_language=lang, devtest_query_id=r['sentence_id'], dev_demonstration_id=sid,
                              cosine_similarity=score, excluded_exact_duplicate_dev_ids=excluded))

    jobs, gold = [], []
    for src, tgt in P.DIRECTIONS:
        d = f'{src}->{tgt}'
        dev_by_id = {r['sentence_id']: r for r in dev[d]['split']}
        uns = {r['sentence_id']: r for r in s0[d]['unsplit_control']}
        for r in s0[d]['sentence_split']:
            sid = r['sentence_id']
            P.require(uns[sid]['source_text'] == r['source_text'], 'S0 alignment differs.')
            query = dict(partition='devtest', sentence_id=sid, src=src, tgt=tgt,
                         source_text=r['source_text'], draft=r['nllb_translation'])
            demo = dev_by_id[neighbors[(src, sid)]]
            example = dict(partition='dev', sentence_id=demo['sentence_id'], src=src, tgt=tgt,
                           source_text=demo['source_text'], draft=demo['nllb_translation'],
                           reference_text=demo['reference_text'])
            gold.append(dict(direction=d, sentence_id=sid, source_text=r['source_text'],
                             reference_text=r['reference_text'], baseline_translation=r['nllb_translation'],
                             unsplit_translation=uns[sid]['nllb_translation'],
                             input_segment_count=r['input_segment_count']))
            for s in P.STRATEGIES:
                ex = example if s == 'knn-oneshot' else None
                job = dict(job_key=f'{d}/{s}/{sid}', partition='devtest', direction=d, sentence_id=sid,
                           strategy=s, query=query, example=ex,
                           demonstration_id=demo['sentence_id'] if ex else None,
                           messages=P.build_frozen_messages(query, s, ex), schema=P.schema_for(s))
                job['job_sha256'] = P.digest(job)
                jobs.append(job)
    P.require(len(jobs) == 12144 and len(gold) == 4048 and len(links) == 3036, 'Planned counts differ.')
    # Structural isolation is enforced by the builder (queries carry no reference field).
    # Textual check: a devtest reference may appear in a prompt only where it is identical
    # to text legitimately present (the NLLB draft, the source, or the dev demonstration).
    gold_ref = {(g['direction'], g['sentence_id']): g['reference_text'] for g in gold}
    leaks = 0
    for j in jobs:
        ref = gold_ref[(j['direction'], j['sentence_id'])]
        if ref in P.canonical(j['messages']).decode():
            allowed = j['query']['draft'] + '\n' + j['query']['source_text']
            if j['example']:
                allowed += '\n' + '\n'.join(j['example'][k] for k in ['source_text', 'draft', 'reference_text'])
            leaks += ref not in allowed
    P.require(leaks == 0, f'{leaks} prompts contain their own devtest reference.')

    multi = sorted(g['sentence_id'] for g in gold if g['direction'] == 'eng_Latn->tgl_Latn' and g['input_segment_count'] > 1)
    single = sorted(g['sentence_id'] for g in gold if g['direction'] == 'eng_Latn->tgl_Latn' and g['input_segment_count'] == 1)
    smoke_ids = sorted([multi[0], single[0]])
    out = root / 'outputs/phase4/main_prepared' / ('main_' + P.digest([j['job_sha256'] for j in jobs])[:16])
    out.mkdir(parents=True, exist_ok=True)
    P.write_jsonl(out / 'jobs.jsonl', jobs)
    P.write_jsonl(out / 'gold_devtest.jsonl', gold)
    P.write_jsonl(out / 'retrieval_links.jsonl', links)
    files = {n: P.file_sha256(out / n) for n in ['jobs.jsonl', 'gold_devtest.jsonl', 'retrieval_links.jsonl']}
    manifest = dict(stage='phase4_main_prepared', partition='devtest', protocol_id=P.PROTOCOL_ID,
                    protocol_fingerprint=P.protocol_fingerprint(), freeze_sha256=P.file_sha256(args.freeze),
                    s0_run_spec_sha256=s0_summary['run_spec_sha256'], s0_dir=str(s0_dir),
                    planned_jobs=12144, items_per_condition=1012, directions=4, strategies=3,
                    planned_outputs_both_models=24288, smoke_ids=smoke_ids,
                    retrieval=dict(model='sentence-transformers/LaBSE', revision=P.REVISIONS['labse'],
                                   pool='all 997 dev IDs per source language', exclusion='exact stripped-source duplicates',
                                   tie_break='smallest dev sentence_id', index='faiss.IndexFlatIP over normalized float32',
                                   dev_embedding_max_abs_diff_vs_pilot=v2_check,
                                   queries_with_excluded_duplicates=sum(bool(x['excluded_exact_duplicate_dev_ids']) for x in links)),
                    reference_leak_check=dict(prompts_checked=len(jobs), leaks=0),
                    environment={k: version(k) for k in ['torch', 'transformers', 'sentence-transformers',
                                                         'faiss-cpu', 'numpy', 'pydantic']},
                    preparer_sha256=P.file_sha256(Path(__file__)), file_sha256=files,
                    created_utc=datetime.now(timezone.utc).isoformat())
    P.atomic_json(out / 'prepared_manifest.json', manifest)
    P.atomic_json(root / 'outputs/phase4/main_prepared_latest.json', dict(jobs_dir=str(out)))
    print('PREPARED:', out, '| jobs', len(jobs), '| smoke IDs', smoke_ids)


if __name__ == '__main__':
    main()
