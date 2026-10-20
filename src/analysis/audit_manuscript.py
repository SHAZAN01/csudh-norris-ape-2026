"""Check evidence-backed claims, numeric tables and draft status without inference.

This is not a parser that verifies every number in arbitrary scientific prose.
Claims in claims_manifest.json and all generated pilot tables are covered.
"""
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper'
EVIDENCE = ROOT / 'docs/phase3/evidence/pilot'


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/update_manuscript_tables.py'),
                    '--check'], check=True)
    summary = list(csv.DictReader((EVIDENCE / 'pilot_condition_results.csv').open()))
    segments = list(csv.DictReader((EVIDENCE / 'pilot_segment_scores.csv').open()))
    require(len(summary) == 24 and len(segments) == 2400, 'Incorrect evidence size')
    groups = defaultdict(list)
    unique = set()
    for row in segments:
        key = (row['model'], row['strategy'], row['direction'])
        identity = key + (row['sentence_id'],)
        require(identity not in unique, 'Duplicate segment identity')
        unique.add(identity)
        groups[key].append(row)
        delta = float(row['comet_native']) - float(row['baseline_comet_native'])
        require(abs(delta - float(row['delta_comet_native'])) < 1e-12,
                'Segment delta does not match scores')
        if row['fallback_used'] == 'True':
            require(row['usable'] == 'False' and row['text_edited'] == 'False'
                    and abs(delta) < 1e-12, 'Fallback changed baseline output')
    require(len(groups) == 24, 'Incorrect condition matrix')
    id_sets = []
    for row in summary:
        key = (row['model'], row['strategy'], row['direction'])
        group = groups[key]
        require(len(group) == 100, f'Incomplete condition: {key}')
        id_sets.append({r['sentence_id'] for r in group})
        for field, output in [('comet_native', 'COMET_points'),
                              ('baseline_comet_native', 'baseline_COMET_points'),
                              ('delta_comet_native', 'delta_COMET_points')]:
            mean = 100 * sum(float(r[field]) for r in group) / 100
            require(abs(mean - float(row[output])) < 1e-10,
                    f'Condition mean mismatch: {key}/{output}')
        for field, output in [('fallback_used', 'fallbacks'), ('usable', 'usable'),
                              ('text_edited', 'text_edited')]:
            require(sum(r[field] == 'True' for r in group) == int(row[output]),
                    f'Condition count mismatch: {key}/{output}')
    require(all(ids == id_sets[0] for ids in id_sets), 'Aligned pilot IDs differ')

    for claim in json.loads((PAPER / 'claims_manifest.json').read_text())['claims']:
        matching = [r for r in summary if all(r[k] == v for k, v in claim['condition'].items())]
        require(bool(matching), f'Missing claim evidence: {claim["id"]}')
        if claim.get('aggregation') == 'sum':
            value = sum(float(r[claim['metric']]) for r in matching)
        else:
            require(len(matching) == 1, f'Ambiguous claim: {claim["id"]}')
            raw = matching[0][claim['metric']]
            value = json.loads(raw)[claim['index']] if 'index' in claim else float(raw)
        value *= claim.get('scale', 1)
        require(claim['rendered'] == format(value, claim['format']),
                f'Claim rounding differs: {claim["id"]}')
        for location in claim['locations']:
            require(claim['rendered'] in (PAPER / location).read_text(),
                    f'Missing claim in {location}: {claim["id"]}')

    bibliography = (PAPER / 'references.bib').read_text()
    keys = re.findall(r'@\w+\s*\{\s*([^,\s]+)', bibliography)
    require(len(keys) == len(set(keys)), 'Duplicate bibliography keys')
    sources = '\n'.join(f.read_text() for f in PAPER.rglob('*.tex'))
    cited = {key.strip() for value in re.findall(r'\\cite\w*\{([^}]+)\}', sources)
             for key in value.split(',')}
    require(not (cited - set(keys)), f'Unresolved citations: {cited - set(keys)}')
    for file in PAPER.rglob('*.tex'):
        for target in re.findall(r'\\input\{([^}]+)\}', file.read_text()):
            require((PAPER / (target + '.tex')).exists(), f'Missing input: {target}')
    config = json.loads((ROOT / 'config/phase3/Reviewed_Candidate_Configuration.json').read_text())
    status = json.loads((ROOT / 'config/phase3/status.json').read_text())
    require(config['freeze_declared'] is False and status['protocol_freeze'] is False,
            'Development manuscript unexpectedly has a frozen protocol')
    require(status['main_devtest_execution_started'] is False,
            'Development draft status inconsistent with main execution')
    require('Pilot results only' in (PAPER / 'conference_101719.tex').read_text(),
            'Development warning missing')
    print(f'PASS: 2400 segments, 24 summaries, aligned IDs, table bytes, '
          f'evidence-linked claims, {len(cited)} citations and unfrozen status.')


if __name__ == '__main__':
    main()
