"""Extract a deterministic, rule-based sample of held-out cases for source-based review.

Selection (fixed before any text is read; no cherry-picking):
  per condition (24): A) protect-pool over-edit with the largest COMET loss,
                      B) the largest COMET improvement,
                      C) the lowest-ID digit-loss flag, D) the lowest-ID language-mismatch flag.
Output contains FLORES+ devtest text and model outputs: PRIVATE evidence; never commit or publish.

  python extract_review_cases.py --root /content/drive/MyDrive/norris --eval-dir <outputs/phase5/eval_xxx>
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import norris_protocol as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--eval-dir', required=True)
    a = ap.parse_args()
    root, ev = Path(a.root), Path(a.eval_dir)
    jobs_dir = Path(P.read_json(root / 'outputs/phase4/main_prepared_latest.json')['jobs_dir'])
    gold = {(g['direction'], g['sentence_id']): g for g in P.read_jsonl(jobs_dir / 'gold_devtest.jsonl')}
    seg = {}
    for r in P.read_jsonl(ev / 'segment_scores_numeric.jsonl'):
        seg.setdefault((r['model'], r['strategy'], r['direction']), []).append(r)
    recs = {}
    for m in P.MODELS:
        latest = P.read_json(jobs_dir / f'{m}_latest_run.json')
        gdir = Path(latest.get('generations_dir', jobs_dir / 'generations'))
        for d in P.DIRECTION_KEYS:
            for s in P.STRATEGIES:
                for r in P.read_jsonl(gdir / f'{m}_{s}_{P.SHORT[d]}.jsonl'):
                    recs[(m, s, d, r['sentence_id'])] = r
    cases = []
    for (m, s, d), rows in sorted(seg.items()):
        picks = []
        prot = [r for r in rows if r['pool'] == 'protect' and r['text_edited'] and r['delta_comet_native'] < -0.02]
        if prot:
            picks.append(('A_largest_protect_overedit', min(prot, key=lambda r: (r['delta_comet_native'], r['sentence_id']))))
        picks.append(('B_largest_improvement', max(rows, key=lambda r: (r['delta_comet_native'], -r['sentence_id']))))
        dig = sorted((r for r in rows if r['digit_loss_flag']), key=lambda r: r['sentence_id'])
        if dig:
            picks.append(('C_first_digit_loss', dig[0]))
        lang = sorted((r for r in rows if r['language_mismatch_flag']), key=lambda r: r['sentence_id'])
        if lang:
            picks.append(('D_first_language_mismatch', lang[0]))
        for rule, r in picks:
            g, rec = gold[(d, r['sentence_id'])], recs[(m, s, d, r['sentence_id'])]
            cases.append(dict(rule=rule, model=m, strategy=s, direction=d, sentence_id=r['sentence_id'],
                              delta_comet_points=100 * r['delta_comet_native'],
                              baseline_comet_points=100 * r['baseline_comet_native'],
                              source=g['source_text'], s0_draft=g['baseline_translation'],
                              edited=rec['edited_translation'], reference=g['reference_text'],
                              diagnosis=rec.get('diagnosis'),
                              flags={k: r[k] for k in ['digit_change_flag', 'digit_loss_flag', 'language_mismatch_flag',
                                                       'length_anomaly_flag', 'sentence_drop_flag']},
                              newly_absent_capitalized=r.get('newly_absent_capitalized_source_tokens')))
    out = ev / 'review_cases_PRIVATE.json'
    P.atomic_json(out, dict(selection_rule=__doc__.split('Output')[0].strip(), n=len(cases), cases=cases))
    print('cases:', len(cases), '->', out, '(PRIVATE: contains benchmark text)')


if __name__ == '__main__':
    main()
