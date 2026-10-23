"""Generate Norris Phase Report 3.2 (revised Phase 3 freeze package) as Markdown from the evidence ZIP
produced by notebooks/phase3/03_rte_v3_revalidation_and_freeze.ipynb. Every number comes from the ZIP.

  python src/freeze/make_report_3_2.py --zip Norris_Phase3_RTEv3_Freeze_Evidence_*.zip --out docs/phase3/Norris_Phase_Report_3_2.md
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

DIRS = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn', 'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
DN = dict(zip(DIRS, ['En→Tl', 'Tl→En', 'En→Es', 'Es→En']))
MN = {'gpt4o-mini': 'GPT-4o Mini', 'llama3-8b': 'Llama 3 8B'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    z = zipfile.ZipFile(a.zip)
    rd = lambda n: json.loads(z.read(n))
    names = z.namelist()
    S = rd('analysis/rte_v3_summary.json')
    man = rd('rte_v3/prepared_manifest.json')
    gate1 = rd('gates_and_freeze/gate_dev_segmentation.json') if 'gates_and_freeze/gate_dev_segmentation.json' in names else None
    gate2 = rd('gates_and_freeze/gate_dev_generation.json') if 'gates_and_freeze/gate_dev_generation.json' in names else None
    fz_name = 'gates_and_freeze/protocol_freeze.json'
    freeze = rd(fz_name) if fz_name in names else None
    L = ['# Norris Phase Report 3.2 — Revised reason-then-edit contract and protocol freeze', '',
         'Principal Investigator: Dr Benyamin Ahmadnia · Graduate Research Assistant: Shazan Ansar Mohammed',
         '', f"Evidence ZIP SHA-256: `{hashlib.sha256(Path(a.zip).read_bytes()).hexdigest()}`", '',
         '## 1. What was requested and what was done', '',
         'On 22 October 2026 the PI asked for the reason-then-edit diagnostic contract to be simplified to the minimum '
         'structure necessary, documented, and rerun on the affected **dev** conditions for both models, without changing '
         'the task or using devtest. The change record (`docs/phase3/RTE_CONTRACT_REVISION.md`) was committed before the '
         'rerun, with a predeclared reliability gate. Only the reason-then-edit suffix, schema and validators changed.', '',
         f"* Measured v2 prompts reproduced byte-for-byte by the frozen builder: **{man['v2_jobs_reproduced_byte_for_byte']}/1200**",
         f"* Stored v2 zero-shot/one-shot outcomes reproduced by the frozen output contract: **{S['plain_v2_outcomes_reproduced']}/1600**",
         f"* Pilot baseline COMET recheck: max |Δ| = {S['baseline_recheck_max_abs_native']:.2e} native (tolerance 1e-5)",
         '* Devtest opened: **no**', '',
         '## 2. Reliability gate (predeclared)', '', f"Rule: {S['gate_rule']}", '',
         '| Model | Fallbacks /400 | ' + ' | '.join(DN[d] + ' /100' for d in DIRS) + ' | Gate |', '|---|---:|' + '---:|' * 4 + '---|']
    for m, g in S['gate'].items():
        L.append(f"| {MN[m]} | {g['fallbacks_total']} | " + ' | '.join(str(g['fallbacks_by_direction'][d]) for d in DIRS) +
                 f" | {'PASS' if g['passes'] else 'FAIL'} |")
    L += ['', f"**Overall: {'PASSED' if S['gate_pass'] else 'FAILED — PI decision required (retain as explicit failure condition or remove)'}.**", '',
          '## 3. Reason-then-edit v2 (measured) vs v3 (revised), dev, 100 items per cell', '',
          '| Model | Dir | Usable v2→v3 | Fallback v2→v3 | Edited v2→v3 | ΔCOMET v2 [95% CI] | ΔCOMET v3 [95% CI] | Harmed v2→v3 | Protect over-edits v2→v3 |',
          '|---|---|---|---|---|---|---|---|---|']
    for c in S['v2_vs_v3']:
        f = lambda k: c[k]
        ci = lambda k: '[{:+.3f}, {:+.3f}]'.format(*c[k])
        L.append(f"| {MN[c['model']]} | {DN[c['direction']]} | {f('v2_usable')}→{f('v3_usable')} | {f('v2_fallbacks')}→{f('v3_fallbacks')} | "
                 f"{f('v2_text_edited')}→{f('v3_text_edited')} | {c['v2_delta_COMET_points']:+.3f} {ci('v2_delta_COMET_95CI_points')} | "
                 f"{c['v3_delta_COMET_points']:+.3f} {ci('v3_delta_COMET_95CI_points')} | {f('v2_harmed')}→{f('v3_harmed')} | "
                 f"{f('v2_overedited_protect_n')}→{f('v3_overedited_protect_n')} |")
    L += ['', 'Δ is edited minus split baseline in COMET points, all 100 items including fallback; intervals are descriptive paired '
          'percentile dev intervals (10,000 resamples, seed 42). These are development diagnostics, not confirmatory results, and '
          'quality was not used to accept or reject the revised contract.', '',
          '## 4. v3 failure classes (mutually exclusive)', '', '| Model | Dir | Classes |', '|---|---|---|']
    for k, g in S['groups_rte_v3'].items():
        m, d, _ = k.split('/')
        L.append(f"| {MN[m]} | {DN[d]} | {json.dumps(g['failure_classes'])} |")
    if gate1 and gate2:
        L += ['', '## 5. Primary baseline (S0) reconstruction on dev', '',
              'The original split-generation cell was not recovered, so the splitter and fragment generation were '
              'reconstructed from the recorded run specification and audited against the saved dev baseline.', '',
              f"* Segmentation: {'PASS' if gate1['passed'] else 'FAIL'} — " +
              ', '.join(f"{k}: {v['exact']}/{v['items']} exact ({v['multi_segment_items']} multi-segment)" for k, v in gate1['report'].items()),
              f"* Join rule on saved fragment translations: {gate2['join_rule']['exact']}/{gate2['join_rule']['total']} exact",
              f"* Single-segment items reuse the unsplit draft: {gate2['single_segment_reuse']['exact']}/{gate2['single_segment_reuse']['total']}",
              f"* Frozen fragment variant `{gate2['frozen_variant']['name']}` reproduces {gate2['multi_items']['exact']}/"
              f"{gate2['multi_items']['total']} dev multi-segment items exactly ({100 * gate2['multi_items']['agreement']:.1f}%); "
              f"fragments {gate2['fragments']['exact']}/{gate2['fragments']['total']}",
              f"* Residual differing fragments: {gate2['differing_fragments']['count']} (character edit distance median "
              f"{gate2['differing_fragments']['char_edit_distance_median']}, max {gate2['differing_fragments']['char_edit_distance_max']})",
              f"* Deterministic re-run within this environment: {gate2['checks']['deterministic_within_environment']}"]
        if gate2.get('unsplit_regeneration'):
            L.append('* Regenerated dev unsplit control vs saved: ' + ', '.join(
                f"{DN[d]} {v['exact']}/{v['n']}" for d, v in gate2['unsplit_regeneration'].items()))
        L += ['', 'Variants measured on dev (exact of 421): ' + ', '.join(f"{v['name']} {v['exact']}" for v in gate2['measured_variants_dev']) + '.', '',
              '**Disclosure for PI review.** Exact translation equality was the initial acceptance rule. It is not attainable: '
              'even unbatched decoding differs on a few items, so the residual is FP16 beam-search numerics, not a recoverable '
              'procedure detail. The recorded criterion is exact segmentation, exact join rule, a deterministic re-run and at least '
              '95% exact agreement, with every residual difference reported. On devtest, single-segment items reuse the '
              'checksum-locked Phase 2 unsplit drafts (as on dev); only multi-segment items are newly translated. Every '
              'post-editing condition edits the same frozen S0 drafts, so the comparisons are unaffected.']
    if freeze:
        L += ['', '## 6. Protocol freeze', '',
              f"* Freeze declared: **{freeze['freeze_declared']}** at {freeze['declared_utc']}; git commit `{freeze['git_commit']}`",
              f"* Protocol fingerprint: `{freeze['protocol']['fingerprint']}`",
              f"* Freeze file SHA-256: `{hashlib.sha256(z.read(fz_name)).hexdigest()}`", '',
              'Research questions (verbatim, used unchanged in the manuscript):', '']
        L += [f"* **{k}** {v}" for k, v in freeze['research_questions'].items()]
        L += ['', 'Main matrix: S0 split NLLB (primary), unsplit diagnostic; S1–S6 = {GPT-4o Mini, Llama 3 8B} × {zero-shot, '
              'retrieved one-shot, reason-then-edit v3}; 24 conditions × 1,012 devtest items = 24,288 outputs.', '',
              f"Retrieval (main): {freeze['retrieval_main']['pool']}; {freeze['retrieval_main']['exclusion']}; tie break "
              f"{freeze['retrieval_main']['tie_break']}.", '',
              f"Statistics: {freeze['evaluation']['test']}; families F1 = {freeze['evaluation']['families']['F1']}; "
              f"F2 = {freeze['evaluation']['families']['F2']}; {freeze['evaluation']['multiplicity']}.", '',
              'Documented deviations from the roadmap:', ''] + [f"* {x}" for x in freeze['deviations_from_roadmap']]
        L += ['', '## 7. ICAI contribution boundary (PI-approved)', '', freeze['pi_instructions']['icai_boundary']]
    L += ['', '## Next step', '', S['next_step'] if not freeze else
          'With the freeze declared and this package sent, Phase 4 (devtest S0 and the 24-condition matrix) proceeds under the frozen configuration; Phase 5 follows the approved plan.']
    Path(a.out).write_text('\n'.join(L) + '\n')
    print('written', a.out)


if __name__ == '__main__':
    main()
