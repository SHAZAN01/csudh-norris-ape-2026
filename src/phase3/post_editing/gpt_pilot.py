"""Dev-only GPT pilot. Exact jobs, immutable raw records, no invalid-output repair."""
import argparse, concurrent.futures, hashlib, importlib.util, json, os, random
import sys, threading, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL='gpt-4o-mini-2024-07-18'
ENDPOINT='https://api.openai.com/v1/chat/completions'

class FatalAPIError(RuntimeError): pass

def load_common(code_dir):
    sys.path.insert(0,str(code_dir))
    import pilot_common
    return pilot_common

class RateGate:
    def __init__(self, rps): self.lock=threading.Lock();self.next_at=0.;self.interval=1./rps
    def wait(self):
        with self.lock:
            slot=max(time.monotonic(),self.next_at);self.next_at=slot+self.interval
        time.sleep(max(0.,slot-time.monotonic()))

def payload_for(job):
    return dict(model=MODEL,messages=job['messages'],temperature=0,top_p=1,seed=42,
        max_tokens=1024,store=False,
        response_format=dict(type='json_schema',json_schema=dict(
            name='norris_'+job['strategy'].replace('-','_'),strict=True,schema=job['schema'])))

def cost(usage):
    # Conservative use of the published uncached rate; discounts are not assumed.
    return usage.get('prompt_tokens',0)*.15/1e6+usage.get('completion_tokens',0)*.60/1e6

def request_json(payload,key):
    req=urllib.request.Request(ENDPOINT,data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
    with urllib.request.urlopen(req,timeout=180) as r:
        return json.loads(r.read()),r.headers.get('x-request-id')

def run(args):
    c=load_common(args.code_dir)
    directory,manifest,jobs=c.load_prepared(args.pointer)
    c.require(manifest['config']['prompt_version']=='candidate_v2_explicit_diagnostics_not_frozen',
              'This continuation requires the reviewed candidate v2, not a different prompt.')
    key=os.environ.get('OPENAI_API_KEY','').strip()
    c.require(bool(key),'OPENAI_API_KEY is absent. Enable the Colab Secret; never paste it into code.')
    spec=dict(model=MODEL,endpoint=ENDPOINT,prepared_manifest_sha256=c.digest(manifest),
        payload_policy='Exact candidate-v2 messages and JSON schema; temperature 0; top_p 1; seed 42; max_tokens 1024; store false.',
        failure_policy='No selective retry for invalid model content; baseline fallback. Retry explicit transient HTTP errors only. Transport-uncertain jobs halt for review.',
        retries=5,workers=4,requests_per_second=4,runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=sys.version.split()[0],protocol_status='candidate_not_frozen')
    sha=c.digest(spec);out=directory/'gpt_runs'/sha[:16];records=out/'records';attempts=out/'attempts'
    records.mkdir(parents=True,exist_ok=True);attempts.mkdir(exist_ok=True)
    c.atomic_json(out/'run_spec.json',spec)
    selected=set(manifest['smoke_ids']) if args.stage=='smoke' else set(manifest['config']['pilot_ids'])
    jobs=[j for j in jobs if j['sentence_id'] in selected]
    c.require(len(jobs)==(24 if args.stage=='smoke' else 1200),'Unexpected pilot size.')
    # Byte counts deliberately overestimate message/schema token lengths for a preflight estimate.
    reserve=sum((len(c.canonical(j['messages']))+4*len(c.canonical(j['schema']))+1024)*.15/1e6+
                1024*.60/1e6 for j in jobs)
    c.require(reserve<=args.max_estimated_usd,
        f'Conservative stage estimate ${reserve:.2f} exceeds the local estimate ceiling. Review account limits before changing this setting.')
    print(f'GPT {args.stage}: {len(jobs)} jobs; conservative preflight estimate ${reserve:.2f}; account billing limits remain authoritative.',flush=True)
    done={};todo=[]
    for j in jobs:
        rp=records/(c.digest(j['job_key'])+'.json')
        if rp.exists():
            r=c.read_json(rp)
            c.require(r['run_sha256']==sha and r['job_sha256']==j['job_sha256'],'GPT saved configuration/job differs.')
            c.require(r['content_sha256']==c.digest({k:v for k,v in r.items() if k!='content_sha256'}),'GPT saved record checksum differs.')
            done[j['job_key']]=r
        else:
            marker=attempts/(c.digest(j['job_key'])+'.json')
            if marker.exists() and c.read_json(marker).get('state') in ['inflight','transport_uncertain','model_mismatch','unexpected_response']:
                raise FatalAPIError('A GPT request has uncertain completion status. Preserve its attempt record and send the evidence for review; no automatic repeat charge.')
            todo.append(j)
    gate=RateGate(4);halt=threading.Event()

    def worker(j):
        marker=attempts/(c.digest(j['job_key'])+'.json')
        prior=c.read_json(marker) if marker.exists() else {}
        events=prior.get('events',[])
        start_attempt=prior.get('attempt',-1)+1 if prior.get('state')=='http_error' else 0
        if start_attempt>5:
            halt.set();raise FatalAPIError('This job has exhausted its five HTTP retries. Preserve the attempts for review.')
        for attempt in range(start_attempt,6):
            if halt.is_set():raise FatalAPIError('Stopped after another request failed; saved records can be resumed.')
            gate.wait()
            base=dict(job_key=j['job_key'],job_sha256=j['job_sha256'],run_sha256=sha,
                attempt=attempt,created_utc=datetime.now(timezone.utc).isoformat())
            c.atomic_json(marker,dict(base,state='inflight',events=events))
            start=time.perf_counter()
            try:
                response,request_id=request_json(payload_for(j),key)
            except urllib.error.HTTPError as e:
                try:err=json.loads(e.read()).get('error',{})
                except Exception:err={}
                # Do not log error messages: authentication errors may quote part of a key.
                event=dict(http_status=e.code,error_type=err.get('type'),error_code=err.get('code'),attempt=attempt)
                events.append(event)
                transient=e.code in [408,409,429,500,502,503,504] and err.get('code') not in [
                    'insufficient_quota','credit_balance_exhausted','organization_spend_limit_exceeded','project_spend_limit_exceeded']
                c.atomic_json(marker,dict(base,state='http_error',events=events))
                if transient and attempt<5:
                    try:delay=float(e.headers.get('Retry-After',0))
                    except (ValueError,TypeError):delay=0
                    time.sleep(min(60,max(delay,2**attempt+random.random())))
                    continue
                halt.set()
                raise FatalAPIError(f'GPT stopped: HTTP {e.code}; error type={err.get("type")}; code={err.get("code")}. Check billing, model access or rate limits. No model replacement was made.') from None
            except Exception as e:
                c.atomic_json(marker,dict(base,state='transport_uncertain',error_class=type(e).__name__,events=events))
                halt.set();raise FatalAPIError('GPT transport result is uncertain. Review the retained attempt marker before repeating this job.') from None
            elapsed=(time.perf_counter()-start)*1000
            if response.get('model')!=MODEL:
                c.atomic_json(marker,dict(base,state='model_mismatch',returned_model=response.get('model'),request_id=request_id))
                halt.set();raise FatalAPIError('The API returned a different model identifier. Stop for protocol review.')
            choices=response.get('choices',[])
            if len(choices)!=1:
                c.atomic_json(marker,dict(base,state='unexpected_response',response=response,request_id=request_id))
                halt.set();raise FatalAPIError('Unexpected API response shape. Raw response retained for review.')
            choice=choices[0];message=choice.get('message',{});raw=message.get('content') or ''
            extracted=c.extract_response(raw,j['strategy'],j['query']['draft'],choice.get('finish_reason'))
            r=dict(job_key=j['job_key'],job_sha256=j['job_sha256'],run_sha256=sha,
                model_id=MODEL,returned_model=response['model'],model_revision=MODEL,
                system_fingerprint=response.get('system_fingerprint'),request_id=request_id,
                response_id=response.get('id'),response_created=response.get('created'),
                direction=j['direction'],strategy=j['strategy'],sentence_id=j['sentence_id'],
                messages=j['messages'],raw_completion=raw,raw_response=response,
                refusal=message.get('refusal'),finish_reason=choice.get('finish_reason'),
                prompt_token_count=response.get('usage',{}).get('prompt_tokens',0),
                completion_token_count=response.get('usage',{}).get('completion_tokens',0),
                usage=response.get('usage',{}),estimated_cost_usd_uncached=cost(response.get('usage',{})),
                request_latency_ms=elapsed,batch_amortized_ms=None,seed=42,retry_count=attempt,
                created_utc=datetime.now(timezone.utc).isoformat(),**extracted)
            r['content_sha256']=c.digest(r)
            c.atomic_json(records/(c.digest(j['job_key'])+'.json'),r)
            c.atomic_json(marker,dict(base,state='recorded',record_sha256=r['content_sha256'],request_id=request_id,events=events))
            return r

    if todo:
        # First pending job is an access/schema check before any concurrent requests.
        r=worker(todo[0]);done[r['job_key']]=r
        print('Exact GPT snapshot responded; first pilot job retained.',flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(worker,j) for j in todo[1:]]
            try:
                for f in concurrent.futures.as_completed(futures):
                    r=f.result();done[r['job_key']]=r
                    if len(done)%50==0:print('GPT saved:',len(done),'/',len(jobs),flush=True)
            except Exception:
                halt.set()
                for f in futures:f.cancel()
                raise
    ordered=[done[j['job_key']] for j in jobs]
    c.write_jsonl(out/(args.stage+'_outputs.jsonl'),ordered)
    summary=dict(stage=args.stage,planned=len(jobs),completed=len(ordered),
        json_parse_success=sum(r['json_parse_success'] for r in ordered),
        schema_valid=sum(r['schema_valid'] for r in ordered),usable=sum(r['usable'] for r in ordered),
        fallback_count=sum(r['fallback_used'] for r in ordered),
        prompt_tokens=sum(r['prompt_token_count'] for r in ordered),
        completion_tokens=sum(r['completion_token_count'] for r in ordered),
        estimated_cost_usd_uncached=sum(r['estimated_cost_usd_uncached'] for r in ordered),
        run_sha256=sha,protocol_status='candidate_not_frozen',status='generation_complete_quality_analysis_pending')
    c.atomic_json(out/(args.stage+'_summary.json'),summary)
    c.atomic_json(Path(args.pointer).with_name('gpt_latest_run.json'),dict(output_dir=str(out),run_sha256=sha,stage=args.stage))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pointer',required=True);p.add_argument('--code-dir',required=True)
    p.add_argument('--stage',choices=['smoke','full'],required=True);p.add_argument('--max-estimated-usd',type=float,default=5.)
    try:run(p.parse_args())
    except FatalAPIError as e:print(str(e),file=sys.stderr);sys.exit(2)
