"""Manuscript audit (7.txt). Draft mode: evidence-linked development claims, citations, inputs,
RQs identical to the frozen protocol text, ICAI boundary, no novelty claims for shared components.
Final mode (--final --phase5-results main_results.json): additionally no \\pending markers, \\finaltrue,
and every generated table/macro byte-identical to a fresh regeneration from the Phase 5 results.
Not a parser that certifies every number in arbitrary prose."""
import argparse
import csv
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper'
EVIDENCE = ROOT / 'docs/phase3/evidence/pilot'
sys.path[:0] = [str(ROOT / 'src' / 'freeze'), str(ROOT / 'src' / 'evaluation'), str(ROOT / 'src' / 'common'),
                str(ROOT / 'src' / 'post_editing')]


def require(c, m):
    if not c:
        raise SystemExit('AUDIT FAIL: ' + m)


def strip_comments(t):
    return re.sub(r'(?<!\\)%.*', '', t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--phase5-results', default=None)
    a = ap.parse_args()
    summary = list(csv.DictReader((EVIDENCE / 'pilot_condition_results.csv').open()))
    for claim in json.loads((PAPER / 'claims_manifest.json').read_text())['claims']:
        rows = [r for r in summary if all(r[k] == v for k, v in claim['condition'].items())]
        require(bool(rows), 'missing evidence ' + claim['id'])
        value = sum(float(r[claim['metric']]) for r in rows) if claim.get('aggregation') == 'sum' else float(rows[0][claim['metric']])
        require(format(value, claim['format']) == claim['rendered'], 'claim value differs ' + claim['id'])
        for loc in claim['locations']:
            require(claim['rendered'] in (PAPER / loc).read_text(), f'claim {claim["id"]} not in {loc}')

    tex = {p: strip_comments(p.read_text()) for p in PAPER.rglob('*.tex') if 'legacy_dev' not in p.parts}
    allsrc = '\n'.join(tex.values())
    bib = (PAPER / 'references.bib').read_text()
    keys = re.findall(r'@\w+\s*\{\s*([^,\s]+)', bib)
    require(len(keys) == len(set(keys)), 'duplicate bib keys')
    cited = {k.strip() for v in re.findall(r'\\cite\w*\{([^}]+)\}', allsrc) for k in v.split(',')}
    require(not cited - set(keys), f'unresolved citations {cited - set(keys)}')
    for p, t in tex.items():
        for target in re.findall(r'\\input\{([^}]+)\}', t):
            if not target.startswith('generated/'):
                require((PAPER / (target + '.tex')).exists(), 'missing input ' + target)

    import build_freeze_manifest as F
    intro = (PAPER / 'sections/01_introduction.tex').read_text()
    for rq, text in F.RESEARCH_QUESTIONS.items():
        require(f'\\textbf{{{rq}:}} {text}' in intro, f'{rq} text differs from the frozen protocol')
    require(len(re.findall(r'\\textbf\{RQ\d:\}', allsrc)) == 4, 'RQs must be defined exactly once')
    require('ahmadnia2026icai' in intro and 'ahmadnia2026icai' in (PAPER / 'sections/02_related_work.tex').read_text(),
            'ICAI must be cited in the introduction and related work')
    require('do not claim either as a contribution' in intro, 'ICAI contribution boundary sentence missing')
    bad = re.findall(r'(?i)\b(novel|we propose|first (?:hybrid|retrieval|training-free)|state-of-the-art)\b', allsrc)
    require(not bad, f'novelty language found: {bad}')
    require('development evidence' in (PAPER / 'sections/04_experimental_setup.tex').read_text(),
            'pilot material must be labelled as development evidence')
    pend = sum(t.count('\\pending{') for t in tex.values()) - 1  # minus the macro definition
    main_tex = (PAPER / 'conference_101719.tex').read_text()
    if a.final:
        require(pend == 0, f'{pend} \\pending markers remain')
        require('\\finaltrue' in main_tex.split('\\begin{document}')[0], 'set \\finaltrue for submission')
        require(a.phase5_results, '--phase5-results is required in final mode')
        import evaluate_main_experiments as EV
        res = json.loads(Path(a.phase5_results).read_text())
        with tempfile.TemporaryDirectory() as d:
            EV.write_tables(res, d)
            for f in Path(d).iterdir():
                require((PAPER / 'generated' / f.name).read_text() == f.read_text(), 'generated file differs: ' + f.name)
    print(f'PASS ({"final" if a.final else "draft"}): {len(cited)} citations, RQs match freeze, ICAI boundary, '
          f'no novelty claims, dev claims verified; {max(pend, 0)} pending markers')


if __name__ == '__main__':
    main()
