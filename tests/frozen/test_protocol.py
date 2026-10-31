"""Frozen protocol checks (no GPU, no API).

1. The generic builder reproduces the published candidate builder (pilot_common v1) byte-for-byte
   when given the v1 suffix/schema, proving assembly is unchanged; only suffix/schema vary.
2. Plain-strategy extraction matches the candidate extractor on valid and invalid fixtures.
3. The v3 reason-then-edit contract: accepts the minimal structure, rejects only structural failures,
   and accepts every pattern that failed the v2 diagnostic validators.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src' / 'common'), str(ROOT / 'src' / 'phase3' / 'post_editing')]
import norris_protocol as P
import pilot_common as V1

Q = dict(sentence_id=7, src='eng_Latn', tgt='tgl_Latn', source_text='The cat sat. It slept.',
         draft='Umupo ang pusa. Natulog ito.')
EX = dict(sentence_id=9, src='eng_Latn', tgt='tgl_Latn', source_text='A dog ran.', draft='Tumakbo ang aso.',
          reference_text='Tumakbo ang isang aso.')


def test_builder_matches_published_candidate_builder():
    for strategy in V1.STRATEGIES:
        ex = EX if strategy == 'knn-oneshot' else None
        v1_suffix = V1.REASON_SUFFIX if strategy == 'reason-then-edit' else V1.PLAIN_SUFFIX
        mine = P.build_messages_with(Q, strategy, ex, v1_suffix, V1.schema_for(strategy))
        mine[0]['content'] = mine[0]['content'].replace(P.SYSTEM_BASE, V1.SYSTEM_BASE, 1)
        assert mine == V1.build_messages(Q, strategy, ex), strategy


def test_plain_extraction_matches_candidate():
    cases = [('{"edited_translation": " Umupo ang pusa. "}', 'stop'),
             ('{"edited_translation": ""}', 'stop'), ('{"edited_translation": "x", "extra": 1}', 'stop'),
             ('{"edited_translation": "x", "edited_translation": "y"}', 'stop'), ('not json', 'stop'),
             ('{"edited_translation": "x"}', 'length'), ('{"edited_translation": 5}', 'stop')]
    for raw, fin in cases:
        for s in ['zero-shot', 'knn-oneshot']:
            a, b = P.extract_response(raw, s, Q['draft'], fin), V1.extract_response(raw, s, Q['draft'], fin)
            for k in ['json_parse_success', 'schema_valid', 'usable', 'edited_translation', 'fallback_used']:
                assert a[k] == b[k], (raw, s, k)


def rte(obj, fin='stop'):
    raw = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return P.extract_response(raw, 'reason-then-edit', Q['draft'], fin)


def test_rte_v3_accepts_minimal_structure():
    r = rte({'diagnosis': 'No source-supported correction needed.', 'edited_translation': Q['draft']})
    assert r['usable'] and not r['fallback_used'] and r['diagnosis'].startswith('No source')
    long_note = ' '.join(['word'] * 60)   # v2 rejected notes > 25 words; v3 does not
    assert rte({'diagnosis': long_note, 'edited_translation': 'Umupo ang pusa. Natulog ito.'})['usable']


def test_rte_v3_rejects_structural_failures_only():
    bad = [{'edited_translation': 'x', 'diagnosis': 'd'},               # wrong order
           {'diagnosis': '', 'edited_translation': 'x'},                # empty diagnosis
           {'diagnosis': 'd', 'edited_translation': '  '},              # empty translation
           {'diagnosis': 'd', 'edited_translation': 'x', 'notes': 'y'}, # extra key
           {'diagnosis': ['d'], 'edited_translation': 'x'}]             # wrong type
    for obj in bad:
        r = rte(obj)
        assert not r['usable'] and r['fallback_used'] and r['edited_translation'] == Q['draft'], obj
    assert not rte('{"diagnosis": "d", "diagnosis": "e", "edited_translation": "x"}')['usable']
    assert not rte({'diagnosis': 'd', 'edited_translation': 'x'}, fin='length')['usable']
    assert not rte('{"diagnosis": "d", "edited_tr')['json_parse_success']


def test_v2_failure_patterns_are_not_v3_failures():
    """v2 categories are gone, so repeated categories / NONE mixing / note length cannot occur as failures."""
    schema = P.schema_for('reason-then-edit')
    assert list(schema['properties']) == ['diagnosis', 'edited_translation']
    assert schema['additionalProperties'] is False and schema['required'] == ['diagnosis', 'edited_translation']
    assert 'MISTRANSLATION' not in P.REASON_SUFFIX_V3 and 'NONE' not in P.REASON_SUFFIX_V3


def test_reference_never_in_query_and_no_self_retrieval():
    for bad_q, ex in [(dict(Q, reference_text='leak'), None), (Q, dict(EX, sentence_id=7))]:
        try:
            P.build_frozen_messages(bad_q, 'knn-oneshot' if ex else 'zero-shot', ex)
            raise AssertionError('should fail')
        except ValueError:
            pass
    # cross-partition IDs may coincide (dev 7 vs devtest 7) and must NOT be treated as self-retrieval
    q = dict(Q, partition='devtest')
    msgs = P.build_frozen_messages(q, 'knn-oneshot', dict(EX, sentence_id=7, partition='dev'))
    assert len(msgs) == 4 and 'Tumakbo ang isang aso.' in msgs[2]['content']
    assert 'reference' not in msgs[-1]['content']


def test_fingerprint_stable():
    assert P.protocol_fingerprint() == P.protocol_fingerprint()


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
