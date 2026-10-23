"""End-to-end offline: S0 dev gates -> freeze manifest -> devtest S0 generation bound to that freeze."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests' / 'phase4'), str(ROOT / 'src' / 'freeze'), str(ROOT / 'src' / 'baselines')]
import test_s0_offline as T
import generate_devtest_baseline as G
import build_freeze_manifest as F
import norris_protocol as P


def test_freeze_end_to_end():
    root = Path(tempfile.mkdtemp())
    T.build(root)
    state = root / 'outputs/phase4'
    state.mkdir(parents=True, exist_ok=True)
    G.verify_dev_segmentation(root, state)
    G.audit_dev_generation(root, state, None)
    adir = root / 'rte_analysis'
    gate = {m: dict(fallbacks_total=0, fallbacks_by_direction={d: 0 for d in P.DIRECTION_KEYS}, passes=True) for m in P.MODELS}
    P.atomic_json(adir / 'rte_v3_summary.json', dict(analysis_sha256='a' * 64, gate=gate, gate_pass=True))
    P.atomic_json(root / 'outputs/phase3_post_editing/rte_v3_analysis_latest.json',
                  dict(output_dir=str(adir), analysis_sha256='a' * 64))
    out = root / 'protocol_freeze.json'
    sys.argv = ['x', '--root', str(root), '--git-commit', 'deadbeef', '--declare', '--out', str(out)]
    F.main()
    fz = json.loads(out.read_text())
    assert fz['freeze_declared'] and fz['baseline']['fragment_variant'] == G.FROZEN_VARIANT
    assert len(fz['baseline']['phase2_devtest_unsplit_sha256']) == 4
    assert fz['research_questions']['RQ1'].startswith('How do editing gains')
    G.generate_devtest(root, state, out, None)
    assert (state / 'devtest_baseline_latest.json').exists()
    # refusing an undeclared freeze
    undeclared = dict(fz, freeze_declared=False)
    out2 = root / 'undeclared.json'
    out2.write_text(json.dumps(undeclared))
    try:
        G.generate_devtest(root, state, out2, None)
        raise AssertionError('undeclared freeze must be refused')
    except SystemExit:
        pass


if __name__ == '__main__':
    test_freeze_end_to_end()
    print('PASS test_freeze_end_to_end (gates -> declared freeze -> devtest S0 bound to freeze; undeclared refused)')
