"""Phase 5 / 7.txt figures, regenerated only from saved numeric evaluation records.

  fig_delta_ecdf.pdf   empirical CDF of segment Delta-COMET (points) per direction, editor x strategy
  fig_bands.pdf        improved / within band / harmed counts per condition (stacked, 1,012 each)
Usage: python generate_main_figures.py --eval-dir <outputs/phase5/eval_xxx> --out paper/figures
"""
import argparse
import json
import os
from pathlib import Path

os.environ['MPLBACKEND'] = 'Agg'  # Colab exports an inline backend that a separate venv cannot load
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DIRS = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn', 'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
DLAB = {'eng_Latn->tgl_Latn': 'En→Tl', 'tgl_Latn->eng_Latn': 'Tl→En', 'eng_Latn->spa_Latn': 'En→Es', 'spa_Latn->eng_Latn': 'Es→En'}
STRATS = ['zero-shot', 'knn-oneshot', 'reason-then-edit']
SLAB = {'zero-shot': 'Zero-shot', 'knn-oneshot': 'One-shot', 'reason-then-edit': 'Reason-then-edit'}
MODELS = ['gpt4o-mini', 'llama3-8b']
MLAB = {'gpt4o-mini': 'GPT-4o Mini', 'llama3-8b': 'Llama 3 8B'}
STYLE = {'zero-shot': dict(color='#1b9e77', ls='-'), 'knn-oneshot': dict(color='#d95f02', ls='--'),
         'reason-then-edit': dict(color='#7570b3', ls=':')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eval-dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ev, out = Path(a.eval_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(x) for x in (ev / 'segment_scores_numeric.jsonl').read_text().splitlines() if x.strip()]
    res = json.loads((ev / 'main_results.json').read_text())
    plt.rcParams.update({'font.size': 7, 'pdf.fonttype': 42, 'ps.fonttype': 42})

    fig, axes = plt.subplots(2, 4, figsize=(7.1, 3.0), sharex=True, sharey=True)
    for i, m in enumerate(MODELS):
        for j, d in enumerate(DIRS):
            ax = axes[i, j]
            for s in STRATS:
                v = np.sort([100 * r['delta_comet_native'] for r in rows if r['model'] == m and r['direction'] == d and r['strategy'] == s])
                ax.step(v, np.arange(1, len(v) + 1) / len(v), where='post', lw=.9, label=SLAB[s], **STYLE[s])
            ax.axvline(0, color='0.6', lw=.5)
            ax.set_xlim(-30, 30)
            ax.grid(alpha=.25, lw=.4)
            if i == 0:
                ax.set_title(DLAB[d])
            if j == 0:
                ax.set_ylabel(MLAB[m] + '\ncumulative fraction')
            if i == 1:
                ax.set_xlabel('ΔCOMET (points)')
    axes[0, 0].legend(frameon=False, fontsize=6, loc='upper left')
    fig.tight_layout(pad=.4)
    fig.savefig(out / 'fig_delta_ecdf.pdf')
    fig.savefig(out / 'fig_delta_ecdf.png', dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(7.1, 1.9), sharey=True)
    for j, d in enumerate(DIRS):
        ax = axes[j]
        labels, imp, mid, harm = [], [], [], []
        for m in MODELS:
            for s in STRATS:
                c = res['conditions'][f'{m}/{d}/{s}']
                labels.append(('G' if m == 'gpt4o-mini' else 'L') + '-' + {'zero-shot': 'Z', 'knn-oneshot': 'O', 'reason-then-edit': 'R'}[s])
                imp.append(c['improved']); mid.append(c['within_band']); harm.append(c['harmed'])
        x = np.arange(len(labels))
        ax.bar(x, harm, color='#d73027', label='Harmed (<−2)')
        ax.bar(x, mid, bottom=harm, color='#e0e0e0', label='Within ±2')
        ax.bar(x, imp, bottom=np.add(harm, mid), color='#4575b4', label='Improved (>+2)')
        ax.set_xticks(x, labels, rotation=90)
        ax.set_title(DLAB[d])
        ax.set_ylim(0, 1012)
    axes[0].set_ylabel('items (of 1,012)')
    axes[-1].legend(frameon=False, fontsize=5.5, loc='lower right')
    fig.tight_layout(pad=.4)
    fig.savefig(out / 'fig_bands.pdf')
    fig.savefig(out / 'fig_bands.png', dpi=300)
    plt.close(fig)
    print('figures ->', out)


if __name__ == '__main__':
    main()
