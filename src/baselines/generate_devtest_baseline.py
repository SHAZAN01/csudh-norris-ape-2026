"""Primary NLLB-200 3.3B sentence-split baseline (S0) for FLORES+ devtest.

Stages (run in order):
  verify-dev-segmentation  CPU. The reconstructed splitter must reproduce all 2,991 saved dev
                           source segmentations exactly.                       -> gate_dev_segmentation.json
  audit-dev-generation     GPU, dev only. Measures (does not guess) how closely the frozen
                           generation procedure reproduces the saved dev baseline:
                             * join rule on the saved fragment translations (must be exact),
                             * the frozen fragment variant on all dev multi-segment items, run
                               twice (must be identical across the two runs = deterministic here),
                             * agreement with the saved dev split translations (>= 95% required),
                             * agreement of a regenerated dev unsplit control with the saved one
                               (reported, not gated).
                           Writes a text-free gate_dev_generation.json.
  devtest                  GPU. Requires both gates and a declared freeze whose code hashes match.
                           Unsplit devtest drafts = the checksum-locked Phase 2 archive (as on dev,
                           where the split condition reused the unsplit control); fragments of
                           multi-segment items are translated with the frozen variant. A
                           regenerated unsplit control is compared with the archive and reported.

Why exact equality is not required for translations (decision recorded 23 Oct 2026): the original
split-generation cell was not recovered; segmentation reproduces exactly, but FP16 padded beam
search is sensitive to batch composition and kernel numerics. Measured on dev multi-segment items
(421): strip input 237; raw input with sentence order 408, length-desc chars 412, length-desc tokens
412, length-asc 411, unbatched 407, per-item batches 408. No ordering reaches 421, including
unbatched decoding, so the residual is numerical, not a recoverable procedure detail. The frozen
variant is the best measured one (raw input, length-descending by characters, batch 32).

Environment (matches the measured dev baseline run): Python 3.13, torch 2.11.0+cu130,
transformers 5.18.0, tokenizers 0.23.2, sentencepiece 0.2.2, huggingface_hub 1.33.0, pysbd 0.3.4.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import norris_splitter as S  # noqa: E402

CKPT = 'facebook/nllb-200-3.3B'
NLLB_REV = '1a07f7d195896b2114afcb79b7b57ab512e7b43e'
DIRECTIONS = [('eng_Latn', 'tgl_Latn'), ('tgl_Latn', 'eng_Latn'),
              ('eng_Latn', 'spa_Latn'), ('spa_Latn', 'eng_Latn')]
DEV_RUN = 'outputs/generations/baselines/phase3_dev_f4a3af94ba1e72fd'
DEV_RUN_SHA = 'f4a3af94ba1e72fddc14a8986924fc23e00ae2884dc8d51800ad79e43a6a0563'
DECODE = dict(num_beams=4, max_length=512, length_penalty=1.0, early_stopping=True, do_sample=False)
BATCH = 32
FROZEN_VARIANT = dict(name='raw_len_chars_desc_b32', fragment_input='raw', order='len_chars_desc', batch=32,
                      join='single_space_between_stripped_fragment_translations')
MEASURED_VARIANTS_DEV = [  # exact / 421 dev multi-segment items, measured 23 Oct 2026 (Colab A100)
    dict(name='strip_fragments_sentence_b32', exact=237), dict(name='raw_sentence_order_b32', exact=408),
    dict(name='raw_len_chars_desc_b32', exact=412), dict(name='raw_len_tokens_desc_b32', exact=412),
    dict(name='raw_len_chars_asc_b32', exact=411), dict(name='raw_unbatched_b1', exact=407),
    dict(name='raw_per_item_batches', exact=408)]
MIN_DEV_SPLIT_AGREEMENT = 0.95


def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(v):
    return hashlib.sha256(canonical(v)).hexdigest()


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(c, m):
    if not c:
        raise SystemExit('STOP: ' + m)


def wjson(p, v):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_name(p.name + '.tmp')
    t.write_text(json.dumps(v, ensure_ascii=False, indent=2))
    os.replace(t, p)


def rjsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]


def wjsonl(p, rows):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_name(p.name + '.tmp')
    t.write_text(''.join(canonical(r).decode() + '\n' for r in rows), encoding='utf-8')
    os.replace(t, p)


def code_hashes():
    return {'norris_splitter.py': fsha(HERE / 'norris_splitter.py'),
            'generate_devtest_baseline.py': fsha(Path(__file__))}


def env_info():
    info = dict(python=sys.version.split()[0])
    try:
        import torch
        import transformers
        info.update(torch=torch.__version__, transformers=transformers.__version__,
                    gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    except ImportError:
        info.update(torch=None, transformers=None, gpu=None)
    return info


def join_fragments(translations):
    return ' '.join(t.strip() for t in translations)


def lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load_dev(root):
    run = root / DEV_RUN
    summary = json.loads((run / 'generation_summary.json').read_text())
    require(summary['run_spec_sha256'] == DEV_RUN_SHA, 'Unexpected dev baseline run.')
    out = {}
    for src, tgt in DIRECTIONS:
        d = f'{src}->{tgt}'
        rows = {}
        for cond in ['sentence_split', 'unsplit_control']:
            name = f'nllb3.3b_{src}_{tgt}_dev_{cond}.jsonl'
            require(fsha(run / name) == summary['directions'][d]['file_sha256'][name], 'Dev checksum differs: ' + name)
            rows[cond] = sorted(rjsonl(run / name), key=lambda r: r['sentence_id'])
            require(len(rows[cond]) == 997, 'Dev row count differs.')
        out[d] = rows
    return out


# ------------------------------------------------------------------ gate 1 (CPU)
def verify_dev_segmentation(root, state):
    dev = load_dev(root)
    by_lang = {'eng_Latn': dev['eng_Latn->tgl_Latn']['sentence_split'],
               'tgl_Latn': dev['tgl_Latn->eng_Latn']['sentence_split'],
               'spa_Latn': dev['spa_Latn->eng_Latn']['sentence_split']}
    report, mismatches = {}, []
    for lang, rows in by_lang.items():
        exact = multi = frags = 0
        for r in rows:
            seg = S.segment(r['source_text'], lang)
            exact += seg == r['source_segments']
            multi += len(seg) > 1
            frags += len(seg)
            if seg != r['source_segments']:
                mismatches.append(dict(language=lang, sentence_id=r['sentence_id']))
        report[lang] = dict(items=len(rows), exact=exact, multi_segment_items=multi, fragments=frags)
    for d, rows in dev.items():
        ref = {r['sentence_id']: r['source_segments'] for r in by_lang[d.split('->')[0]]}
        require(all(ref[r['sentence_id']] == r['source_segments'] for r in rows['sentence_split']),
                'Saved segmentation differs across directions.')
    gate = dict(gate='dev_segmentation', passed=not mismatches, report=report, n_mismatches=len(mismatches),
                mismatch_ids=mismatches[:50], splitter_version=S.SPLITTER_VERSION, pysbd=S.PYSBD_VERSION,
                patterns=S.PATTERNS, code_sha256=code_hashes(), created_utc=datetime.now(timezone.utc).isoformat())
    wjson(state / 'gate_dev_segmentation.json', gate)
    print(json.dumps({k: gate[k] for k in ['passed', 'report', 'n_mismatches']}, indent=2))
    require(gate['passed'], 'Splitter does not reproduce the saved dev segmentation; do not touch devtest.')


# ------------------------------------------------------------------ NLLB
class NLLB:
    def __init__(self, token):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        torch.manual_seed(42)
        torch.set_float32_matmul_precision('highest')
        require(torch.cuda.is_available(), 'A100 runtime required.')
        self.torch, self.AutoTokenizer, self.token = torch, AutoTokenizer, token
        self.model = AutoModelForSeq2SeqLM.from_pretrained(CKPT, revision=NLLB_REV, dtype=torch.float16,
                                                           token=token).cuda().eval()
        self.toks = {}

    def tok(self, src):
        if src not in self.toks:
            self.toks[src] = self.AutoTokenizer.from_pretrained(CKPT, revision=NLLB_REV, src_lang=src,
                                                                use_fast=True, token=self.token)
        return self.toks[src]

    def translate(self, texts, src, tgt, batch=BATCH):
        tok = self.tok(src)
        bos = tok.convert_tokens_to_ids(tgt)
        out, seconds = [], 0.0
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            require(max(len(x) for x in tok(chunk, truncation=False)['input_ids']) <= 512,
                    'Input exceeds 512 tokens; no silent truncation.')
            enc = tok(chunk, return_tensors='pt', padding=True, truncation=False).to('cuda')
            t0 = time.perf_counter()
            with self.torch.inference_mode():
                gen = self.model.generate(**enc, forced_bos_token_id=bos, **DECODE)
            self.torch.cuda.synchronize()
            seconds += time.perf_counter() - t0
            out.extend(tok.batch_decode(gen, skip_special_tokens=True))
        return out, seconds


def translate_fragments(nllb, rows, src, tgt):
    """Frozen variant: raw fragments of multi-segment items, length-descending (chars), batch 32.
    Returns {sentence_id: [fragment translations]} for multi-segment items only."""
    frags, owners = [], []
    for r in rows:
        if len(r['source_segments']) > 1:
            for k, seg in enumerate(r['source_segments']):
                frags.append(seg)
                owners.append((r['sentence_id'], k))
    if not frags:
        return {}, 0.0, 0
    order = sorted(range(len(frags)), key=lambda i: -len(frags[i]))  # stable sort: ties keep sentence order
    out, seconds = nllb.translate([frags[i] for i in order], src, tgt, batch=FROZEN_VARIANT['batch'])
    hyps = [None] * len(frags)
    for i, h in zip(order, out):
        hyps[i] = h
    pieces = {}
    for (sid, _k), h in zip(owners, hyps):
        pieces.setdefault(sid, []).append(h)
    return pieces, seconds, len(frags)


# ------------------------------------------------------------------ gate 2 (GPU, dev)
def audit_dev_generation(root, state, token, unsplit_check=True):
    g1 = json.loads((state / 'gate_dev_segmentation.json').read_text())
    require(g1['passed'] and g1['code_sha256'] == code_hashes(), 'Run verify-dev-segmentation with this exact code first.')
    dev = load_dev(root)
    join_exact = join_total = 0
    for d in dev:
        for r in dev[d]['sentence_split']:
            if len(r['source_segments']) > 1:
                join_total += 1
                join_exact += join_fragments(r['segment_translations']) == r['nllb_translation']
    single_reuse = sum(a['nllb_translation'] == b['nllb_translation']
                       for d in dev for a, b in zip(dev[d]['sentence_split'], dev[d]['unsplit_control'])
                       if len(a['source_segments']) == 1)
    single_total = sum(len(a['source_segments']) == 1 for d in dev for a in dev[d]['sentence_split'])
    nllb = NLLB(token)
    runs, per_dir = [], {}
    for rep in range(2):
        allp = {}
        for src, tgt in DIRECTIONS:
            d = f'{src}->{tgt}'
            pieces, secs, nfr = translate_fragments(nllb, dev[d]['sentence_split'], src, tgt)
            allp[d] = pieces
            if rep == 0:
                per_dir[d] = dict(fragments=nfr, seconds=secs)
        runs.append(allp)
    deterministic = runs[0] == runs[1]
    items = exact = frag_total = frag_exact = 0
    diffs = []
    for src, tgt in DIRECTIONS:
        d = f'{src}->{tgt}'
        ex = 0
        for r in dev[d]['sentence_split']:
            if len(r['source_segments']) == 1:
                continue
            reg = runs[0][d][r['sentence_id']]
            items += 1
            ok = join_fragments(reg) == r['nllb_translation']
            exact += ok
            ex += ok
            for k, (a, b) in enumerate(zip(r['segment_translations'], reg)):
                frag_total += 1
                frag_exact += a == b
                if a != b:
                    diffs.append(dict(direction=d, sentence_id=r['sentence_id'], fragment=k,
                                      n_fragments=len(reg), saved_chars=len(a), regenerated_chars=len(b),
                                      char_edit_distance=lev(a, b),
                                      word_count_change=len(b.split()) - len(a.split())))
        per_dir[d]['multi_items_exact'] = ex
    unsplit = None
    if unsplit_check:
        unsplit = {}
        for src, tgt in DIRECTIONS:
            d = f'{src}->{tgt}'
            rows = dev[d]['unsplit_control']
            hyps, secs = nllb.translate([r['source_text'] for r in rows], src, tgt)
            unsplit[d] = dict(exact=sum(h == r['nllb_translation'] for h, r in zip(hyps, rows)), n=len(rows),
                              seconds=secs)
    agreement = exact / items if items else 0.0
    checks = dict(join_rule_exact=join_exact == join_total, single_segment_reuse_exact=single_reuse == single_total,
                  deterministic_within_environment=deterministic,
                  split_agreement_at_least_95pct=agreement >= MIN_DEV_SPLIT_AGREEMENT)
    eds = sorted(x['char_edit_distance'] for x in diffs)
    gate = dict(gate='dev_generation_audit', passed=all(checks.values()), checks=checks,
                frozen_variant=FROZEN_VARIANT, measured_variants_dev=MEASURED_VARIANTS_DEV,
                join_rule=dict(exact=join_exact, total=join_total),
                single_segment_reuse=dict(exact=single_reuse, total=single_total),
                multi_items=dict(exact=exact, total=items, agreement=agreement),
                fragments=dict(exact=frag_exact, total=frag_total),
                differing_fragments=dict(count=len(diffs), char_edit_distance_median=eds[len(eds) // 2] if eds else 0,
                                         char_edit_distance_max=eds[-1] if eds else 0, items=diffs),
                per_direction=per_dir, unsplit_regeneration=unsplit,
                criterion_note='Exact translation equality was the initial gate; it is unattainable here (unbatched '
                               'decoding also differs), so the recorded criterion is: exact segmentation, exact join '
                               'rule, deterministic re-run, and >=95% exact agreement on dev multi-segment items, with '
                               'all residual differences reported. Decision recorded 23 Oct 2026 for PI review.',
                environment=env_info(), decode=DECODE, code_sha256=code_hashes(),
                created_utc=datetime.now(timezone.utc).isoformat())
    wjson(state / 'gate_dev_generation.json', gate)
    print(json.dumps({k: gate[k] for k in ['passed', 'checks', 'join_rule', 'single_segment_reuse', 'multi_items',
                                           'fragments', 'unsplit_regeneration']}, indent=1))
    print('differing fragments:', len(diffs), '| char edit distance median', gate['differing_fragments']['char_edit_distance_median'],
          'max', gate['differing_fragments']['char_edit_distance_max'])
    require(gate['passed'], 'Dev generation audit failed: ' + ', '.join(k for k, v in checks.items() if not v))


# ------------------------------------------------------------------ devtest (after freeze)
def load_devtest_archive(root):
    manifest = json.loads((root / 'outputs/logs/data_manifest.json').read_text())
    require(manifest['revision'] == '5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06', 'FLORES+ revision differs.')
    arch, files = {}, {}
    for src, tgt in DIRECTIONS:
        p = root / f'outputs/generations/baselines/nllb3.3b_{src}_{tgt}_devtest.jsonl'
        files[p.name] = fsha(p)
        rows = sorted(rjsonl(p), key=lambda r: r['sentence_id'])
        require(len(rows) == 1012 and len({r['sentence_id'] for r in rows}) == 1012, 'Phase 2 devtest archive incomplete.')
        require(all(isinstance(r['nllb_translation'], str) and r['nllb_translation'].strip() for r in rows),
                'Empty archived translation.')
        arch[f'{src}->{tgt}'] = rows
    texts = {}
    for d, rows in arch.items():
        s, t = d.split('->')
        for lang, field in [(s, 'source_text'), (t, 'reference_text')]:
            texts.setdefault(lang, set()).add('\n'.join(r[field] for r in rows))
    for lang, blobs in texts.items():
        require(len(blobs) == 1, 'Devtest text differs across directions for ' + lang)
        require(hashlib.sha256(next(iter(blobs)).encode('utf-8')).hexdigest() ==
                manifest['splits'][f'devtest/{lang}']['sha256'], 'Devtest checksum differs from Phase 2 manifest: ' + lang)
    return arch, files


def generate_devtest(root, state, freeze_path, token, unsplit_check=True):
    freeze = json.loads(Path(freeze_path).read_text())
    require(freeze.get('freeze_declared') is True, 'Protocol freeze must be declared before devtest generation.')
    g1 = json.loads((state / 'gate_dev_segmentation.json').read_text())
    g2 = json.loads((state / 'gate_dev_generation.json').read_text())
    require(g1['passed'] and g2['passed'], 'Dev gates must pass first.')
    require(g1['code_sha256'] == g2['code_sha256'] == code_hashes() == freeze['baseline']['code_sha256'],
            'Splitter/generator code differs from the frozen and gated code.')
    require(freeze['baseline']['fragment_variant'] == FROZEN_VARIANT, 'Fragment variant differs from freeze.')
    arch, arch_files = load_devtest_archive(root)
    require(arch_files == freeze['baseline']['phase2_devtest_unsplit_sha256'], 'Phase 2 devtest archive differs from freeze.')
    spec = dict(stage='phase4_devtest_baseline', split='devtest', model=CKPT, revision=NLLB_REV, precision='float16',
                seed=42, decode=DECODE, truncation=False, fragment_variant=FROZEN_VARIANT,
                single_segment_rule='reuse checksum-locked Phase 2 unsplit devtest hypothesis',
                splitter=dict(version=S.SPLITTER_VERSION, pysbd=S.PYSBD_VERSION, rule_language=S.RULE_LANGUAGE,
                              patterns=S.PATTERNS),
                phase2_devtest_unsplit_sha256=arch_files, code_sha256=code_hashes(), freeze_sha256=fsha(freeze_path),
                environment=g2['environment'])
    run_sha = digest(spec)
    out = root / 'outputs/generations/baselines' / ('phase4_devtest_' + run_sha[:16])
    out.mkdir(parents=True, exist_ok=True)
    wjson(out / 'run_spec.json', spec)
    nllb = NLLB(token)
    summary = dict(run_spec_sha256=run_sha, directions={})
    for src, tgt in DIRECTIONS:
        d = f'{src}->{tgt}'
        rows = arch[d]
        seg_rows = [dict(sentence_id=r['sentence_id'], source_segments=S.segment(r['source_text'], src)) for r in rows]
        pieces, t_frag, n_frag = translate_fragments(nllb, seg_rows, src, tgt)
        regen = None
        if unsplit_check:
            hyps, t_uns = nllb.translate([r['source_text'] for r in rows], src, tgt)
            regen = dict(exact_vs_archive=sum(h == r['nllb_translation'] for h, r in zip(hyps, rows)), n=1012,
                         seconds=t_uns)
        unsplit, split = [], []
        for r, sr in zip(rows, seg_rows):
            sid = r['sentence_id']
            common = dict(split='devtest', direction=d, run_spec_sha256=run_sha, sentence_id=sid,
                          source_text=r['source_text'], reference_text=r['reference_text'])
            unsplit.append(dict(common, condition='unsplit_control', nllb_translation=r['nllb_translation'],
                                provenance='phase2_archive'))
            multi = len(sr['source_segments']) > 1
            split.append(dict(common, condition='sentence_split',
                              nllb_translation=join_fragments(pieces[sid]) if multi else r['nllb_translation'],
                              source_segments=sr['source_segments'], input_segment_count=len(sr['source_segments']),
                              segment_translations=pieces[sid] if multi else None, reused_unsplit=not multi))
        require(all(''.join(x['source_segments']) == x['source_text'] for x in split), 'Lossless segmentation violated.')
        fu = out / f'nllb3.3b_{src}_{tgt}_devtest_unsplit_control.jsonl'
        fs = out / f'nllb3.3b_{src}_{tgt}_devtest_sentence_split.jsonl'
        wjsonl(fu, unsplit)
        wjsonl(fs, split)
        summary['directions'][d] = dict(rows=1012, multi_segment_items=sum(len(x['source_segments']) > 1 for x in seg_rows),
                                        fragments_translated=n_frag, fragment_inference_seconds=t_frag,
                                        split_differs_from_unsplit=sum(a['nllb_translation'] != b['nllb_translation']
                                                                       for a, b in zip(unsplit, split)),
                                        unsplit_regeneration=regen,
                                        file_sha256={fu.name: fsha(fu), fs.name: fsha(fs)})
        print(d, json.dumps(summary['directions'][d]), flush=True)
    summary.update(scored=False, created_utc=datetime.now(timezone.utc).isoformat())
    wjson(out / 'generation_summary.json', summary)
    wjson(state / 'devtest_baseline_latest.json', dict(run_dir=str(out), run_spec_sha256=run_sha))
    print('DEVTEST S0 COMPLETE (generated, not scored):', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['verify-dev-segmentation', 'audit-dev-generation', 'devtest'], required=True)
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--freeze', default=None)
    ap.add_argument('--skip-unsplit-regeneration', action='store_true')
    a = ap.parse_args()
    root = Path(a.root)
    state = root / 'outputs/phase4'
    state.mkdir(parents=True, exist_ok=True)
    token = os.environ.get('HF_TOKEN')
    if a.stage == 'verify-dev-segmentation':
        verify_dev_segmentation(root, state)
    elif a.stage == 'audit-dev-generation':
        audit_dev_generation(root, state, token, not a.skip_unsplit_regeneration)
    else:
        require(a.freeze, '--freeze is required for devtest generation.')
        generate_devtest(root, state, a.freeze, token, not a.skip_unsplit_regeneration)


if __name__ == '__main__':
    main()
