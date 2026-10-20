"""Score both complete dev pilots. No devtest reads and no protocol freeze."""
import argparse,collections,hashlib,json,math,re,statistics,sys
from pathlib import Path
from importlib.metadata import version,distributions

COMET_ID='Unbabel/wmt22-comet-da'
COMET_REV='2760a223ac957f30acfb18c8aa649b01cf1d75f2'

def numeric_tokens(text):
    # Digit-preservation screen only. Number words are deliberately not called corruptions.
    out=[]
    for value in re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?!\w)',text):
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',value):value=re.sub(r'[.,]','',value)
        else:value=value.replace(',','.')
        out.append(value.lstrip('0') or '0')
    return collections.Counter(out)

def preservation_flags(source,baseline,hypothesis):
    b=numeric_tokens(baseline);h=numeric_tokens(hypothesis)
    lost=list((b-h).elements())
    # Detect newly absent source capitalized tokens which the baseline retained.
    words=re.findall(r'[^\W\d_]+(?:[-\x27][^\W\d_]+)*',source,re.UNICODE)
    candidates={w.casefold() for w in words[1:] if len(w)>2 and w[0].isupper()}
    bw={w.casefold() for w in re.findall(r'[^\W\d_]+',baseline)}
    hw={w.casefold() for w in re.findall(r'[^\W\d_]+',hypothesis)}
    return dict(digit_change_flag=bool(b!=h),digit_loss_flag=bool(lost),lost_digit_tokens=lost,
        newly_absent_capitalized_source_tokens=sorted((candidates&bw)-hw),
        preservation_interpretation='Heuristic flags only: localization, number-word spelling and inflection may be legitimate; source review required.')

def paired_ci(deltas):
    import numpy as np
    a=np.asarray(deltas,dtype=float);rng=np.random.default_rng(42)
    draws=np.empty(10000)
    for k in range(0,10000,500):
        n=min(500,10000-k);idx=rng.integers(0,len(a),size=(n,len(a)));draws[k:k+n]=a[idx].mean(axis=1)*100
    return [float(v) for v in np.quantile(draws,[.025,.975])]

def aggregate(rows):
    n=len(rows);protect=[r for r in rows if r['baseline_comet_original_native']>=.90]
    edited_protect=[r for r in protect if r['text_edited']]
    over=[r for r in protect if r['text_edited'] and r['delta_comet_native']<-.02]
    pct=lambda k,d:100*k/d if d else None
    return dict(n=n,json_parse_success=sum(r['json_parse_success'] for r in rows),
        schema_valid=sum(r['schema_valid'] for r in rows),usable=sum(r['usable'] for r in rows),
        fallbacks=sum(r['fallback_used'] for r in rows),
        text_edited=sum(r['text_edited'] for r in rows),
        edit_rate_pct=pct(sum(r['text_edited'] for r in rows),n),
        COMET_points=statistics.mean(r['comet_native'] for r in rows)*100,
        baseline_COMET_points=statistics.mean(r['baseline_comet_native'] for r in rows)*100,
        delta_COMET_points=statistics.mean(r['delta_comet_native'] for r in rows)*100,
        delta_COMET_95CI_points=paired_ci([r['delta_comet_native'] for r in rows]),
        improved=sum(r['delta_comet_native']>.02 for r in rows),
        within_band=sum(-.02<=r['delta_comet_native']<=.02 for r in rows),
        harmed=sum(r['delta_comet_native']<-.02 for r in rows),
        protect_n=len(protect),edited_protect_n=len(edited_protect),overedited_protect_n=len(over),
        overedit_pct_all_protect=pct(len(over),len(protect)),overedit_pct_edited_protect=pct(len(over),len(edited_protect)),
        improve_pool_n=sum(r['baseline_comet_original_native']<.80 for r in rows),
        digit_change_flags=sum(r['digit_change_flag'] for r in rows),digit_loss_flags=sum(r['digit_loss_flag'] for r in rows),
        capitalized_token_flags=sum(bool(r['newly_absent_capitalized_source_tokens']) for r in rows),
        language_mismatch_flags=sum(r['language_mismatch_flag'] for r in rows),
        language_unknown=sum(r['language_predicted']=='unknown' for r in rows),
        reference_language_mismatch_flags=sum(r['reference_language_mismatch_flag'] for r in rows),
        length_anomaly_flags=sum(r['length_anomaly_flag'] for r in rows),
        NONE_with_text_change=sum(r['NONE_with_text_change'] for r in rows),
        latency_definition=rows[0]['latency_definition'],
        mean_latency_ms=statistics.mean(r['analysis_latency_ms'] for r in rows),
        median_latency_ms=statistics.median(r['analysis_latency_ms'] for r in rows))

def analyze(args):
    sys.path.insert(0,args.code_dir)
    import pilot_common as c
    import numpy as np
    from sacrebleu.metrics import BLEU,CHRF
    from langdetect import detect,DetectorFactory
    DetectorFactory.seed=0
    directory,manifest,jobs=c.load_prepared(args.pointer)
    c.require(manifest['config']['prompt_version']=='candidate_v2_explicit_diagnostics_not_frozen','Candidate mismatch.')
    gold=c.read_jsonl(directory/'evaluation_gold.jsonl');gmap={(r['direction'],r['sentence_id']):r for r in gold}
    c.require(len(gold)==len(gmap)==400,'Expected 400 unique offline dev query rows.')
    jmap={j['job_key']:j for j in jobs}
    paths={};all_records={}
    for model,ptr in [('llama3-8b','llama_latest_run.json'),('gpt4o-mini','gpt_latest_run.json')]:
        pointer=c.read_json(Path(args.pointer).with_name(ptr));run_dir=Path(pointer['output_dir'])
        c.require(pointer['stage']=='full','Both full pilots must finish before analysis.')
        records=c.read_jsonl(run_dir/'full_outputs.jsonl');c.require(len(records)==1200,'Incomplete full pilot.')
        c.require({r['job_key'] for r in records}==set(jmap),'Missing or duplicate pilot jobs.')
        for r in records:
            c.require(r['content_sha256']==c.digest({k:v for k,v in r.items() if k!='content_sha256'}),'Pilot record checksum differs.')
            j=jmap[r['job_key']];c.require(r['job_sha256']==j['job_sha256'],'Prompt job differs.')
            v=c.extract_response(r['raw_completion'],r['strategy'],j['query']['draft'],r['finish_reason'])
            for key in ['json_parse_success','schema_valid','usable','edited_translation','fallback_used']:
                c.require(v[key]==r[key],'Stored response extraction differs: '+r['job_key'])
            c.require(j['query']['draft']==gmap[(r['direction'],r['sentence_id'])]['baseline_translation'],'Offline baseline differs.')
        all_records[model]=records;paths[model]=str(run_dir)
    env={k:version(k) for k in ['torch','transformers','unbabel-comet','numpy','sacrebleu','langdetect','huggingface-hub']}
    spec=dict(prepared_manifest_sha256=c.digest(manifest),models={k:c.read_json(Path(v)/'run_spec.json') for k,v in paths.items()},
        COMET_model=COMET_ID,COMET_revision=COMET_REV,environment=env,seed=42,bootstrap_resamples=10000,
        bootstrap='Paired percentile dev diagnostic CI; no confirmatory p-values or superiority selection.',
        chrF_word_order=2,chrF_character_order=6,chrF_beta=2,BLEU_tokenizer='13a',
        scorer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        baseline_pool_rule='Use original pre-pilot baseline COMET: protect >=.90; improve <.80.',
        baseline_check='Re-score 400 pilot baselines with the pinned checkpoint; abort if original-score difference exceeds 1e-5 native.',
        flags='Digit multiset and source capitalized-token screens; number words/localization require source review; language ID is heuristic.',
        protocol_status='candidate_not_frozen')
    sha=c.digest(spec);out=directory/'pilot_analysis'/sha[:16];out.mkdir(parents=True,exist_ok=True)
    c.atomic_json(out/'analysis_spec.json',spec)
    resolved=sorted(f"{d.metadata['Name']}=={d.version}" for d in distributions() if d.metadata.get('Name'))
    (out/'requirements_evaluation_resolved.txt').write_text('\n'.join(resolved)+'\n')
    cache_dir=out/'comet_cache';cache_dir.mkdir(exist_ok=True)
    score_config=c.digest(dict(model=COMET_ID,revision=COMET_REV,environment=env))
    model=None
    def triplet_key(src,mt,ref):return c.digest(dict(src=src,mt=mt,ref=ref,scoring=score_config))
    triplets={}
    for g in gold:
        key=triplet_key(g['source_text'],g['baseline_translation'],g['reference_text'])
        triplets[key]=dict(src=g['source_text'],mt=g['baseline_translation'],ref=g['reference_text'])
    for records in all_records.values():
        for r in records:
            g=gmap[(r['direction'],r['sentence_id'])];mt=r['edited_translation']
            triplets[triplet_key(g['source_text'],mt,g['reference_text'])]=dict(src=g['source_text'],mt=mt,ref=g['reference_text'])
    scores={};pending=[]
    for key,triplet in triplets.items():
        file=cache_dir/(key+'.json')
        if file.exists():
            x=c.read_json(file);c.require(x['key']==key and math.isfinite(x['score']),'COMET cache differs.');scores[key]=x['score']
        else:pending.append((key,triplet))
    if pending:
        import torch
        from comet import load_from_checkpoint
        from huggingface_hub import snapshot_download
        c.require(torch.cuda.is_available(),'Use the A100 for COMET scoring.')
        snap=Path(snapshot_download(repo_id=COMET_ID,revision=COMET_REV,allow_patterns=['checkpoints/model.ckpt','hparams.yaml']))
        model=load_from_checkpoint(str(snap/'checkpoints/model.ckpt'));model.eval()
        encoder=getattr(getattr(model,'encoder',None),'model',None)
        c.atomic_json(out/'comet_provenance.json',dict(model=COMET_ID,revision=COMET_REV,
            encoder_config_commit=getattr(getattr(encoder,'config',None),'_commit_hash',None),gpu=torch.cuda.get_device_name(0)))
        for start in range(0,len(pending),128):
            chunk=pending[start:start+128]
            pred=model.predict([x[1] for x in chunk],batch_size=64,gpus=1,progress_bar=False,
                num_workers=2,length_batching=True,mc_dropout=0)
            vals=np.asarray(pred.scores,dtype=np.float64)
            c.require(len(vals)==len(chunk) and np.isfinite(vals).all(),'Invalid COMET predictions.')
            for (key,_),value in zip(chunk,vals):
                scores[key]=float(value);c.atomic_json(cache_dir/(key+'.json'),dict(key=key,score=float(value)))
            print('COMET cached:',start+len(chunk),'/',len(pending),flush=True)
    base_scores={}
    for g in gold:
        base_scores[(g['direction'],g['sentence_id'])]=scores[triplet_key(g['source_text'],g['baseline_translation'],g['reference_text'])]
    max_difference=max(abs(base_scores[(g['direction'],g['sentence_id'])]-g['baseline_comet_native']) for g in gold)
    c.atomic_json(out/'baseline_recheck.json',dict(n=400,max_abs_difference_native=max_difference,tolerance=1e-5))
    c.require(max_difference<=1e-5,'Pilot baseline COMET recheck differs. Preserve this evidence for review before interpreting deltas.')
    lidcache={}
    def lid(text):
        if text not in lidcache:
            try:lidcache[text]=detect(text)
            except Exception:lidcache[text]='unknown'
        return lidcache[text]
    expected={'eng_Latn':'en','tgl_Latn':'tl','spa_Latn':'es'}
    details=[];groups={};cases=[]
    for model_name,records in all_records.items():
        for r in records:
            g=gmap[(r['direction'],r['sentence_id'])];hyp=r['edited_translation'];bs=base_scores[(r['direction'],r['sentence_id'])]
            score=scores[triplet_key(g['source_text'],hyp,g['reference_text'])]
            ratio=len(hyp.split())/max(1,len(g['source_text'].split()));target=expected[r['direction'].split('->')[1]]
            predlang=lid(hyp);reflang=lid(g['reference_text'])
            latency=r.get('request_latency_ms') if model_name=='gpt4o-mini' else r['batch_amortized_ms']
            d=dict(model=model_name,job_key=r['job_key'],direction=r['direction'],strategy=r['strategy'],sentence_id=r['sentence_id'],
                source_text=g['source_text'],reference_text=g['reference_text'],baseline_translation=g['baseline_translation'],
                edited_translation=hyp,raw_completion=r['raw_completion'],diagnostics=r['diagnostics'],
                baseline_comet_original_native=g['baseline_comet_native'],baseline_comet_native=bs,comet_native=score,
                delta_comet_native=score-bs,text_edited=hyp!=g['baseline_translation'],
                json_parse_success=r['json_parse_success'],schema_valid=r['schema_valid'],usable=r['usable'],
                fallback_used=r['fallback_used'],validation_error=r['validation_error'],finish_reason=r['finish_reason'],
                language_predicted=predlang,language_expected=target,language_mismatch_flag=predlang not in [target,'unknown'],
                reference_language_mismatch_flag=reflang not in [target,'unknown'],
                output_source_word_ratio=ratio,length_anomaly_flag=ratio>2.5 or ratio<.4,
                NONE_with_text_change=any(x.get('error_type')=='NONE' for x in r['diagnostics']) and hyp!=g['baseline_translation'],
                analysis_latency_ms=latency,latency_definition='HTTP request wall time' if model_name=='gpt4o-mini' else 'batch-amortized generation time; model initialization excluded',
                **preservation_flags(g['source_text'],g['baseline_translation'],hyp))
            details.append(d)
        for direction in sorted({r['direction'] for r in records}):
            for strategy in c.STRATEGIES:
                subset=[r for r in details if r['model']==model_name and r['direction']==direction and r['strategy']==strategy]
                c.require(len(subset)==100,'Every pilot condition must contain 100 items, including fallbacks.')
                a=aggregate(subset);hyp=[r['edited_translation'] for r in subset];refs=[[r['reference_text'] for r in subset]]
                b=BLEU(tokenize='13a');f=CHRF(char_order=6,word_order=2,beta=2)
                a.update(BLEU=b.corpus_score(hyp,refs).score,chrFpp=f.corpus_score(hyp,refs).score,
                    BLEU_signature=str(b.get_signature()),chrF_signature=str(f.get_signature()))
                groups[f'{model_name}/{direction}/{strategy}']=a
                chosen=sorted(subset,key=lambda r:r['delta_comet_native'])[:3]+sorted(subset,key=lambda r:r['delta_comet_native'],reverse=True)[:3]+[r for r in subset if r['fallback_used']][:3]
                cases.extend(chosen)
    c.write_jsonl(out/'segment_analysis.jsonl',details)
    c.write_jsonl(out/'review_cases.jsonl',list({(x['model'],x['job_key']):x for x in cases}.values()))
    summary=dict(status='full_dev_pilots_scored_case_review_and_configuration_finalization_pending',groups=groups,
        n_records=len(details),unique_scored_triplets=len(triplets),analysis_sha256=sha,
        baseline_recheck_max_abs_native=max_difference,protocol_status='candidate_not_frozen',
        freeze_declared=False,devtest_opened_by_this_workflow=False,
        pending=['Investigator review of error examples and failure analysis','Final ICAI overlap audit verification','Record final configuration after acceptance items are met; obtain PI Phase 3 sign-off'],
        flags_are_not_gold_errors=True,statistics='Exploratory dev CIs only; no confirmatory main-experiment conclusions.')
    c.atomic_json(out/'pilot_summary.json',summary)
    c.atomic_json(out/'candidate_configuration.json',dict(prepared=manifest['config'],model_specs=spec['models'],analysis=spec,
        status='candidate_not_frozen',freeze_declared=False))
    text=['# Norris Phase Report 3 - measured pilot evidence draft','',
        '**Status: full development pilots generated and scored; case review and configuration finalization pending. Protocol not frozen.**','',
        'This draft is generated from actual saved dev outputs. It does not certify completion of the overlap audit or authorize Phase 4.',
        '', '## Scope and procedure','',
        'Same 100 aligned dev IDs per direction and strategy, seed 42. Llama 3 8B Instruct and the exact GPT-4o Mini snapshot each contribute 1,200 planned outcomes. Invalid outputs remain in the population through labeled baseline fallback. References are offline, except for a retrieved nonpilot demonstration reference.',
        '', 'Candidate v2 was retained after the reviewed smoke showed five diagnostic-validation fallbacks. A perfect schema-validity rate was not an acceptance threshold. The full pilot measures this failure mode; no invalid content was repaired or selectively regenerated.',
        '', '## Condition results','',
        '| Model / direction / strategy | N | Usable | Fallback | BLEU | chrF++ | COMET x100 | Delta points | 95% dev CI |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for k,a in groups.items():
        lo,hi=a['delta_COMET_95CI_points'];text.append(f"| {k} | {a['n']} | {a['usable']} | {a['fallbacks']} | {a['BLEU']:.3f} | {a['chrFpp']:.3f} | {a['COMET_points']:.3f} | {a['delta_COMET_points']:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
    text+=['','## Editing and harm','',
        '| Condition | Edited /100 | Improved | Within band | Harmed | Protect N | Overedited protect |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for k,a in groups.items():text.append(f"| {k} | {a['text_edited']} | {a['improved']} | {a['within_band']} | {a['harmed']} | {a['protect_n']} | {a['overedited_protect_n']} |")
    text+=['','Native COMET bands: improved >0.02, within [-0.02,+0.02], harmed <-0.02. Protect-pool over-editing also requires original baseline COMET >=0.90 and a textual edit. A native 0.02 equals 2 reported points. Within-band does not mean textually unchanged or human-equivalent.',
        '', '## Failure and interpretation limits','',
        'See pilot_summary.json and segment_analysis.jsonl for parse/schema rates, fallback, preservation flags, language checks, timing and pool denominators. review_cases.jsonl contains extreme deltas and failure examples for investigator review. Digit and capitalized-token screens are not confirmed corruptions; number words and localization require source-based review. Language detection is a heuristic with reference mismatch rates provided.',
        '', 'The 10,000-resample paired percentile intervals describe dev diagnostics. Main-experiment Holm-corrected hypothesis testing remains future work. No result here establishes performance on dialectal, heritage, code-switched or Los Angeles community Spanish.',
        '', '## Acceptance and freeze','',
        'Review raw examples, disclose diagnostic failures and methodological changes, verify the final ICAI overlap audit, and resolve any scope decision requiring explicit PI approval. Then finalize the configuration under the PI instructions and submit Report 3 for Phase 3 sign-off. candidate_configuration.json records exact current settings and explicitly does not declare a freeze. No devtest scoring or main execution is performed.',
        '', 'Analysis signature: '+sha]
    (out/'Report3_Measured_Pilot_DRAFT.md').write_text('\n'.join(text)+'\n')
    c.atomic_json(Path(args.pointer).with_name('analysis_latest_run.json'),dict(output_dir=str(out),analysis_sha256=sha))
    print('ANALYSIS COMPLETE:',out,flush=True)
    print('Return the evidence ZIP for case review and the final Report 3. Protocol remains unfrozen.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pointer',required=True);p.add_argument('--code-dir',required=True)
    analyze(p.parse_args())
