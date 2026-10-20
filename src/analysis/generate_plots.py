"""Render descriptive dev distributions from public numeric-only evidence.

ECDFs retain the atom at zero from unchanged and fallback outputs. A smoothed
density would conceal that feature of this experiment. No inference is run.
"""
from collections import defaultdict
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper/figures'
OUT.mkdir(exist_ok=True)
rows = list(csv.DictReader((ROOT / 'docs/phase3/evidence/pilot/pilot_segment_scores.csv').open()))
groups = defaultdict(list)
for row in rows:
    groups[row['model'], row['direction'], row['strategy']].append(
        100 * float(row['delta_comet_native']))
directions = ['eng_Latn->tgl_Latn', 'tgl_Latn->eng_Latn',
              'eng_Latn->spa_Latn', 'spa_Latn->eng_Latn']
names = ['English to Tagalog', 'Tagalog to English', 'English to Spanish', 'Spanish to English']
models = [('gpt4o-mini', 'GPT-4o Mini'), ('llama3-8b', 'Llama 3 8B')]
strategies = [('zero-shot', 'Zero-shot', '#0072B2', '-'),
              ('knn-oneshot', 'One-shot', '#D55E00', '--'),
              ('reason-then-edit', 'Reason-then-edit', '#009E73', ':')]
plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(2, 4, figsize=(7.15, 3.25), sharex=True, sharey=True)
for i, (model, label) in enumerate(models):
    for j, (direction, name) in enumerate(zip(directions, names)):
        ax = axes[i, j]
        for strategy, strategy_name, color, style in strategies:
            x = np.sort(groups[model, direction, strategy])
            assert len(x) == 100
            assert x.min() >= -40 and x.max() <= 40, 'Plot range would hide an observation'
            # Extend each empirical CDF to the shared full plotting range.
            ax.step(np.r_[-40, x, 40], np.r_[0, np.arange(1, 101) / 100, 1],
                    where='post', color=color, linestyle=style, lw=1.3,
                    label=strategy_name)
        ax.axvline(0, color='#666666', lw=.65, zorder=0)
        ax.set_xlim(-40, 40); ax.set_ylim(0, 1.02)
        ax.set_xticks([-40, 0, 40]); ax.grid(axis='y', alpha=.18)
        if i == 0:
            ax.set_title(name, fontsize=8)
        if j == 0:
            ax.set_ylabel(label + '\nCumulative fraction')
        if i == 1:
            ax.set_xlabel('COMET change (points)')
fig.legend(*axes[0, 0].get_legend_handles_labels(), loc='upper center',
           bbox_to_anchor=(.53, 1.04), ncol=3, frameon=False)
fig.tight_layout(rect=(0, 0, 1, .95), w_pad=.6)
fig.savefig(OUT / 'pilot_delta_ecdf.pdf', bbox_inches='tight',
            metadata={'CreationDate': None, 'ModDate': None})
fig.savefig(OUT / 'pilot_delta_ecdf.png', bbox_inches='tight', dpi=220)
plt.close(fig)
print('Generated paper/figures/pilot_delta_ecdf.pdf and PNG; dev only, all 2400 outcomes.')
