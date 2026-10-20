"""Recompute the Norris pilot report from the supplied evidence without GPU inference."""
import collections,csv,hashlib,importlib.util,json,math,statistics,sys
from pathlib import Path
import numpy as np
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent
sys.path.insert(0,str(ROOT/'code/pilot'))
import pilot_common as c
specmod=importlib.util.spec_from_file_location('supplied_analyzer',ROOT/'code/continuation/analyze_pilots.py')
an=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(an)
from sacrebleu.metrics import BLEU,CHRF

def read(p):return json.loads((ROOT/p).read_text())
def lines(p):return [json.loads(x) for x in (ROOT/p).read_text().splitlines() if x.strip()]
def close(x,y,tol=1e-9):
 if x is None or y is None:assert x is y,(x,y)
 elif isinstance(x,list):assert np.allclose(x,y,atol=tol,rtol=0),(x,y)
 elif isinstance(x,(float,int)):assert abs(x-y)<=tol,(x,y)
 else:assert x==y,(x,y)
checks=[]
def passed(name):checks.append(name);print('PASS',name)

m=read('prepared/prepared_manifest.json');s=read('analysis/analysis_spec.json');summary=read('analysis/pilot_summary.json')
assert c.digest(m['config'])==m['config_sha256'];assert c.digest(m)==s['prepared_manifest_sha256']
assert c.digest(s)==summary['analysis_sha256']
for name,h in m['file_sha256'].items():assert hashlib.sha256((ROOT/'prepared'/name).read_bytes()).hexdigest()==h,name
for name,h in m['config']['code_sha256'].items():assert hashlib.sha256((ROOT/'code/pilot'/name).read_bytes()).hexdigest()==h,name
assert hashlib.sha256((ROOT/'code/continuation/analyze_pilots.py').read_bytes()).hexdigest()==s['scorer_sha256']
passed('Prepared configuration and all preparation/code hashes; analysis signature')
jobs=lines('prepared/jobs.jsonl');jmap={j['job_key']:j for j in jobs};gold=lines('prepared/evaluation_gold.jsonl');gmap={(g['direction'],g['sentence_id']):g for g in gold}
assert len(jobs)==len(jmap)==1200 and len(gold)==len(gmap)==400
pilot=set(m['config']['pilot_ids']);assert len(pilot)==100 and c.digest(sorted(pilot))==m['config']['pilot_ids_sha256']
for j in jobs:
 assert j['job_sha256']==c.digest({k:v for k,v in j.items() if k!='job_sha256'})
 assert set(j['query'])=={'draft','source_text','sentence_id','src','tgt'}
 assert json.loads(j['messages'][-1]['content'])==json.loads(c._input_payload(j['query']))
 assert j['schema']==c.schema_for(j['strategy'])
 if j['strategy']=='knn-oneshot':assert j['demonstration_id'] not in pilot and len(j['messages'])==4
 else:assert j['messages']==c.build_messages(j['query'],j['strategy'])
passed('1200 unique prompt jobs, 400 offline query rows, query-field/reference isolation')
maps=read('prepared/retrieval_corpus_map.json');retrieval=read('prepared/retrieval_audit.json');max_coserr=0
for lang,rows in maps.items():
 mat=np.load(ROOT/'prepared'/('embeddings_'+lang+'.npy'));assert mat.shape==(997,768) and mat.dtype==np.float32
 assert np.allclose(np.linalg.norm(mat,axis=1),1,atol=1e-6)
 pos={r['sentence_id']:i for i,r in enumerate(rows)};hashed={r['sentence_id']:r['stripped_source_sha256'] for r in rows}
 for link in retrieval:
  if link['direction'].split('->')[0]!=lang:continue
  q=link['query_id'];d=link['demonstration_id'];assert d not in pilot and hashed[q]!=hashed[d]
  sims=mat@mat[pos[q]];eligible=[pos[i] for i in pos if i not in pilot and hashed[i]!=hashed[q]]
  assert sims[pos[d]]>=max(sims[i] for i in eligible)-1e-6
  max_coserr=max(max_coserr,abs(float(sims[pos[d]])-link['cosine_similarity']))
assert len(retrieval)==400
passed('All 400 nearest-neighbor links independently reconstructed; all pilot IDs and duplicate sources excluded')
raw={};rawmap={};fail_counts={};fingerprints={};gptcost=0
for model,folder in [('llama3-8b','llama'),('gpt4o-mini','gpt')]:
 run=read(folder+'/run_spec.json');assert run['prepared_manifest_sha256']==c.digest(m)
 rr=lines(folder+'/full_outputs.jsonl');assert len(rr)==1200 and {r['job_key'] for r in rr}==set(jmap)
 for r in rr:
  assert r['run_sha256']==c.digest(run)
  assert r['content_sha256']==c.digest({k:v for k,v in r.items() if k!='content_sha256'})
  job=jmap[r['job_key']];assert r['job_sha256']==job['job_sha256'] and r['messages']==job['messages']
  parsed=c.extract_response(r['raw_completion'],r['strategy'],job['query']['draft'],r['finish_reason'])
  for key in ['json_parse_success','schema_valid','usable','fallback_used','edited_translation','diagnostics']:assert r[key]==parsed[key]
  rawmap[(model,r['job_key'])]=r
 if model=='gpt4o-mini':
  assert all(r['returned_model']=='gpt-4o-mini-2024-07-18' for r in rr)
  assert len({r['response_id'] for r in rr})==1200
  assert hashlib.sha256((ROOT/'code/continuation/gpt_pilot.py').read_bytes()).hexdigest()==run['runner_sha256']
  for r in rr:
   assert r['raw_response']['choices'][0]['message']['content']==r['raw_completion']
   assert r['usage']==r['raw_response']['usage']
  fs=read('gpt/full_summary.json')
  assert sum(r['prompt_token_count'] for r in rr)==fs['prompt_tokens']
  assert sum(r['completion_token_count'] for r in rr)==fs['completion_tokens']
  gptcost=sum((r['prompt_token_count']*.15+r['completion_token_count']*.6)/1e6 for r in rr)
  close(gptcost,fs['estimated_cost_usd_uncached'])
  assert len(list((ROOT/'gpt/attempts').glob('*.json')))==1200
  assert all(json.loads(p.read_text())['state']=='recorded' for p in (ROOT/'gpt/attempts').glob('*.json'))
  fingerprints=dict(collections.Counter(r.get('system_fingerprint') for r in rr))
 failures=collections.Counter()
 for r in rr:
  if not r['usable']:
   try:
    d=json.loads(r['raw_completion']).get('diagnostics',[]);labels=[x.get('error_type') for x in d]
    if len(labels)!=len(set(labels)):failures['repeated_category']+=1
    if 'NONE' in labels and labels!=['NONE']:failures['NONE_mixed']+=1
    if any(not x.get('note','').strip() or len(x.get('note','').split())>25 for x in d):failures['invalid_note']+=1
    if not 1<=len(d)<=6:failures['diagnostic_count']+=1
   except Exception:failures['JSON_error']+=1
   if r['finish_reason']!='stop':failures['nonstop_finish']+=1
 fail_counts[model]=dict(failures);raw[model]=rr
passed('All 2400 raw-record hashes, prompt lineage, schema/fallback decisions; exact GPT snapshot; unique responses and usage accounting')
cfg=c.digest(dict(model=s['COMET_model'],revision=s['COMET_revision'],environment=s['environment']))
key=lambda src,mt,ref:c.digest(dict(src=src,mt=mt,ref=ref,scoring=cfg))
cache={}
for p in (ROOT/'analysis/comet_cache').glob('*.json'):
 x=json.loads(p.read_text());assert p.stem==x['key'] and math.isfinite(x['score']);cache[x['key']]=x['score']
details=lines('analysis/segment_analysis.jsonl');assert len(details)==2400
required=set();max_basediff=0
for r in details:
 g=gmap[(r['direction'],r['sentence_id'])];rr=rawmap[(r['model'],r['job_key'])]
 for field in ['source_text','reference_text','baseline_translation']:assert r[field]==g[field]
 assert r['edited_translation']==rr['edited_translation']
 bkey=key(g['source_text'],g['baseline_translation'],g['reference_text']);hkey=key(g['source_text'],r['edited_translation'],g['reference_text'])
 required.update([bkey,hkey]);close(r['baseline_comet_native'],cache[bkey]);close(r['comet_native'],cache[hkey])
 close(r['delta_comet_native'],cache[hkey]-cache[bkey]);close(r['baseline_comet_original_native'],g['baseline_comet_native'])
 max_basediff=max(max_basediff,abs(cache[bkey]-g['baseline_comet_native']))
 assert r['text_edited']==(r['edited_translation']!=g['baseline_translation'])
 flags=an.preservation_flags(g['source_text'],g['baseline_translation'],r['edited_translation'])
 for k in flags:assert r[k]==flags[k]
assert required==set(cache) and len(cache)==1492
close(max_basediff,read('analysis/baseline_recheck.json')['max_abs_difference_native'])
passed('1492 exact source-hypothesis-reference score-cache keys; all segment deltas, preservation flags and baseline recheck')
baseline_metrics={};rows_csv=[]
for name,stored in summary['groups'].items():
 model,direction,strategy=name.split('/');subset=[x for x in details if x['model']==model and x['direction']==direction and x['strategy']==strategy]
 assert len(subset)==100 and {r['sentence_id'] for r in subset}==pilot
 recomputed=an.aggregate(subset)
 for k,v in recomputed.items():close(v,stored[k])
 bleu,chrf=BLEU(tokenize='13a'),CHRF(char_order=6,word_order=2,beta=2)
 hyps=[r['edited_translation'] for r in subset];refs=[[r['reference_text'] for r in subset]]
 close(bleu.corpus_score(hyps,refs).score,stored['BLEU']);close(chrf.corpus_score(hyps,refs).score,stored['chrFpp'])
 assert str(bleu.get_signature())==stored['BLEU_signature'] and str(chrf.get_signature())==stored['chrF_signature']
 if direction not in baseline_metrics:
  baseline_metrics[direction]=dict(n=100,BLEU=bleu.corpus_score([r['baseline_translation'] for r in subset],refs).score,
    chrFpp=chrf.corpus_score([r['baseline_translation'] for r in subset],refs).score,COMET_points=stored['baseline_COMET_points'],
    protect_n=stored['protect_n'],improve_n=stored['improve_pool_n'])
 rows_csv.append(dict(model=model,direction=direction,strategy=strategy,**stored))
passed('All 24 condition means, counts, editing/harm/protect denominators, 10000-resample CIs, and BLEU/chrF++ values independently recomputed')
pooled={}
for model in raw:
 for st in c.STRATEGIES:
  subset=[x for x in details if x['model']==model and x['strategy']==st]
  pooled[model+'/'+st]=an.aggregate(subset)
out=ROOT/'independent_review';out.mkdir(exist_ok=True)
with (out/'pilot_condition_results.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows_csv[0]));w.writeheader();w.writerows(rows_csv)
numeric=[]
for r in details:
 numeric.append({k:v for k,v in r.items() if k not in ['source_text','reference_text','baseline_translation','edited_translation','raw_completion','diagnostics','validation_error','newly_absent_capitalized_source_tokens','preservation_interpretation','lost_digit_tokens']})
c.write_jsonl(out/'pilot_scores_numeric.jsonl',numeric)
influence={}
for model in raw:
 for st in c.STRATEGIES:
  subset=[r for r in details if r['model']==model and r['strategy']==st and r['direction']=='eng_Latn->tgl_Latn']
  influence[model+'/'+st]=dict(all_100_points=statistics.mean(r['delta_comet_native'] for r in subset)*100,
    without_dev_983_points=statistics.mean(r['delta_comet_native'] for r in subset if r['sentence_id']!=983)*100,
    interpretation='Post hoc influence diagnostic only; all 100 items retained in primary pilot results.')
result=dict(status='independent_numeric_audit_passed',checks=checks,n_checks=len(checks),
 raw_records=2400,planned_jobs_per_model=1200,offline_queries=400,pilot_aligned_ids=100,
 score_cache_triplets=len(cache),max_cosine_reconstruction_difference=max_coserr,
 baseline_recheck_max_abs_native=max_basediff,failure_patterns=fail_counts,
 gpt_token_cost_estimate_usd=gptcost,gpt_system_fingerprints=fingerprints,
 baseline_pilot_metrics=baseline_metrics,pooled_descriptive=pooled,post_hoc_influence=influence,
 scope='Lexical metrics recomputed from raw text; COMET aggregates/CIs and exact triplet alignment recomputed from the supplied numeric caches. Neural COMET inference not rerun here. Language-ID flags retained from the supplied pinned langdetect run; not independently regenerated.',
 freeze_declared=False)
c.atomic_json(out/'independent_numeric_audit.json',result)
print('AUDIT COMPLETE',out)
