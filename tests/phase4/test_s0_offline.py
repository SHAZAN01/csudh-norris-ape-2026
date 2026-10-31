"""Offline test of the S0 pipeline: segmentation gate, generation audit, and devtest generation,
with a deterministic fake NLLB (no GPU). Verifies gate logic, join rule, reuse of archived unsplit
drafts for single-segment items, lossless segmentation, freeze binding and checksums."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'baselines'))
import generate_devtest_baseline as G
import norris_splitter as S


class FakeNLLB:
    def __init__(self, token=None):
        pass

    def translate(self, texts, src, tgt, batch=32):
        return [f'[{tgt}] ' + t.strip()[::-1] for t in texts], 0.01


G.NLLB = FakeNLLB
SRC = {'eng_Latn': ['The cat sat. It slept.', 'Dr. Smith came at 8 p.m. Monday.', 'One sentence only here.'],
       'tgl_Latn': ['Umupo ang pusa. Natulog ito.', 'Prutas, gulay, atbp. ay mura.', 'Isang pangungusap lang.'],
       'spa_Latn': ['El gato se sentó. Durmió.', 'El Sr. Pérez Jr. llegó.', 'Solo una oración aquí.']}


def build(root, n_dev=997, n_test=1012):
    run = root / G.DEV_RUN
    summ = dict(run_spec_sha256=G.DEV_RUN_SHA, directions={})
    for src, tgt in G.DIRECTIONS:
        d = f'{src}->{tgt}'
        split, uns = [], []
        for sid in range(1, n_dev + 1):
            text = SRC[src][sid % 3]
            segs = S.segment(text, src)
            ctrl = f'[{tgt}] ' + text.strip()[::-1]
            st = [f'[{tgt}] ' + s.strip()[::-1] for s in segs] if len(segs) > 1 else None
            if st and sid == 9:      # one residual numerical difference in a fragment
                st = [st[0][:-1] + 'X'] + st[1:]
            hyp = G.join_fragments(st) if st else ctrl
            split.append(dict(sentence_id=sid, source_text=text, reference_text='ref', nllb_translation=hyp,
                              source_segments=segs, segment_translations=st, input_segment_count=len(segs)))
            uns.append(dict(sentence_id=sid, source_text=text, reference_text='ref', nllb_translation=ctrl))
        files = {}
        for cond, rows in [('sentence_split', split), ('unsplit_control', uns)]:
            name = f'nllb3.3b_{src}_{tgt}_dev_{cond}.jsonl'
            G.wjsonl(run / name, rows)
            files[name] = G.fsha(run / name)
        summ['directions'][d] = dict(file_sha256=files)
        test = [dict(sentence_id=sid, source_text=SRC[src][sid % 3] + f' #{sid}', reference_text=SRC[tgt][sid % 3] + f' #{sid}',
                     nllb_translation=f'arch {sid}') for sid in range(1, n_test + 1)]
        G.wjsonl(root / f'outputs/generations/baselines/nllb3.3b_{src}_{tgt}_devtest.jsonl', test)
    G.wjson(run / 'generation_summary.json', summ)
    splits = {}
    for lang in SRC:
        text = '\n'.join(SRC[lang][sid % 3] + f' #{sid}' for sid in range(1, n_test + 1))
        splits[f'devtest/{lang}'] = dict(sha256=hashlib.sha256(text.encode()).hexdigest())
    G.wjson(root / 'outputs/logs/data_manifest.json', dict(revision='5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06', splits=splits))


def test_pipeline():
    root = Path(tempfile.mkdtemp())
    build(root)
    state = root / 'outputs/phase4'
    state.mkdir(parents=True, exist_ok=True)
    G.verify_dev_segmentation(root, state)
    G.audit_dev_generation(root, state, None, unsplit_check=True)
    g2 = json.loads((state / 'gate_dev_generation.json').read_text())
    assert g2['passed'] and g2['checks']['deterministic_within_environment']
    assert g2['join_rule']['exact'] == g2['join_rule']['total'] > 0
    assert g2['multi_items']['total'] - g2['multi_items']['exact'] == 4   # sid 9 in each direction
    assert g2['differing_fragments']['count'] == 4 and g2['differing_fragments']['char_edit_distance_max'] == 1
    assert all(v['exact'] == 997 for v in g2['unsplit_regeneration'].values())
    archive = {}
    for src, tgt in G.DIRECTIONS:
        p = root / f'outputs/generations/baselines/nllb3.3b_{src}_{tgt}_devtest.jsonl'
        archive[p.name] = G.fsha(p)
    freeze = root / 'freeze.json'
    freeze.write_text(json.dumps(dict(freeze_declared=True, baseline=dict(code_sha256=G.code_hashes(),
                      fragment_variant=G.FROZEN_VARIANT, phase2_devtest_unsplit_sha256=archive))))
    G.generate_devtest(root, state, freeze, None, unsplit_check=True)
    ptr = json.loads((state / 'devtest_baseline_latest.json').read_text())
    run = Path(ptr['run_dir'])
    summ = json.loads((run / 'generation_summary.json').read_text())
    for src, tgt in G.DIRECTIONS:
        rows = G.rjsonl(run / f'nllb3.3b_{src}_{tgt}_devtest_sentence_split.jsonl')
        assert len(rows) == 1012
        for r in rows:
            assert ''.join(r['source_segments']) == r['source_text']
            if r['input_segment_count'] == 1:
                assert r['nllb_translation'] == f"arch {r['sentence_id']}" and r['reused_unsplit']
            else:
                assert r['nllb_translation'] == G.join_fragments(r['segment_translations'])
        assert summ['directions'][f'{src}->{tgt}']['multi_segment_items'] > 0
    # tampered archive must be refused
    p = root / 'outputs/generations/baselines/nllb3.3b_eng_Latn_tgl_Latn_devtest.jsonl'
    p.write_text(p.read_text().replace('arch 5"', 'arch 5x"'))
    try:
        G.generate_devtest(root, state, freeze, None)
        raise AssertionError('tampered archive must be refused')
    except SystemExit as e:
        assert 'differs from freeze' in str(e)


if __name__ == '__main__':
    test_pipeline()
    print('PASS test_s0_offline (segmentation gate, generation audit, devtest generation, freeze binding, tamper refusal)')
