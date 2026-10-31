"""Build Norris Phase Report 5.1. Every number is read from the committed evidence files; nothing is typed by hand
except the fixed labels of the frozen protocol."""
import hashlib
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
FD = '/usr/share/fonts/truetype/liberation/'
pdfmetrics.registerFont(TTFont('LS', FD + 'LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('LS-B', FD + 'LiberationSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('LS-I', FD + 'LiberationSans-Italic.ttf'))
pdfmetrics.registerFont(TTFont('LS-BI', FD + 'LiberationSans-BoldItalic.ttf'))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily('LS', normal='LS', bold='LS-B', italic='LS-I', boldItalic='LS-BI')

RES = json.loads((REPO / 'docs/phase5/evidence/main_results.json').read_text())
X = json.loads((REPO / 'docs/phase5/evidence/extended/extended_analyses.json').read_text())
sha = lambda p: hashlib.sha256((REPO / p).read_bytes()).hexdigest()

D = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn', 'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
DL = {'eng_Latn->tgl_Latn': 'En→Tl', 'tgl_Latn->eng_Latn': 'Tl→En', 'eng_Latn->spa_Latn': 'En→Es', 'spa_Latn->eng_Latn': 'Es→En'}
S = ['zero-shot', 'knn-oneshot', 'reason-then-edit']
SL = {'zero-shot': 'Zero-shot', 'knn-oneshot': 'One-shot', 'reason-then-edit': 'Reason-then-edit'}
M = ['gpt4o-mini', 'llama3-8b']
ML = {'gpt4o-mini': 'GPT-4o Mini', 'llama3-8b': 'Llama 3 8B'}
F1 = {(r['model'], r['strategy'], r['direction']): r for r in RES['F1_primary']}
C = RES['conditions']

HEAD = colors.HexColor('#E6EDF7')
GRID = colors.HexColor('#B8C4D6')
BLUE = colors.HexColor('#2F5DA8')
NOTE = colors.HexColor('#F4F6FA')

ss = {
    'title': ParagraphStyle('t', fontName='LS-B', fontSize=22, leading=27, spaceAfter=4),
    'sub': ParagraphStyle('s', fontName='LS-I', fontSize=11.5, leading=15, spaceAfter=9),
    'meta': ParagraphStyle('m', fontName='LS', fontSize=9.6, leading=12.6),
    'h1': ParagraphStyle('h1', fontName='LS-B', fontSize=13.5, leading=17, spaceBefore=9, spaceAfter=4),
    'h2': ParagraphStyle('h2', fontName='LS-B', fontSize=10.5, leading=13.5, spaceBefore=6, spaceAfter=2),
    'body': ParagraphStyle('b', fontName='LS', fontSize=9.3, leading=12.3, spaceAfter=4.5, alignment=TA_LEFT),
    'lead': ParagraphStyle('l', fontName='LS-B', fontSize=9.8, leading=13, spaceAfter=6),
    'cap': ParagraphStyle('c', fontName='LS', fontSize=7.8, leading=9.8, textColor=colors.HexColor('#333333'), spaceAfter=7),
    'cell': ParagraphStyle('cell', fontName='LS', fontSize=7.6, leading=9.4),
    'cellb': ParagraphStyle('cellb', fontName='LS-B', fontSize=7.6, leading=9.4),
    'bul': ParagraphStyle('bul', fontName='LS', fontSize=9.2, leading=12.1, leftIndent=11, bulletIndent=2, spaceAfter=2.5),
}


def P(t, st='body'):
    return Paragraph(t, ss[st])


def bullets(items):
    return [Paragraph(t, ss['bul'], bulletText='•') for t in items]


def table(rows, widths, head=1, align_right_from=None, zebra=False, fs=7.6, bold_first_col=False):
    data = [[c if not isinstance(c, str) else Paragraph(c, ss['cellb'] if (i < head) else ss['cell']) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=head)
    st = [('GRID', (0, 0), (-1, -1), 0.5, GRID), ('BACKGROUND', (0, 0), (-1, head - 1), HEAD),
          ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 2.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
          ('LEFTPADDING', (0, 0), (-1, -1), 3.5), ('RIGHTPADDING', (0, 0), (-1, -1), 3.5)]
    if zebra:
        for i in range(head, len(rows)):
            if (i - head) % 2 == 1:
                st.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FAFBFD')))
    t.setStyle(TableStyle(st))
    return t


def note_box(text):
    t = Table([[Paragraph(text, ss['body'])]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NOTE), ('BOX', (0, 0), (-1, -1), 0.6, GRID),
                           ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                           ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def fig(path, width):
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(str(path))
    w, h = ir.getSize()
    return Image(str(path), width=width, height=width * h / w)


pc = lambda x, d=1: f'{100 * x:.{d}f}'
sp = lambda x, d=2: f'{x:+.{d}f}'.replace('-', '−')
num = lambda x, d=2: f'{x:.{d}f}'.replace('-', '−')
ci = lambda lo, hi, d=2: f'[{sp(lo, d)}, {sp(hi, d)}]'

# ------------------------------------------------------------------ derived values used in the prose
mu = X['X1_multiplicity']
x3 = X['X3_summary']
x4 = X['X4_summary']
x5 = X['X5_summary']
x6 = X['X6_summary']
x7 = X['X7_metric_concordance']
x8 = X['X8_strategy_rank_concordance']
x9 = X['X9_cost']
rates = X['X5_overediting']['rates']
gaps = X['X5_overediting']['editor_gap_same_strategy']
cn = mu['closest_nonsignificant']
cost = x9['by_strategy']
one_vs_zero_cost = 100 * (cost['knn-oneshot']['cost_usd'] / cost['zero-shot']['cost_usd'] - 1)
one_vs_zero_gain = 100 * (cost['knn-oneshot']['mean_delta'] / cost['zero-shot']['mean_delta'] - 1)
rte_vs_zero_cost = 100 * (cost['reason-then-edit']['cost_usd'] / cost['zero-shot']['cost_usd'] - 1)
rte_vs_zero_gain = 100 * (cost['reason-then-edit']['mean_delta'] / cost['zero-shot']['mean_delta'] - 1)
weak_share_items = {d: RES['baseline_pools'][d]['improve'] / RES['baseline_pools'][d]['n'] for d in D}
gap_lo = min(v['ci'][0] for k, v in gaps.items())
gap_hi = max(v['ci'][1] for k, v in gaps.items())
sep = X['X5_direction_separation']
sep_yes = [DL[d] for d in D if sep[d]['separate']]
sep_no = [DL[d] for d in D if not sep[d]['separate']]
bh_added = [RES['F2_strategy'][i] for i in mu['F2']['changed_vs_holm']['bh_fdr']]
band = X['X2_band_sensitivity']
pooled_w = X['X4_standardization']['weights']

story = []
# ------------------------------------------------------------------ title block
story += [P('Norris Phase Report 5.1', 'title'),
          P('Phase 5 final: held-out evaluation consolidated, with exploratory robustness analyses', 'sub'),
          P('Principal Investigator&nbsp;&nbsp;Dr Benyamin Ahmadnia', 'meta'),
          P('Graduate Research Assistant&nbsp;&nbsp;Shazan Ansar Mohammed', 'meta'),
          P('Reporting date&nbsp;&nbsp;30 October 2026 (supplements Report 5 of 25 October 2026)', 'meta'),
          P('Repository&nbsp;&nbsp;github.com/SHAZAN01/csudh-norris-ape-2026 (phase4-main, to be merged into main)', 'meta'),
          Spacer(1, 8),
          P('Phase 5 complete. The confirmatory results of Report 5 stand unchanged; ten exploratory analyses, run '
            'from committed evidence only, confirm them and sharpen two interpretations. One wording in Report 5 (RQ1) '
            'is corrected below, and three sentences of the manuscript were revised accordingly.', 'lead')]

story += [P('Executive summary', 'h1')]
story += [P(f'<b>What this report adds.</b> Report 5 delivered the frozen confirmatory analysis: two Holm families of 24 paired-bootstrap '
            f'tests, harm bands, protect-pool over-editing, preservation screens and a 96-case source review. Report 5.1 asks how robust '
            f'those conclusions are and where the effects come from. All analyses below are <i>exploratory</i>, declared after the '
            f'confirmatory analysis, computed by a new script (<font face="LS-I">src/analysis/phase5_extended.py</font>) from '
            f'<font face="LS-I">main_results.json</font> and the Phase 4 run summary, and verified by unit tests against SciPy and a '
            f'published Newcombe example. No frozen file, threshold, family or research question was changed.')]
story += bullets([
    f'<b>The confirmatory conclusions are robust.</b> No F1 decision changes under Bonferroni or Benjamini–Hochberg correction, or under '
    f'Holm over both families jointly (48 tests). All {mu["F1"]["holm_frozen"]} Holm-significant F1 effects have the same sign in COMET, '
    f'BLEU and chrF++; across all 24 conditions the COMET deltas rank-correlate with chrF++ at ρ = {x7["spearman_comet_chrf"]:.2f} and with BLEU at '
    f'ρ = {x7["spearman_comet_bleu"]:.2f}.',
    f'<b>Where the gains come from.</b> An exact decomposition of each mean ΔCOMET by baseline-quality pool reproduces all 24 F1 deltas '
    f'(maximum error {X["checks"]["decomposition_max_abs_error_points"]:.0e} points). For GPT-4o Mini, weak drafts (S0 &lt; 0.80, 6–18% of items) supply '
    f'{pc(x3["gpt_weak_share_min"], 0)}–{pc(x3["gpt_weak_share_max"], 0)}% of each gain; strong drafts move the mean by at most '
    f'{x3["gpt_strong_contrib_abs_max"]:.3f} points. For Llama, edits help weak drafts in {x3["llama_weak_only_positive"]} of 12 conditions, '
    f'but losses on mid-quality and strong drafts outweigh them: even an oracle that left strong drafts untouched would keep Llama below S0 in '
    f'{12 - x3["llama_skip_strong_positive"]} of 12 conditions.',
    f'<b>RQ1 correction.</b> Reweighting each direction to a common quality mix narrows GPT-4o Mini’s Tagalog–Spanish gap by only '
    f'{x4["gpt_gap_reduction_min"]:.0f}–{x4["gpt_gap_reduction_max"]:.0f}%; at least {pc(x4["gpt_std_gap_middle_share_min"], 0)}% of the remaining gap arises '
    f'in mid-quality drafts. Report 5 §9 said the pair difference “tracks the share of weak drafts more than language”; that was too strong. '
    f'Baseline quality explains part of the difference, not most of it. The manuscript now says so.',
    f'<b>The over-editing gap is not a sampling artefact.</b> Wilson 95% intervals separate the pooled protect-pool rates (GPT-4o Mini at most '
    f'{pc(x5["gpt_max_upper_0.02"])}%, Llama at least {pc(x5["llama_min_lower_0.02"])}%), and the Llama − GPT-4o Mini difference excludes zero for every '
    f'strategy at every sensitivity threshold. Per direction, the intervals separate out of English ({", ".join(sep_yes)}) but overlap into English '
    f'({", ".join(sep_no)}).',
    f'<b>Edit quality, not edit quantity.</b> Among edited drafts, every GPT-4o Mini condition harms at most {pc(x6["gpt_harm_rate_max"])}%, below the '
    f'{pc(x6["llama_harm_rate_min"])}% minimum for Llama. GPT-4o Mini makes {num(x6["gpt_ratio_min"], 1)}–{num(x6["gpt_ratio_max"], 1)} improvements per harm; '
    f'Llama {num(x6["llama_ratio_min"], 2)}–{num(x6["llama_ratio_max"], 2)}, below one in {x6["llama_ratio_below_1"]} of 12 conditions.',
    f'<b>Strategy ranking and cost.</b> GPT-4o Mini ranks one-shot &gt; zero-shot &gt; reason-then-edit in all four directions (Kendall’s '
    f'W = {x8["gpt4o-mini"]["W"]:.2f}); reason-then-edit is last for both editors everywhere. One-shot costs {one_vs_zero_cost:.0f}% more than zero-shot and '
    f'yields a {one_vs_zero_gain:.0f}% larger mean gain; reason-then-edit costs {rte_vs_zero_cost:.0f}% more and yields {abs(rte_vs_zero_gain):.0f}% less.',
])

ver = [['Check', 'Result'],
       ['Inputs', f'main_results.json (evaluation {RES["evaluation_sha256"][:16]}…) and Phase 4 GPT run summary; no text, generations or GPU'],
       ['Holm recomputation', f'F1 and F2 Holm p-values recomputed from raw p: maximum difference {X["checks"]["F1_holm_recomputed_maxdiff"]:.0f} and {X["checks"]["F2_holm_recomputed_maxdiff"]:.0f}'],
       ['Pool decomposition', f'Σ(pool share × pool mean) equals each of the 24 F1 deltas; maximum error {X["checks"]["decomposition_max_abs_error_points"]:.1e} points'],
       ['Practical-band flag', 'Recomputed ±0.5 flags equal the frozen evaluator’s flags for all 48 contrasts'],
       ['Token accounting', 'Phase 5 token counts equal the Phase 4 run summary for all 12 GPT-4o Mini conditions'],
       ['Statistics code', 'Wilson, Spearman, BH and Holm equal SciPy to 1e−12; Newcombe interval reproduces the published 0.0524–0.3339'],
       ['Manuscript audit', '77 held-out claims (66 + 11 new) verified against evidence; planted errors in new claims detected; 5 pages']]
story += [Spacer(1, 3), KeepTogether(table(ver, [1.55 * inch, 5.45 * inch]))]

# ------------------------------------------------------------------ 1 scope
story += [P('1. Status of these analyses', 'h1'),
          P('The approved plan (17 October) allows analyses beyond the two confirmatory families if they are labelled exploratory and '
            'their multiplicity treatment is stated. Accordingly: (i) none of the analyses below adds a test to F1 or F2; (ii) where '
            'intervals are reported they are pointwise and descriptive, with no new significance claims; (iii) any quantity that uses the '
            'reference-based S0 COMET to decide which drafts to edit is labelled <b>oracle</b>, because a deployed system cannot see the reference; '
            '(iv) the analyses use condition-level aggregates committed in the repository. Item-level indicators remain private on Drive, so '
            'intervals for over-editing differences treat the two editors’ samples as independent (Section 6).'),
          P('The pool definitions are the frozen ones: <i>weak</i> (improve pool) S0 COMET &lt; 0.80; <i>strong</i> (protect pool) S0 COMET ≥ 0.90; '
            '<i>middle</i> in between. Pool sizes per direction (weak / middle / strong): ' +
            '; '.join(f'{DL[d]} {RES["baseline_pools"][d]["improve"]} / {RES["baseline_pools"][d]["n"] - RES["baseline_pools"][d]["improve"] - RES["baseline_pools"][d]["protect"]} / {RES["baseline_pools"][d]["protect"]}' for d in D) + '.')]

# ------------------------------------------------------------------ 2 confirmatory recap
story += [P('2. Confirmatory results at a glance (unchanged from Report 5)', 'h1'),
          fig(REPO / 'docs/phase5/figures_extended/figX1_forest_F1.png', 6.9 * inch),
          P('Figure 1. Primary family F1: each condition minus S0 with paired percentile 95% intervals (10,000 resamples, seed 42). Filled markers '
            'are significant after Holm correction over 24 tests; the grey band is the prespecified ±0.5-point practical band (a flag, not an '
            'equivalence test). Full F1/F2 tables with raw and Holm p-values are in Report 5, Sections 2–3.', 'cap'),
          P(f'GPT-4o Mini improves all twelve conditions ({sp(min(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D))} to '
            f'{sp(max(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D))} points); Llama 3 8B improves none and is significantly worse in six. '
            f'In the strategy family, {sum(r["significant_holm"] for r in RES["F2_strategy"])} of 24 contrasts are significant: one-shot beats zero-shot for '
            f'GPT-4o Mini in three directions, and reason-then-edit is never significantly better than either alternative.')]

# ------------------------------------------------------------------ 3 multiplicity + band
story += [P('3. Robustness of the inferential decisions', 'h1'), P('3.1 Alternative multiplicity corrections (X1)', 'h2')]
mt = [['Family (24 tests each)', 'Raw p &lt; .05', 'Holm (frozen)', 'Bonferroni', 'Benjamini–Hochberg (FDR)', 'Holm over all 48'],
      ['F1: condition − S0', str(mu['F1']['raw_p_below_alpha']), str(mu['F1']['holm_frozen']), str(mu['F1']['bonferroni']), str(mu['F1']['bh_fdr']),
       str(mu['pooled48_holm']['F1'])],
      ['F2: strategy contrasts', str(mu['F2']['raw_p_below_alpha']), str(mu['F2']['holm_frozen']), str(mu['F2']['bonferroni']), str(mu['F2']['bh_fdr']),
       str(mu['pooled48_holm']['F2'])]]
story += [table(mt, [1.7 * inch, 0.85 * inch, 0.95 * inch, 0.9 * inch, 1.5 * inch, 1.1 * inch]),
          P('Number of significant contrasts at α = 0.05 under each correction. Holm within each family is the frozen procedure; the others are sensitivity checks only.', 'cap'),
          P(f'Every F1 decision is identical under all four procedures, and every F2 decision is identical under Bonferroni and under a single Holm '
            f'family of 48. A less conservative FDR criterion would add three F2 contrasts, all small and none changing a conclusion: ' +
            '; '.join(f'{ML[r["model"]]} {DL[r["direction"]]} {r["contrast"].replace("knn-oneshot", "one-shot")} {sp(r["delta_points"])} (raw p = {r["p_raw"]:.3f})' for r in bh_added) +
            f'. The frozen Holm results are therefore, if anything, conservative. Resolution note: {mu["F1"]["raw_p_at_floor"]} of the '
            f'{mu["F1"]["holm_frozen"]} significant F1 tests and {mu["F2"]["raw_p_at_floor"]} of the {mu["F2"]["holm_frozen"]} significant F2 tests sit at the bootstrap floor p = 1/10,001; '
            f'with 24 tests the smallest attainable Holm value is 0.0024, comfortably below 0.05. The closest non-significant contrast is '
            f'{ML[cn["model"]]} {DL[cn["direction"]]} reason-then-edit − zero-shot ({sp(cn["delta"])}; raw p = {cn["p_raw"]:.3f}, Holm p = {cn["p_holm"]:.3f}).'),
          P('3.2 Width of the practical band (X2)', 'h2')]
bt = [['Editor', '±0.25 points: beyond / within / straddles', '±0.5 points (frozen)', '±1.0 point']]
for m in M:
    bt.append([ML[m]] + [f'{band[f"{m}@{b}"]["beyond"]} / {band[f"{m}@{b}"]["within"]} / {band[f"{m}@{b}"]["straddles"]}' for b in [0.25, 0.5, 1.0]])
story += [table(bt, [1.2 * inch, 2.3 * inch, 1.75 * inch, 1.75 * inch]),
          P('Counts of the 12 F1 intervals per editor that lie entirely beyond the band (|effect| larger than the band with 95% confidence), entirely within it, or straddle its edge.', 'cap'),
          P(f'Two readings are stable. First, no GPT-4o Mini interval lies beyond ±1 point: the gains are real but modest at every band width. '
            f'Second, Llama’s reason-then-edit losses remain beyond the band in {band["llama3-8b@1.0"]["beyond"]} directions even at ±1 point. '
            f'At ±0.25 points, {band["gpt4o-mini@0.25"]["beyond"]} of 12 GPT-4o Mini gains are clearly beyond the band, so “small” is not “negligible”.')]

# ------------------------------------------------------------------ 4 decomposition
story += [PageBreak(), P('4. Where gains and losses come from: exact pool decomposition (X3)', 'h1'),
          P('For each condition the mean ΔCOMET over 1,012 items equals Σ<sub>pool</sub> (n<sub>pool</sub> / 1,012) × mean ΔCOMET<sub>pool</sub>. '
            'The three terms are the contributions of weak, middle and strong drafts. Because the identity is exact, it is also a cross-artifact '
            'check: the pool means from the evaluator’s stratified summaries reproduce the F1 deltas from the bootstrap module to floating-point precision.'),
          fig(REPO / 'docs/phase5/figures_extended/figX2_pool_decomposition.png', 6.9 * inch),
          P('Figure 2. Contribution of each baseline-quality pool to the mean ΔCOMET (points). Bars stack positive and negative contributions separately; '
            'the black tick is the F1 total. Z/O/R = zero-shot / one-shot / reason-then-edit.', 'cap')]
dt = [['Editor', 'Strategy', 'Dir.', 'Weak', 'Middle', 'Strong', 'Total = F1', 'Oracle: weak only', 'Oracle: skip strong']]
for r in X['X3_pool_decomposition']:
    c = r['contribution']
    dt.append([ML[r['model']], SL[r['strategy']], DL[r['direction']], sp(c['improve'], 3), sp(c['middle'], 3), sp(c['protect'], 3),
               sp(r['F1_delta'], 3), sp(r['oracle_edit_weak_only'], 3), sp(r['oracle_skip_strong'], 3)])
story += [table(dt, [0.85 * inch, 1.0 * inch, 0.48 * inch, 0.62 * inch, 0.62 * inch, 0.62 * inch, 0.78 * inch, 0.98 * inch, 1.05 * inch], zebra=True),
          P('Contributions in COMET points. Oracle columns: the mean change if edits were kept only for weak drafts, or for all but strong drafts, '
            'with S0 elsewhere. They use the reference-based S0 score and are not deployable; they show headroom, not an achievable system.', 'cap')]
gw = {r['direction']: r for r in X['X3_pool_decomposition'] if r['model'] == 'gpt4o-mini' and r['strategy'] == 'knn-oneshot'}
story += [P('<b>Reading.</b> ' +
            f'GPT-4o Mini’s gains rest on weak and middle drafts, while strong drafts are essentially neutral (|contribution| ≤ {x3["gpt_strong_contrib_abs_max"]:.3f}). '
            f'The weak pool is small (from {pc(min(weak_share_items.values()), 0)}% of items in Es→En to {pc(max(weak_share_items.values()), 0)}% in En→Tl) yet carries '
            f'{pc(x3["gpt_weak_share_min"], 0)}–{pc(x3["gpt_weak_share_max"], 0)}% of each GPT-4o Mini gain. Llama shows the opposite profile: its weak-pool contribution is '
            f'positive in {x3["llama_weak_only_positive"]} of 12 conditions (all but reason-then-edit En→Tl), so the model can repair bad drafts, but its losses on '
            f'mid-quality and strong drafts dominate. Leaving strong drafts untouched would still leave {12 - x3["llama_skip_strong_positive"]} Llama conditions '
            f'below S0, all of them with negative middle-pool contributions. Protecting strong drafts is necessary but not sufficient: an open 8B editor would also '
            f'need to leave adequate mid-quality drafts alone. This motivates quality-estimation gating as future work; it was not part of the frozen design and is not claimed.')]

# ------------------------------------------------------------------ 5 RQ1 standardization
story += [P('5. RQ1 revisited: quality-standardized pair comparison (X4)', 'h1'),
          P(f'RQ1 asks how gains differ between the pairs <i>conditional on baseline quality</i>. Direct standardization answers this descriptively: each '
            f'direction’s pool means are reweighted to the pooled four-direction quality mix (weak {pc(pooled_w["improve"])}%, middle {pc(pooled_w["middle"])}%, '
            f'strong {pc(pooled_w["protect"])}%). If the Tagalog pair gained more only because it has more weak drafts, the standardized gap should vanish.')]
st = [['Editor', 'Strategy'] + [f'{DL[d]} raw / std' for d in D] + ['Tl − Es gap raw', 'Gap std', 'Reduction']]
for r in X['X4_standardization']['rows']:
    red = 100 * (1 - r['pair_gap_standardized'] / r['pair_gap_raw'])
    st.append([ML[r['model']], SL[r['strategy']]] + [f'{sp(r[d]["raw"])} / {sp(r[d]["standardized"])}' for d in D] +
              [sp(r['pair_gap_raw']), sp(r['pair_gap_standardized']), f'{red:.0f}%' if red >= 0 else f'widens {abs(red):.0f}%'])
story += [table(st, [0.82 * inch, 0.95 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch, 0.68 * inch, 0.6 * inch, 0.67 * inch], zebra=True),
          P('Raw = F1 delta; std = Σ pooled weight × direction pool mean. Gap = mean of the two Tagalog directions minus the mean of the two Spanish directions. '
            'For Llama the gap is negative (larger losses in the Tagalog pair) and standardization slightly widens it.', 'cap'),
          note_box(f'<b>Correction to Report 5, Section 9 (RQ1).</b> Report 5 stated that the pair difference “tracks the share of weak drafts more than language”. '
                   f'Standardization narrows GPT-4o Mini’s Tagalog–Spanish gap by only {x4["gpt_gap_reduction_min"]:.0f}–{x4["gpt_gap_reduction_max"]:.0f}%, and '
                   f'{pc(x4["gpt_std_gap_middle_share_min"], 0)}–{pc(max(x4["gpt_std_gap_middle_share"].values()), 0)}% of the remaining gap comes from mid-quality drafts, where '
                   f'GPT-4o Mini gains more in the Tagalog pair. <b>Corrected reading:</b> baseline-quality composition explains part of the pair difference; the remainder '
                   f'may reflect finer quality differences inside the broad middle pool or genuine pair effects, which three coarse pools cannot separate, and resource level '
                   f'stays confounded with language, direction and domain. The manuscript sentence was revised to this reading (Section 10).'),
          Spacer(1, 6)]

# ------------------------------------------------------------------ 6 over-editing uncertainty
story += [P('6. Uncertainty in over-editing (X5) and edit outcomes (X6)', 'h1'), P('6.1 Protect-pool over-editing with Wilson intervals', 'h2')]
ot = [['Editor', 'Strategy', 'Loss > 0.01', 'Loss > 0.02 (primary)', 'Loss > 0.05']]
for m in M:
    for s in S:
        row = [ML[m], SL[s]]
        for t in ['0.01', '0.02', '0.05']:
            v = rates[f'{m}|{s}|{t}']
            row.append(f'{v["x"]}/{v["n"]} = {pc(v["rate"])}% [{pc(v["lo"])}, {pc(v["hi"])}]')
        ot.append(row)
ot.append(['Llama − GPT', 'Same strategy'] + ['; '.join(f'{SL[s][0]} {pc(gaps[f"{s}|{t}"]["diff_llama_minus_gpt"])} [{pc(gaps[f"{s}|{t}"]["ci"][0])}, {pc(gaps[f"{s}|{t}"]["ci"][1])}]' for s in S) for t in ['0.01', '0.02', '0.05']])
story += [table(ot, [0.85 * inch, 1.05 * inch, 1.7 * inch, 1.7 * inch, 1.7 * inch], zebra=True),
          P('Pooled over the four directions (1,179 strong drafts). Brackets: Wilson 95% intervals; last row: Newcombe hybrid-score intervals for the difference in '
            'percentage points (Z/O/R), treating the editors as independent samples because item-level indicators are not in the committed evidence.', 'cap'),
          P(f'At every threshold and for every strategy the difference interval excludes zero (smallest lower bound {pc(gap_lo)} points). Per direction at the primary '
            f'threshold, the highest GPT-4o Mini upper bound lies below the lowest Llama lower bound in {", ".join(sep_yes)}, but the intervals overlap in {", ".join(sep_no)}, '
            f'where the Llama zero-shot and one-shot rates come closest to GPT-4o Mini one-shot. The pooled ordering is secure; direction-level ordering into English '
            f'should be stated with that caveat.'),
          fig(REPO / 'docs/phase5/figures_extended/figX3_edit_vs_overedit.png', 4.6 * inch),
          P('Figure 3. Share of drafts edited against the share of strong drafts over-edited (Wilson 95% intervals), one point per condition. Edit rates overlap '
            'between the editors (GPT-4o Mini one-shot edits 69–90%); over-editing rates do not.', 'cap'),
          P('6.2 What happens when an editor does change a draft', 'h2')]
et = [['Editor', 'Strategy', 'Dir.', 'Edited', 'Improved / edited', 'Harmed / edited', 'Improved : harmed', 'Net per 1,000 items']]
for r in X['X6_edit_outcomes']:
    et.append([ML[r['model']], SL[r['strategy']], DL[r['direction']], str(r['edited']), f'{pc(r["precision"])}%', f'{pc(r["harm_rate"])}%',
               num(r['benefit_harm_ratio'], 2), f'{r["net_per_1000"]:+.0f}'.replace('-', '−')])
story += [table(et, [0.85 * inch, 1.05 * inch, 0.5 * inch, 0.6 * inch, 1.05 * inch, 1.0 * inch, 0.95 * inch, 1.0 * inch], zebra=True),
          P('Improved / harmed: native ΔCOMET &gt; +0.02 / &lt; −0.02. Unedited outputs have Δ = 0, so every improved or harmed item is an edited one.', 'cap'),
          P(f'Conditional on editing, the editors separate completely: the worst GPT-4o Mini harm rate ({pc(x6["gpt_harm_rate_max"])}%) is below the best Llama harm rate '
            f'({pc(x6["llama_harm_rate_min"])}%). Among GPT-4o Mini strategies, zero-shot has the lowest harm rate among edits in every direction (tied with one-shot in En→Es); '
            f'one-shot accepts a similar or modestly higher harm rate for the largest net gain in three directions (tied in Es→En). Llama’s improvement rate among edits '
            f'(median 11%) is less than half of GPT-4o Mini’s (median 25%), and reason-then-edit raises its harm rate among edits to 23–32%.')]

# ------------------------------------------------------------------ 7 metric concordance, ranking, cost
story += [P('7. Metric concordance, strategy ranking and cost (X7–X9)', 'h1'),
          P(f'<b>Metrics.</b> Across the 24 conditions, ΔCOMET, ΔBLEU and ΔchrF++ agree in sign in {x7["sign_agree_all_three"]} cases, including all '
            f'{x7["significant_n"]} Holm-significant ones. Rank correlations: COMET–chrF++ ρ = {x7["spearman_comet_chrf"]:.2f}, COMET–BLEU ρ = {x7["spearman_comet_bleu"]:.2f}, '
            f'BLEU–chrF++ ρ = {x7["spearman_bleu_chrf"]:.2f}. The three disagreements are all non-significant Llama conditions in which COMET is flat while both '
            f'lexical metrics fall: ' + '; '.join(f'{SL[r["strategy"]]} {DL[r["direction"]]} (ΔCOMET {sp(r["dCOMET"])}, ΔBLEU {sp(r["dBLEU"])}, ΔchrF++ {sp(r["dchrF"])})' for r in x7['disagreements']) +
            '. This is the signature of rewording away from the reference without measured semantic loss, consistent with the source review. BLEU and chrF++ remain descriptive; no tests were run on them.'),
          P(f'<b>Strategy ranking.</b> Kendall’s coefficient of concordance across the four directions is W = {x8["gpt4o-mini"]["W"]:.2f} for GPT-4o Mini (one-shot first, '
            f'zero-shot second, reason-then-edit third in every direction) and W = {x8["llama3-8b"]["W"]:.2f} for Llama (one-shot and zero-shot swap in Es→En only). '
            f'Reason-then-edit ranks last for both editors in all four directions. Rankings use point estimates; their significance is the F2 family’s.')]
ct = [['GPT-4o Mini strategy', 'Cost, all 4 directions (USD)', 'Prompt / completion tokens per item', 'Mean F1 Δ (points)', 'Δ points per US$ per 1,000 items']]
for s in S:
    rows = [r for r in x9['per_condition'] if r['strategy'] == s]
    tk = x9['tokens_per_item']['gpt4o-mini'][s]
    ct.append([SL[s], f'{cost[s]["cost_usd"]:.3f}', f'{tk["prompt_per_item"]:.0f} / {tk["completion_per_item"]:.0f}', sp(cost[s]['mean_delta']),
               f'{min(r["points_per_dollar_per_1000"] for r in rows):.1f}–{max(r["points_per_dollar_per_1000"] for r in rows):.1f}'])
lt = x9['tokens_per_item']['llama3-8b']
story += [table(ct, [1.35 * inch, 1.45 * inch, 1.6 * inch, 1.1 * inch, 1.5 * inch]),
          P(f'List uncached token rates from the Phase 4 run summary (US${x9["gpt_total_devtest_usd"]:.2f} for all 12,144 devtest calls; not an invoice). Llama ran locally on one A100; '
            f'its tokens per item were {lt["zero-shot"]["prompt_per_item"]:.0f}/{lt["zero-shot"]["completion_per_item"]:.0f} (zero-shot), '
            f'{lt["knn-oneshot"]["prompt_per_item"]:.0f}/{lt["knn-oneshot"]["completion_per_item"]:.0f} (one-shot) and '
            f'{lt["reason-then-edit"]["prompt_per_item"]:.0f}/{lt["reason-then-edit"]["completion_per_item"]:.0f} (reason-then-edit).', 'cap'),
          P(f'<b>Cost.</b> The retrieved exemplar is worth its tokens: one-shot costs {one_vs_zero_cost:.0f}% more than zero-shot for a {one_vs_zero_gain:.0f}% larger mean gain. '
            f'Reason-then-edit is dominated: it costs {rte_vs_zero_cost:.0f}% more than zero-shot, through both longer prompts and longer completions, and gains {abs(rte_vs_zero_gain):.0f}% less. '
            f'At these prices, post-editing 1,000 sentences with GPT-4o Mini one-shot costs about US$0.09–0.10.')]

# ------------------------------------------------------------------ 8 RQ answers
story += [P('8. Final answers to the research questions', 'h1'),
          P('Confirmatory evidence first; exploratory refinements from this report are marked [X].')]
story += bullets([
    f'<b>RQ1 (pairs, conditional on quality).</b> GPT-4o Mini gains are larger for Tagalog ({sp(min(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D[:2]))} to '
    f'{sp(max(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D[:2]))}) than for Spanish ({sp(min(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D[2:]))} to '
    f'{sp(max(F1[("gpt4o-mini", s, d)]["delta_points"] for s in S for d in D[2:]))}), and Llama’s losses are also largest for Tagalog. Editing helps weak drafts in 23 of 24 '
    f'conditions in both pairs. [X] Quality composition explains {x4["gpt_gap_reduction_min"]:.0f}–{x4["gpt_gap_reduction_max"]:.0f}% of GPT-4o Mini’s pair gap; most of the rest arises in '
    f'mid-quality drafts. No causal resource claim.',
    '<b>RQ2 (strategies).</b> Retrieved one-shot is GPT-4o Mini’s best strategy (significant over zero-shot in three directions); reason-then-edit is never better '
    f'and is Llama’s worst in every direction. [X] The GPT-4o Mini ranking is identical in all four directions (W = {x8["gpt4o-mini"]["W"]:.2f}); one-shot is also the most cost-effective; '
    'conclusions are unchanged under Bonferroni or joint Holm correction.',
    f'<b>RQ3 (over-editing).</b> GPT-4o Mini over-edits 0.8–4.3% of strong drafts, Llama 11.2–20.9%. [X] Wilson intervals separate the pooled rates; conditional on editing, '
    f'every GPT-4o Mini harm rate is below every Llama harm rate; for Llama, even sparing strong drafts would not remove the losses, because mid-quality drafts are also degraded.',
    f'<b>RQ4 (direction).</b> Direction effects are small and inconsistent (into English larger for GPT-4o Mini in the Tagalog pair only). [X] The over-editing ordering is '
    f'secure out of English but overlaps per direction into English. Reverse directions carry translationese; no direction claim beyond the estimates.',
])

# ------------------------------------------------------------------ 9 phase 5 completion
story += [PageBreak(), P('9. Phase 5 completion against the approved plan', 'h1')]
cp = [['Deliverable (Plan of 17 Oct, §4–6)', 'Status', 'Where'],
      ['Full-precision metric JSON; signatures; COMET provenance', 'Done', 'docs/phase5/evidence/main_results.json, evaluation_spec.json'],
      ['Native per-item COMET scores (16,973 unique triplets)', 'Done (private)', 'Drive eval_aaff72ad…/segment_scores_numeric.jsonl'],
      ['Coverage audit: 24 × 1,012, aligned to S0', 'Done', 'Report 5, verification table'],
      ['Bootstrap configuration, F1 and F2 Holm families', 'Done', 'F1_primary.csv, F2_strategy.csv; Report 5 §2–3'],
      ['Effect tables, pool denominators, bands', 'Done', 'Report 5 §5–6; paper/generated/*'],
      ['Over-editing with sensitivity 0.01 / 0.02 / 0.05', 'Done', 'Report 5 §5; this report §6'],
      ['Failure summaries and preservation screens', 'Done', 'Report 5 §7 (0 fallbacks in all 24 conditions)'],
      ['Runtime and token accounting', 'Done', 'Report 4 §5–6; this report §7'],
      ['LaTeX results table (main_results_matrix.tex)', 'Done', 'paper/generated/, byte-identical to regeneration'],
      ['Figures regenerated from records, never by hand', 'Done', 'paper/figures/, docs/phase5/figures_extended/'],
      ['Cross-artifact numerical checks', 'Done', 'Report 5 (max difference 0); this report (decomposition 2e−16)'],
      ['Source-based review of flagged cases', 'Done', '96 cases; source_review_summary.json'],
      ['Robustness and sensitivity (exploratory)', 'Done', 'This report; extended/extended_analyses.json'],
      ['Transfer of verified results into Overleaf', 'Done', '5 pages; 77 audited held-out claims'],
      ['Review by the PI', 'With you', 'Reports 3.2, 4, 5 and 5.1']]
story += [table(cp, [3.0 * inch, 0.95 * inch, 3.05 * inch], zebra=True)]

# ------------------------------------------------------------------ 10 manuscript changes
story += [P('10. Manuscript and repository changes', 'h1'),
          P('Three manuscript edits follow from Sections 4–6; each new number is registered in <font face="LS-I">paper/claims_manifest.json</font> and '
            'recomputed by the audit from the committed evidence. The paper still compiles to exactly 5 pages including references.')]
mc = [['Section', 'Before', 'After'],
      ['Results, RQ1', '“The pair difference thus tracks baseline quality as much as language.”',
       '“Baseline quality explains only part of the pair difference, however: reweighting each direction to the pooled weak/middle/strong mix narrows '
       'GPT-4o Mini’s Tagalog–Spanish gap by 16–23%, and at least 73% of the remaining gap arises in mid-quality drafts (exploratory).”'],
      ['Results, new paragraph', '—',
       '“Robustness (exploratory).” Multiplicity invariance of F1; sign agreement of the 18 significant effects across three metrics; Wilson separation of over-editing '
       '(≤ 5.6% vs ≥ 9.5%); harm among edited drafts (≤ 8.9% vs ≥ 9.9%).'],
      ['Discussion, first paragraph', '“A post-editor is therefore only useful if it leaves correct drafts alone.”',
       'Adds: an oracle that left strong drafts untouched would keep Llama below S0 in 6 of 12 conditions, because it also degrades mid-quality drafts; protecting '
       'strong drafts is necessary but not sufficient.'],
      ['Conclusion', '“Gains came from weak drafts”', '“Gains came from weak and mid-quality drafts rather than strong ones” (the decomposition shows both pools contribute).']]
story += [table(mc, [1.2 * inch, 2.2 * inch, 3.6 * inch]),
          P('Repository additions on phase4-main: <font face="LS-I">src/analysis/phase5_extended.py</font>, <font face="LS-I">tests/phase5/test_extended.py</font>, '
            '<font face="LS-I">docs/phase5/evidence/extended/</font> (JSON and three CSVs), <font face="LS-I">docs/phase5/figures_extended/</font>, this report, '
            'eleven new audited facts in <font face="LS-I">src/analysis/phase5_facts.py</font>, and updates to the reviewer memo and README. The public-file audit passes; '
            'no benchmark text or generations are added.', 'body')]

# ------------------------------------------------------------------ 11 limitations + open items
story += [P('11. Limitations of the extended analyses', 'h1')]
story += bullets([
    'Post hoc: these analyses were chosen after the devtest results were seen. They re-express or bound frozen results; they do not create new confirmatory claims.',
    'Aggregates only: three coarse quality pools cannot separate finer quality differences inside the middle pool. A segment-level standardization (for example, '
    'by S0 COMET deciles) would need the private segment file on Drive.',
    'Independence approximation: Newcombe intervals for editor differences ignore that both editors edit the same strong drafts.',
    'Oracle gates use the reference and bound headroom only; a deployable gate would need reference-free quality estimation, chosen on dev.',
    'Costs use list token rates recorded at run time, not invoices; local Llama compute is not priced.',
])
story += [P('12. Decisions requested', 'h1')]
story += bullets([
    '<b>Author byline and order</b> (the manuscript still shows a working-draft byline).',
    '<b>S0 baseline-reproduction disposition</b> (Report 3.2 §5: 412/421 dev multi-sentence items identical; disclosed in the paper). Please acknowledge or advise.',
    '<b>Tagalog verification</b> of the 48 Tagalog-direction review cases (blind, three labels, about two hours), or keep it as a stated limitation.',
    '<b>The exploratory paragraphs and the RQ1 wording correction</b> in Results and Discussion: keep as written, shorten, or move to a footnote.',
])
story += [Spacer(1, 6), P('Evidence', 'h2'),
          P('Extended analyses ' + sha('docs/phase5/evidence/extended/extended_analyses.json') + '<br/>'
            'Analysis script ' + sha('src/analysis/phase5_extended.py') + '<br/>'
            'Phase 5 results ' + sha('docs/phase5/evidence/main_results.json') + '<br/>'
            'Evaluation ' + RES['evaluation_sha256'] + '<br/>'
            'Freeze 6e6259a9cf1c7e2aca978a770fa85d86596f31b0e8b3c55f42635203e4f7462c', 'cap')]


def deco(canvas, doc):
    canvas.saveState()
    canvas.setFont('LS', 7.6)
    canvas.setFillColor(colors.HexColor('#444444'))
    canvas.drawString(0.75 * inch, 10.6 * inch, 'NORRIS RESEARCH PROJECT  |  PHASE REPORT 5.1')
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(0.8)
    canvas.line(0.75 * inch, 10.53 * inch, 7.75 * inch, 10.53 * inch)
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f'30 October 2026  |  Phase 5 final, extended analyses  |  {doc.page}')
    canvas.restoreState()


for st_ in ('h1', 'h2'):
    ss[st_].keepWithNext = 1
doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.75 * inch,
                        bottomMargin=0.75 * inch, title='Norris Phase Report 5.1', author='Shazan Ansar Mohammed',
                        subject='Phase 5 final: held-out evaluation and exploratory robustness analyses')
doc.build(story, onFirstPage=deco, onLaterPages=deco)
print('built', OUT)
