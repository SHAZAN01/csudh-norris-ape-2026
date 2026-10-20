"""Regenerate development tables from audited numeric evidence, or check exact bytes."""
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'paper'
checked=[]
def put(path,text):
    expected=text.strip()+'\n'
    if args.check:
        if path.read_text()!=expected:raise SystemExit('Table differs from evidence: '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(expected)
    checked.append(str(path.relative_to(ROOT)))
rows=list(csv.DictReader((ROOT/'docs/phase3/evidence/pilot/pilot_condition_results.csv').open()))
directions=['eng_Latn->tgl_Latn','tgl_Latn->eng_Latn','eng_Latn->spa_Latn','spa_Latn->eng_Latn']
names={d:n for d,n in zip(directions,[r'En$\to$Tl',r'Tl$\to$En',r'En$\to$Es',r'Es$\to$En'])}
strategies=['zero-shot','knn-oneshot','reason-then-edit'];sn=['Zero','One','Reason']
lines=[r'\begin{table*}[t]',r'\centering\small',r'\caption{Development pilot results. Each row uses all 100 planned items, including fallback. COMET (C) and differences ($\Delta$) are reported on the native $\times100$ scale. Intervals are descriptive paired 95\% development intervals; no main-experiment significance is claimed. Zero/One/Reason denote zero-shot, retrieved one-shot, and reason-then-edit.}',r'\label{tab:pilot}',r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Direction & Strategy & BLEU & chrF++ & C & $\Delta$C & 95\% dev interval & Fallback \\',r'\midrule']
for model,label in [('gpt4o-mini','GPT-4o Mini'),('llama3-8b','Llama 3 8B Instruct')]:
    lines.append(r'\multicolumn{8}{l}{\textbf{'+label+r'}}\\')
    for d in directions:
        for st,n in zip(strategies,sn):
            r=next(r for r in rows if r['model']==model and r['direction']==d and r['strategy']==st)
            lo,hi=json.loads(r['delta_COMET_95CI_points'])
            lines.append(f"{names[d]} & {n} & {float(r['BLEU']):.3f} & {float(r['chrFpp']):.3f} & {float(r['COMET_points']):.3f} & {float(r['delta_COMET_points']):+.3f} & [{lo:+.3f}, {hi:+.3f}] & {r['fallbacks']} "+r'\\')
    lines.append(r'\midrule')
lines[-1]=r'\bottomrule'
lines += [r'\end{tabular}',r'\end{table*}']
put(P/'tables/pilot_results.tex','\n'.join(lines))
a=json.loads((ROOT/'docs/phase3/evidence/pilot/independent_numeric_audit.json').read_text())
base=[r'\begin{table}[t]\centering\small',r'\caption{Sentence-split baseline on the 100-ID development pilot. These are not the full 997-item development scores.}\label{tab:pilotbase}',r'\begin{tabular}{lrrr}\toprule Direction & BLEU & chrF++ & COMET \\\midrule']
for d in directions:
 r=a['baseline_pilot_metrics'][d];base.append(f"{names[d]} & {r['BLEU']:.3f} & {r['chrFpp']:.3f} & {r['COMET_points']:.3f} "+r'\\')
base += [r'\bottomrule\end{tabular}\end{table}'];put(P/'tables/pilot_baselines.tex','\n'.join(base))
harm=[r'\begin{table}[t]\centering\footnotesize',r'\caption{Pooled descriptive pilot counts per 400 outcomes. E: text edited; I/H: metric improvement/harm; P: protect-pool over-edits divided by all 116 protect observations.}\label{tab:harm}',r'\begin{tabular}{llrrrr}\toprule Editor & Strategy & E & I & H & P \\\midrule']
for model,label in [('gpt4o-mini','GPT'),('llama3-8b','Llama')]:
 for st,n in zip(strategies,sn):
  r=a['pooled_descriptive'][model+'/'+st];harm.append(f"{label} & {n} & {r['text_edited']} & {r['improved']} & {r['harmed']} & {r['overedited_protect_n']}/116 "+r'\\')
harm += [r'\bottomrule\end{tabular}\end{table}'];put(P/'tables/pilot_harm.tex','\n'.join(harm))

print(('Checked' if args.check else 'Generated')+': '+', '.join(checked))
