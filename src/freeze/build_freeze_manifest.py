"""Build the Norris protocol freeze manifest (Phase 3 close-out).

Reads dev evidence only (RTE v3 gate, splitter dev gates). Declares the freeze only if
the reason-then-edit reliability gate passed, or the PI's recorded disposition is
supplied. Writes config/frozen/protocol_freeze.json (repo) and a Drive copy.

  python src/freeze/build_freeze_manifest.py --root /content/drive/MyDrive/norris \
      --repo /content/csudh-norris-ape-2026 --git-commit <sha> --declare
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / 'src' / 'common'), str(REPO / 'src' / 'post_editing'), str(REPO / 'src' / 'evaluation')]
import norris_protocol as P  # noqa: E402

RESEARCH_QUESTIONS = {
    'RQ1': 'How do editing gains and harms differ between the Tagalog and Spanish pairs, conditional on baseline quality?',
    'RQ2': 'How do the three prompting strategies compare within each model and direction?',
    'RQ3': 'When do editors change already strong drafts and degrade their measured quality or source fidelity?',
    'RQ4': 'How do effects differ between the two directions of a language pair?',
}
RQ_ANALYSIS = {
    'RQ1': 'F1 estimates and intervals by pair; pool-stratified mean deltas (protect >=.90, middle, improve <.80). '
           'Descriptive comparison of pairs; no confirmatory test of a pair difference; resource level is confounded '
           'with language, direction, domain and baseline quality.',
    'RQ2': 'F2 confirmatory strategy family (24 tests, Holm).',
    'RQ3': 'Protect-pool over-editing (primary threshold .02; sensitivity .01/.05), overall harm, preservation '
           'screens (digit, capitalized token, language ID, length ratio, sentence count). Screens are not gold errors.',
    'RQ4': 'F1 estimates and intervals for the two directions of each pair; descriptive, no confirmatory direction '
           'test; translationese in reverse directions disclosed.',
}
FROZEN_CODE = ['src/common/norris_protocol.py', 'src/post_editing/run_main_experiments.py',
               'src/post_editing/prepare_main_jobs.py', 'src/baselines/norris_splitter.py',
               'src/baselines/generate_devtest_baseline.py', 'src/evaluation/norris_stats.py',
               'src/evaluation/evaluate_main_experiments.py', 'src/phase3/post_editing/analyze_pilots.py',
               'src/phase3/post_editing/baseline_io.py']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/content/drive/MyDrive/norris')
    ap.add_argument('--git-commit', required=True)
    ap.add_argument('--declare', action='store_true')
    ap.add_argument('--rte-disposition', choices=['gate_passed', 'retain_as_explicit_failure'], default='gate_passed')
    ap.add_argument('--pi-decision-note', default=None)
    ap.add_argument('--out', default=str(REPO / 'config' / 'frozen' / 'protocol_freeze.json'))
    args = ap.parse_args()
    root = Path(args.root)
    import run_main_experiments as E
    import norris_stats as ST
    import evaluate_main_experiments as EV

    rte_ptr = P.read_json(root / 'outputs/phase3_post_editing/rte_v3_analysis_latest.json')
    rte = P.read_json(Path(rte_ptr['output_dir']) / 'rte_v3_summary.json')
    P.require(rte['analysis_sha256'] == rte_ptr['analysis_sha256'], 'RTE v3 analysis pointer differs.')
    if args.rte_disposition == 'gate_passed':
        P.require(rte['gate_pass'], 'RTE v3 reliability gate FAILED. Do not freeze; bring the evidence to the PI.')
    else:
        P.require(bool(args.pi_decision_note), 'A recorded PI decision note is required for this disposition.')
    g1 = P.read_json(root / 'outputs/phase4/gate_dev_segmentation.json')
    g2 = P.read_json(root / 'outputs/phase4/gate_dev_generation.json')
    P.require(g1['passed'] and g2['passed'] and g1['code_sha256'] == g2['code_sha256'], 'Splitter dev gates not passed.')
    P.require(g2.get('gate') == 'dev_generation_audit', 'Rerun the S0 dev audit with the current generator.')
    archive_sha = {}
    for src, tgt in P.DIRECTIONS:  # checksum-lock (not read for scoring) the Phase 2 devtest unsplit archive
        f = root / f'outputs/generations/baselines/nllb3.3b_{src}_{tgt}_devtest.jsonl'
        P.require(f.exists(), 'Missing Phase 2 devtest archive: ' + f.name)
        archive_sha[f.name] = P.file_sha256(f)

    freeze = dict(
        freeze_id='norris_protocol_freeze_v1', freeze_declared=bool(args.declare),
        declared_utc=datetime.now(timezone.utc).isoformat() if args.declare else None,
        git_commit=args.git_commit, devtest_opened_before_freeze=False,
        pi_instructions=dict(date='2026-10-22', rte_revision='Simplify the diagnostic contract to the minimum '
                             'structure necessary; document; rerun affected dev conditions for both models; no task '
                             'change; no devtest.', icai_boundary='Frozen-NMT anchoring and semantic exemplar retrieval '
                             'cited as established prior methodology (ICAI); not claimed as Norris contributions.',
                             baseline='Sentence-split NLLB primary; unsplit diagnostic.'),
        research_questions=RESEARCH_QUESTIONS, rq_analysis=RQ_ANALYSIS,
        data=dict(dataset='openlanguagedata/flores_plus', revision=P.REVISIONS['flores_plus'],
                  code_mapping='FLORES+ fil_Latn -> NLLB tgl_Latn', spanish='standard Spanish (spa_Latn); no claims '
                  'about heritage, dialectal, code-switched or Los Angeles community Spanish',
                  dev='997 IDs: prompt development, retrieval pool, pilots', devtest='1,012 IDs per direction: main '
                  'experiment only, opened after this freeze', directions=P.DIRECTION_KEYS),
        matrix=dict(systems={'S0': 'sentence-split NLLB-200 3.3B (primary baseline)',
                             'S0u': 'unsplit NLLB-200 3.3B (diagnostic, not in confirmatory families)',
                             'S1': 'GPT-4o Mini zero-shot', 'S2': 'GPT-4o Mini retrieved one-shot',
                             'S3': 'GPT-4o Mini reason-then-edit', 'S4': 'Llama 3 8B Instruct zero-shot',
                             'S5': 'Llama 3 8B Instruct retrieved one-shot', 'S6': 'Llama 3 8B Instruct reason-then-edit'},
                    post_editing_outputs=24288, conditions=24, items_per_condition=1012, baseline_records=4048),
        baseline=dict(model='facebook/nllb-200-3.3B', revision=P.REVISIONS['nllb'], precision='float16',
                      decode=g2['decode'], truncation=False,
                      splitter=g1['patterns'], splitter_version=g1['splitter_version'], pysbd=g1['pysbd'],
                      fragment_variant=g2['frozen_variant'], code_sha256=g1['code_sha256'],
                      single_segment_rule='reuse the checksum-locked Phase 2 unsplit devtest hypothesis (as on dev)',
                      phase2_devtest_unsplit_sha256=archive_sha,
                      dev_gates=dict(segmentation=g1['report'], join_rule=g2['join_rule'],
                                     single_segment_reuse=g2['single_segment_reuse'],
                                     multi_items=g2['multi_items'], fragments=g2['fragments'],
                                     differing_fragments={k: v for k, v in g2['differing_fragments'].items() if k != 'items'},
                                     deterministic_within_environment=g2['checks']['deterministic_within_environment'],
                                     unsplit_regeneration=g2['unsplit_regeneration'],
                                     measured_variants_dev=g2['measured_variants_dev'],
                                     criterion_note=g2['criterion_note']),
                      reconstruction_note='Original split-generation cell not recovered; splitter reconstructed from the '
                                          'recorded run_spec (exact on all 2,991 dev segmentations). Translation '
                                          'reproduction is measured and disclosed, not bit-exact (FP16 beam search).'),
        protocol=dict(id=P.PROTOCOL_ID, fingerprint=P.protocol_fingerprint(), plain_version=P.PLAIN_VERSION,
                      rte_version=P.RTE_VERSION, system_base=P.SYSTEM_BASE, plain_suffix=P.PLAIN_SUFFIX,
                      reason_suffix=P.REASON_SUFFIX_V3, schemas={s: P.schema_for(s) for s in P.STRATEGIES},
                      output_contract=dict(plain='JSON; no duplicate keys; {edited_translation} non-empty; strict; '
                                                 'finish_reason stop', reason_then_edit='JSON; no duplicate keys; exactly '
                                                 '{diagnosis, edited_translation} in that order; both non-empty; strict; '
                                                 'finish_reason stop'),
                      fallback='Invalid/unfinished output -> unchanged S0 draft; raw output retained; no repair; no '
                               'selective regeneration; all planned items stay in the primary population.',
                      reference_rule='Query references never in prompts; only the retrieved dev demonstration exposes '
                                     'its own dev reference.'),
        editors=dict(llama=dict(model=P.MODELS['llama3-8b'], revision=P.REVISIONS['llama'], sampling=E.LLAMA_SAMPLING,
                                engine=E.LLAMA_ENGINE, batch=E.LLAMA_BATCH, vllm='0.11.2'),
                     gpt=dict(model=P.MODELS['gpt4o-mini'], payload=E.GPT_PAYLOAD, structured_output='json_schema strict',
                              client='openai 1.109.1 AsyncOpenAI, max_retries=0',
                              transport='transient HTTP retry <=5 with backoff; timeout/connection -> uncertain, halt; '
                                        'operator release recorded in attempt history')),
        retrieval_main=dict(encoder='sentence-transformers/LaBSE', revision=P.REVISIONS['labse'],
                            pool='all 997 dev IDs (same source language)', exclusion='exact stripped-source duplicates of '
                            'the query', ranking='cosine on normalized float32; exact FAISS IndexFlatIP', k=1,
                            tie_break='smallest dev sentence_id', note='Pilot excluded its 100 IDs; the main pool does '
                            'not, as declared in the Phase 4/5 plan.'),
        evaluation=dict(primary='COMET-22 Unbabel/wmt22-comet-da @ ' + P.REVISIONS['comet'] + ', native x100',
                        BLEU='sacrebleu 2.6.0, 13a, mixed case, exp smoothing (descriptive)',
                        chrF='chrF++ char order 6, word order 2, beta 2 (descriptive; roadmap nw:1 superseded)',
                        population='all 1,012 aligned items per direction including fallback',
                        families=dict(F1='24 tests: each PE condition minus S0 per direction',
                                      F2='24 tests: one-shot - zero-shot, reason - zero-shot, reason - one-shot within '
                                         'model x direction'),
                        test='two-sided centered paired bootstrap, B=10,000, seed 42, shared resample index; '
                             'p=(1+#|null|>=|obs|)/(B+1)', ci='paired percentile 95% (pointwise)',
                        multiplicity='Holm within family, alpha .05; markers from adjusted p',
                        practical_band='+/-0.5 COMET points (flag only; not an equivalence test)',
                        bands=dict(improved='> +0.02 native', within='[-0.02, +0.02]', decreased='< -0.02 native'),
                        pools=dict(protect='S0 COMET >= .90 on devtest', improve='S0 COMET < .80'),
                        overediting='protect item, text changed (NFC, outer whitespace stripped), native loss > .02; '
                                    'denominator = all protect items; sensitivity .01/.05',
                        flags='digit multiset/loss and capitalized-token screens (pilot definitions); langdetect 1.0.9 '
                              'seed 0 (replaces roadmap fastText; tl/es/en); length ratio words >2.5 or <.4; pysbd sentence '
                              'count drop/restore on multi-segment items',
                        edit_distance='character Levenshtein (rapidfuzz 3.10.1) on NFC outer-stripped strings, '
                                      'normalized by max length',
                        interpretation='Nonsignificant = inconclusive. No language/direction difference inferred from '
                                       'significance patterns. No exploratory test added to F1/F2 after viewing devtest.',
                        stats_sha256=P.file_sha256(Path(ST.__file__)), evaluator_sha256=P.file_sha256(Path(EV.__file__))),
        dev_evidence=dict(v2_pilot_analysis_sha256=P.V2_PILOT_ANALYSIS_SHA,
                          rte_v3_analysis_sha256=rte['analysis_sha256'], rte_v3_gate=rte['gate'],
                          rte_v3_gate_pass=rte['gate_pass'], rte_disposition=args.rte_disposition,
                          pi_decision_note=args.pi_decision_note),
        deviations_from_roadmap=[
            'Language code tag_Latn (role files) corrected to tgl_Latn; FLORES+ fil_Latn mapped.',
            'chrF++ word order 2 (Report 1) supersedes nw:1 in 5.txt.',
            'langdetect 1.0.9 replaces fastText language ID (pilot-validated; heuristic).',
            'Reason-then-edit contract simplified per PI (22 Oct 2026): six-category taxonomy and its validators '
            'removed; one free-text diagnosis field before the translation.',
            'Roadmap "contrastive CoT" naming not used; condition is single-call structured reason-then-edit.',
            'LaBSE retrieval is semantic similarity only; no syntactic-similarity claim.',
            'No external human raters (PI, 24 Sep 2026).',
            'vLLM 0.11.2 StructuredOutputsParams (GuidedDecodingParams no longer exists); offline engine, not a server.',
            'SQLite ledger on local disk with durable per-job JSON records on Drive (Drive-mounted SQLite unreliable).',
            'Sentence-split NLLB is the primary baseline (PI approved); unsplit retained as diagnostic.',
            'FLORES+ maintained release used in place of the original FLORES-200 distribution.'],
        code_sha256={f: P.file_sha256(REPO / f) for f in FROZEN_CODE},
        created_utc=datetime.now(timezone.utc).isoformat())
    out = Path(args.out)
    P.atomic_json(out, freeze)
    P.atomic_json(root / 'outputs/frozen/protocol_freeze.json', freeze)
    print('FREEZE', 'DECLARED' if args.declare else 'DRAFT (not declared)', '->', out)
    print('freeze sha256:', P.file_sha256(out))


if __name__ == '__main__':
    main()
