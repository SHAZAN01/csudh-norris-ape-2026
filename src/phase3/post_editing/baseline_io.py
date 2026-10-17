"""Resume-safe dev-only baseline evaluation; no NLLB or post-editor generation."""
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import sys
import json
import math
import hashlib
from pathlib import Path
from importlib.metadata import version, distributions

RUN_NAME = 'phase3_dev_f4a3af94ba1e72fd'
EXPECTED_RUN_SHA = 'f4a3af94ba1e72fddc14a8986924fc23e00ae2884dc8d51800ad79e43a6a0563'
COMET_ID = 'Unbabel/wmt22-comet-da'
COMET_REV = '2760a223ac957f30acfb18c8aa649b01cf1d75f2'
DIRECTIONS = [('eng_Latn', 'tgl_Latn'), ('tgl_Latn', 'eng_Latn'),
              ('eng_Latn', 'spa_Latn'), ('spa_Latn', 'eng_Latn')]
EXPECTED_HASHES = {
 'nllb3.3b_eng_Latn_tgl_Latn_dev_unsplit_control.jsonl': '4a17a36f513a5eb90b05d3192179124605bd99c65902bdbdd7bf5463ef091f9f',
 'nllb3.3b_eng_Latn_tgl_Latn_dev_sentence_split.jsonl': 'd6617cb4b12dc23203326970cc5db9d217be6cdfc658e2b4c3eb59f67e252176',
 'nllb3.3b_tgl_Latn_eng_Latn_dev_unsplit_control.jsonl': 'e218625b96cffb539f42e368a26c025b400a457c3f6d35a9625e97de9478abd0',
 'nllb3.3b_tgl_Latn_eng_Latn_dev_sentence_split.jsonl': '8a0924a378738010fdb13f4a0a5eaa7da8bbda30d3bcc4fa526c26c50c47a3f4',
 'nllb3.3b_eng_Latn_spa_Latn_dev_unsplit_control.jsonl': '575b6519738da932ae6dc9520f61b6c4ac5db669b81121d304e18b2df81bf43c',
 'nllb3.3b_eng_Latn_spa_Latn_dev_sentence_split.jsonl': '34b1d8f011d4addeae4dda7049ac58fea35a9beb8d07dd8d0201665f088d0a42',
 'nllb3.3b_spa_Latn_eng_Latn_dev_unsplit_control.jsonl': 'a0eda958cf61561208ebff752bc54b10d41a8b996251b8c02cf1bf7684a840c3',
 'nllb3.3b_spa_Latn_eng_Latn_dev_sentence_split.jsonl': '291c5e9ca8c0fdbf7108bfeb7949f793939e1cbf66f35238b4165819e95ce088',
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
    os.replace(temporary, path)


def read_json(path):
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f)


def load_inputs(input_dir):
    """Validate the saved run against the exact hashes recorded in chat."""
    input_dir = Path(input_dir)
    summary = read_json(input_dir / 'generation_summary.json')
    spec = read_json(input_dir / 'run_spec.json')
    require(summary['run_spec_sha256'] == EXPECTED_RUN_SHA, 'Unexpected generation run.')
    require(digest(spec) == EXPECTED_RUN_SHA, 'Generation configuration hash differs.')
    data = {}
    common_ids = None
    for src, tgt in DIRECTIONS:
        direction = f'{src}->{tgt}'
        pair = {}
        for label in ['unsplit_control', 'sentence_split']:
            name = f'nllb3.3b_{src}_{tgt}_dev_{label}.jsonl'
            path = input_dir / name
            require(path.is_file(), f'Missing saved baseline: {name}')
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            require(actual == EXPECTED_HASHES[name], f'Checksum mismatch: {name}')
            require(summary['directions'][direction]['file_sha256'][name] == actual,
                    f'Summary checksum differs: {name}')
            with path.open(encoding='utf-8') as f:
                rows = sorted([json.loads(line) for line in f if line.strip()],
                              key=lambda r: r['sentence_id'])
            ids = [r['sentence_id'] for r in rows]
            require(len(rows) == len(set(ids)) == 997, f'Bad row IDs: {name}')
            if common_ids is None:
                common_ids = ids
            require(ids == common_ids, f'ID alignment differs: {name}')
            for row in rows:
                require(row['split'] == 'dev', 'Only dev is permitted.')
                require(row['direction'] == direction, 'Direction field differs.')
                require(row['run_spec_sha256'] == EXPECTED_RUN_SHA, 'Row provenance differs.')
                require(all(isinstance(row[k], str) and row[k].strip() for k in
                            ['source_text', 'reference_text', 'nllb_translation']),
                        f'Empty or invalid text: {name}')
            pair[label] = rows
        u, s = pair['unsplit_control'], pair['sentence_split']
        changed, multi = [], []
        for a, b in zip(u, s):
            require(all(a[k] == b[k] for k in
                        ['sentence_id', 'source_text', 'reference_text']),
                    'Paired sources/references differ.')
            require(''.join(b['source_segments']) == b['source_text'],
                    'Source reconstruction differs.')
            changed.append(a['nllb_translation'] != b['nllb_translation'])
            multi.append(b['input_segment_count'] > 1)
        require(all(not c or m for c, m in zip(changed, multi)),
                'A single-sentence item differs across conditions.')
        require(sum(changed) == summary['directions'][direction][
                    'split_outputs_different_from_current_control'], 'Changed count differs.')
        data[direction] = dict(unsplit=u, split=s, changed=changed, multi=multi)
    return data, summary


def validate_score_cache(cache, evaluation_sha, item):
    ids = [r['sentence_id'] for r in item['unsplit']]
    require(cache['evaluation_sha256'] == evaluation_sha, 'Score provenance differs.')
    require(cache['sentence_ids'] == ids, 'Score IDs differ.')
    require(cache['content_sha256'] == digest({k: v for k, v in cache.items()
                                             if k != 'content_sha256'}),
            'Score cache checksum differs.')
    u, s = cache['unsplit_scores_native'], cache['split_scores_native']
    require(len(u) == len(s) == 997, 'Score counts differ.')
    require(all(isinstance(x, (int, float)) and math.isfinite(x) for x in u + s),
            'Invalid COMET scores.')
    require(all(c or a == b for c, a, b in zip(item['changed'], u, s)),
            'Identical translations have different cached scores.')
    return u, s


def find_completed_evaluation(input_dir, data):
    """Reuse a validated completed evaluation, including yesterday's script."""
    candidates = sorted((Path(input_dir) / 'evaluation').glob('*/dev_baseline_metrics.json'),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            report = read_json(path)
            spec = read_json(path.parent / 'evaluation_spec.json')
            sha = digest(spec)
            require(report['status'] == 'dev_baseline_evaluation_complete', 'Incomplete report.')
            require(report['evaluation_sha256'] == sha, 'Evaluation signature differs.')
            require(spec['generation_run_sha256'] == EXPECTED_RUN_SHA, 'Wrong generation run.')
            require(spec['input_file_hashes'] == EXPECTED_HASHES, 'Wrong input hashes.')
            require(spec['comet_model'] == COMET_ID and spec['comet_revision'] == COMET_REV,
                    'Wrong COMET checkpoint.')
            require(spec['bootstrap_resamples'] == 10000, 'Unexpected bootstrap count.')
            require('word_order=2' in spec['chrf'], 'Wrong chrF word order.')
            for src, tgt in DIRECTIONS:
                direction = f'{src}->{tgt}'
                result = report['results'][direction]
                require(result['n'] == 997, 'Wrong reported count.')
                require(result['text_outputs_changed'] == sum(data[direction]['changed']),
                        'Reported changed count differs.')
                require(result['multi_sentence_items'] == sum(data[direction]['multi']),
                        'Reported multi-sentence count differs.')
                cache = read_json(path.parent / f'scores_{src}_{tgt}_dev.json')
                u, s = validate_score_cache(cache, sha, data[direction])
                for label, scores in [('current_unsplit', u), ('sentence_split', s)]:
                    metrics = result[label]
                    require(abs(metrics['COMET_points'] - sum(scores) / 997 * 100) < 1e-8,
                            'Reported mean COMET differs from saved scores.')
                    require(all(math.isfinite(metrics[k]) for k in ['BLEU', 'chrF++']),
                            'Invalid lexical metric.')
                    require('nw:2' in metrics['chrF_signature'] and
                            'nc:6' in metrics['chrF_signature'], 'Unexpected chrF signature.')
                    require('tok:13a' in metrics['BLEU_signature'], 'Unexpected BLEU tokenizer.')
                difference = result['paired_delta_all_items']
                expected_mean = sum(b - a for a, b in zip(u, s)) / 997 * 100
                require(difference['n'] == 997 and
                        abs(difference['mean_difference_points'] - expected_mean) < 1e-8,
                        'Reported paired mean differs from saved scores.')
                lo, hi = difference['ci95_points']
                require(math.isfinite(lo) and math.isfinite(hi) and lo <= hi,
                        'Invalid reported confidence interval.')
            return path, report
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f'Existing evaluation not reused: {path.parent.name}: {exc}', flush=True)
    return None, None


def paired_mean_ci(differences, resamples=10000, seed=42):
    import numpy as np
    values = np.asarray(differences, dtype=np.float64)
    require(values.ndim == 1 and len(values) > 0 and np.isfinite(values).all(),
            'Invalid bootstrap input.')
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, resamples, 128):
        count = min(128, resamples - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means.append(values[indices].mean(axis=1))
    low, high = np.quantile(np.concatenate(means), [0.025, 0.975])
    return dict(n=len(values), mean_difference_points=float(values.mean() * 100),
                ci95_points=[float(low * 100), float(high * 100)])


def main():
    import numpy as np
    import torch
    from comet import load_from_checkpoint
    from huggingface_hub import snapshot_download
    from sacrebleu.metrics import BLEU, CHRF

    root = Path('/content/drive/MyDrive/norris')
    input_dir = root / 'outputs/generations/baselines' / RUN_NAME
    data, generation_summary = load_inputs(input_dir)
    completed_path, completed_report = find_completed_evaluation(input_dir, data)
    if completed_path:
        print('DEV BASELINE EVALUATION ALREADY COMPLETE')
        print(json.dumps(completed_report['results'], indent=2))
        print('RESULT DIRECTORY:', completed_path.parent)
        return

    require(sys.version_info[:2] == (3, 11), 'Use the isolated Python 3.11 environment.')
    require(torch.cuda.is_available(), 'Connect an A100 GPU runtime before scoring.')
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    torch.set_float32_matmul_precision('highest')
    environment = {'python': sys.version.split()[0], **{name: version(name) for name in
        ['torch', 'transformers', 'unbabel-comet', 'numpy', 'sacrebleu', 'huggingface-hub',
         'pytorch-lightning', 'torchmetrics', 'sentencepiece']},
        'gpu': torch.cuda.get_device_name(0)}
    freeze = sorted({f"{d.metadata['Name']}=={d.version}" for d in distributions()
                     if d.metadata.get('Name')})
    spec = dict(generation_run_sha256=EXPECTED_RUN_SHA, input_file_hashes=EXPECTED_HASHES,
        comet_model=COMET_ID, comet_revision=COMET_REV, comet_batch_size=64,
        length_batching=True, mc_dropout=0, num_workers=2,
        float32_matmul_precision='highest', bootstrap_resamples=10000, bootstrap_seed=42,
        bootstrap_method='paired percentile CI for mean COMET difference',
        difference_orientation='sentence_split minus current_unsplit',
        comet_report_scale='native score multiplied by 100',
        bleu='13a; mixed case; exponential smoothing',
        chrf='char_order=6; word_order=2; beta=2', environment=environment,
        resolved_packages_sha256=digest(freeze),
        evaluator_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    sha = digest(spec)
    output_dir = input_dir / 'evaluation' / sha[:16]
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(output_dir / 'evaluation_spec.json', spec)
    (output_dir / 'requirements_resolved.txt').write_text('\n'.join(freeze) + '\n')
    model = None

    def predict(rows):
        nonlocal model
        if not rows:
            return np.empty(0, dtype=np.float64)
        if model is None:
            snapshot = Path(snapshot_download(repo_id=COMET_ID, revision=COMET_REV,
                allow_patterns=['checkpoints/model.ckpt', 'hparams.yaml']))
            model = load_from_checkpoint(str(snapshot / 'checkpoints/model.ckpt'))
            model.eval()
            encoder = getattr(getattr(model, 'encoder', None), 'model', None)
            atomic_json(output_dir / 'model_provenance.json', dict(
                comet_model=COMET_ID, comet_revision=COMET_REV,
                encoder_config_commit=getattr(getattr(encoder, 'config', None), '_commit_hash', None)))
        prediction = model.predict([dict(src=r['source_text'], mt=r['nllb_translation'],
            ref=r['reference_text']) for r in rows], batch_size=64, gpus=1,
            progress_bar=False, num_workers=2, length_batching=True, mc_dropout=0)
        scores = np.asarray(prediction.scores, dtype=np.float64)
        require(len(scores) == len(rows) and np.isfinite(scores).all(), 'Invalid COMET output.')
        return scores

    def metrics(rows, scores):
        hypotheses = [r['nllb_translation'] for r in rows]
        references = [[r['reference_text'] for r in rows]]
        bleu, chrf = BLEU(tokenize='13a'), CHRF(char_order=6, word_order=2, beta=2)
        b, c = bleu.corpus_score(hypotheses, references), chrf.corpus_score(hypotheses, references)
        return {'BLEU': float(b.score), 'chrF++': float(c.score),
                'COMET_points': float(scores.mean() * 100),
                'BLEU_signature': str(bleu.get_signature()), 'chrF_signature': str(chrf.get_signature())}

    results = {}
    for src, tgt in DIRECTIONS:
        direction = f'{src}->{tgt}'
        item = data[direction]
        u, s = item['unsplit'], item['split']
        changed = np.asarray(item['changed'], dtype=bool)
        multi = np.asarray(item['multi'], dtype=bool)
        path = output_dir / f'scores_{src}_{tgt}_dev.json'
        if path.exists():
            a, b = validate_score_cache(read_json(path), sha, item)
            a, b = np.asarray(a), np.asarray(b)
            print('RESUMED:', direction, flush=True)
        else:
            print('SCORING:', direction, flush=True)
            a = predict(u)
            b = a.copy()
            indices = np.flatnonzero(changed)
            b[indices] = predict([s[int(i)] for i in indices])
            cache = dict(evaluation_sha256=sha, sentence_ids=[r['sentence_id'] for r in u],
                         unsplit_scores_native=a.tolist(), split_scores_native=b.tolist())
            cache['content_sha256'] = digest(cache)
            validate_score_cache(cache, sha, item)
            atomic_json(path, cache)
        delta = b - a
        result = dict(n=997, multi_sentence_items=int(multi.sum()),
            text_outputs_changed=int(changed.sum()),
            current_unsplit=metrics(u, a), sentence_split=metrics(s, b),
            paired_delta_all_items=paired_mean_ci(delta),
            paired_delta_multi_sentence_items=paired_mean_ci(delta[multi]),
            metric_change_bins_native_threshold_002={
                'increased_gt_0.02': int((delta > .02).sum()),
                'within_inclusive_plus_minus_0.02': int((np.abs(delta) <= .02).sum()),
                'decreased_gt_0.02': int((delta < -.02).sum())},
            sentence_split_baseline_pools={'COMET_lt_0.80': int((b < .8).sum()),
                                          'COMET_ge_0.90': int((b >= .9).sum())})
        old_path = root / 'outputs/logs' / f'comet_seg_nllb_{src}_{tgt}_dev.json'
        if old_path.exists():
            old = read_json(old_path)
            old_scores = np.asarray([old[str(r['sentence_id'])] for r in u], dtype=np.float64)
            require(np.isfinite(old_scores).all(), 'Invalid saved Phase 2 COMET scores.')
            diff = a - old_scores
            result['phase2_comet_recheck'] = dict(mean_difference_points=float(diff.mean() * 100),
                max_absolute_difference_native=float(np.abs(diff).max()),
                mean_absolute_difference_native=float(np.abs(diff).mean()))
        results[direction] = result
        print('DONE:', direction, '| COMET unsplit / split:',
              round(result['current_unsplit']['COMET_points'], 4),
              round(result['sentence_split']['COMET_points'], 4), flush=True)
    report = dict(status='dev_baseline_evaluation_complete',
        interpretation='Exploratory dev baseline diagnostic; not the LLM pilot or devtest evaluation.',
        evaluation_sha256=sha, environment=environment, bootstrap_resamples=10000,
        difference_orientation='sentence_split minus current_unsplit', results=results)
    atomic_json(output_dir / 'dev_baseline_metrics.json', report)
    print('\nDEV BASELINE EVALUATION COMPLETE')
    print(json.dumps(results, indent=2))
    print('\nRESULT DIRECTORY:', output_dir)
    print('Devtest was not opened.')


if __name__ == '__main__':
    main()

