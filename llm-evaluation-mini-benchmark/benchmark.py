"""Scoring and reporting logic for the LLM Evaluation Mini-Benchmark."""
from __future__ import annotations
import csv, json, re, subprocess, sys, time
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / 'data' / 'benchmark.json'
REPORTS_DIR = ROOT / 'reports'

def load_benchmark(path: Path = DATA_PATH):
    data=json.loads(path.read_text(encoding='utf-8')); ids=[x['id'] for x in data]
    if len(ids)!=len(set(ids)): raise ValueError('Benchmark IDs must be unique.')
    for item in data:
        for k in ('id','category','prompt','rubric','checks'):
            if k not in item: raise ValueError(f'Benchmark item missing {k}: {item}')
    return data

def normalize(text): return re.sub(r'\s+',' ',text.strip().lower())
def extract_code(text):
    m=re.search(r'```(?:python)?\s*(.*?)```',text,re.S|re.I); return m.group(1).strip() if m else text.strip()

def _python_test_response(response, checks):
    code=extract_code(response); harness = r"""
import json, sys
payload=json.loads(sys.stdin.read()); namespace={'__builtins__':__builtins__}
try:
 exec(payload['code'],namespace,namespace); fn=namespace.get(payload['function'])
 if not callable(fn): raise ValueError('Required function not found')
 outcomes=[]
 for args,expected in payload['tests']:
  try:
   actual=fn(*args) if isinstance(args,list) else fn(args)
   outcomes.append({'passed':actual==expected,'expected':expected,'actual':repr(actual)})
  except Exception as exc: outcomes.append({'passed':False,'expected':expected,'error':type(exc).__name__+': '+str(exc)})
 print(json.dumps(outcomes))
except Exception as exc: print(json.dumps({'error':type(exc).__name__+': '+str(exc)}))
"""
    payload={'code':code,'function':checks['function'],'tests':checks['tests']}
    try:
        p=subprocess.run([sys.executable,'-I','-c',harness],input=json.dumps(payload),text=True,capture_output=True,timeout=2)
        parsed=json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {'error':p.stderr[-500:]}
        if isinstance(parsed,dict) and 'error' in parsed: return 0.0,'Code failed to load or required function missing.',{'error':parsed['error']}
        passed=sum(bool(x.get('passed')) for x in parsed); total=len(checks['tests'])
        return passed/total if total else 0.0,f'{passed}/{total} deterministic tests passed.',{'tests':parsed,'passed':passed,'total':total}
    except subprocess.TimeoutExpired: return 0.0,'Code timed out during tests.',{'error':'timeout'}
    except Exception as exc: return 0.0,f'Test harness error: {exc}',{'error':str(exc)}

def score_response(item, response):
    c=item['checks']; kind=c['type']; text=response.strip(); low=text.lower(); score=0.0; reason=''; details={}
    if kind=='exact_json':
        try:
            score=1.0 if json.loads(text)==c['expected'] else 0.0; reason='Exact JSON structure matches.' if score else 'JSON parsed but did not match expected object.'
        except json.JSONDecodeError: reason='Response is not valid standalone JSON.'
    elif kind=='word_count':
        words=text.split(); count_ok=len(words)==c['count']; kw=all(k.lower() in low for k in c.get('keywords',[])); score=1.0 if count_ok and kw else (0.5 if count_ok or kw else 0.0); reason=f'Word count {len(words)}/{c["count"]}; required keywords {"present" if kw else "missing"}.'
    elif kind=='bullets':
        lines=[x.strip() for x in text.splitlines() if x.strip()]; bullets=[x for x in lines if re.match(r'^([-*•]|\d+[.)])\s+',x)]; kw=all(k.lower() in low for k in c.get('keywords',[])); score=1.0 if len(lines)==c['count'] and len(bullets)==c['count'] and kw else (0.5 if len(bullets)==c['count'] else 0.0); reason=f'{len(bullets)} bullet lines; expected {c["count"]}.'
    elif kind=='exact_lines':
        actual=[x.strip() for x in text.splitlines() if x.strip()]; score=1.0 if actual==c['expected'] else 0.0; reason='Lines exactly match expected CSV.' if score else 'CSV lines differ from expected.'
    elif kind=='contains_any':
        found=[x for x in c['expected'] if x.lower() in low]; score=1.0 if found else 0.0; reason='Expected indicator found: '+', '.join(found) if found else 'No expected indicator found.'; details['matched_indicators']=found
    elif kind=='number_range':
        vals=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',text)]; valid=[x for x in vals if c['min']<=x<=c['max']]; score=1.0 if valid else 0.0; reason=f'Found acceptable numeric answer {valid[0]}.' if valid else 'No number in the accepted range.'; details['numbers_found']=vals
    elif kind=='exact_normalized': score=1.0 if normalize(text).strip(' .!?')==normalize(c['expected']) else 0.0; reason='Normalized answer matches.' if score else 'Normalized answer does not match.'
    elif kind=='python_tests': score,reason,details=_python_test_response(text,c)
    elif kind=='summary_coverage':
        found=[k for k in c['keywords'] if k in low]; coverage=len(found)/len(c['keywords']); score=1.0 if coverage==1 else (0.5 if coverage>=.75 else 0.0); reason=f'Summary keyword coverage {len(found)}/{len(c["keywords"])}.'; details['matched_keywords']=found
    else: raise ValueError(f'Unknown check type: {kind}')
    return {'id':item['id'],'category':item['category'],'difficulty':item.get('difficulty','unspecified'),'score':round(float(score),4),'reason':reason,'response':response,'details':details}

def evaluate(responses, model_name='Unnamed model', benchmark=None):
    benchmark=benchmark or load_benchmark(); results=[]; missing=[]
    for item in benchmark:
        if item['id'] not in responses: missing.append(item['id']); response=''
        else: response=responses[item['id']]
        row=score_response(item,response); row['model']=model_name; row['rubric']=item['rubric']
        if item['id'] in missing: row['reason']='Missing response; scored 0.'
        results.append(row)
    groups={}
    for r in results: groups.setdefault(r['category'],[]).append(r['score'])
    return {'model':model_name,'benchmark_version':'1.0','total_items':len(benchmark),'responses_provided':len(responses),'missing_ids':missing,'overall_score':round(sum(r['score'] for r in results)/len(results),4) if results else 0,'category_scores':{k:round(sum(v)/len(v),4) for k,v in sorted(groups.items())},'results':results}

def read_responses_jsonl(path):
    responses={}
    for n,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try:
            row=json.loads(line)
            if not isinstance(row.get('id'),str) or not isinstance(row.get('response'),str): raise ValueError("Each line requires string fields 'id' and 'response'.")
            if row['id'] in responses: raise ValueError(f'Duplicate id {row["id"]}')
            responses[row['id']]=row['response']
        except Exception as exc: raise ValueError(f'Invalid JSONL line {n}: {exc}') from exc
    return responses

def write_outputs(ev, run_id=None):
    REPORTS_DIR.mkdir(parents=True,exist_ok=True); run_id=run_id or time.strftime('%Y%m%d_%H%M%S'); safe=re.sub(r'[^A-Za-z0-9_-]+','_',ev['model']).strip('_') or 'model'; stem=f'{safe}_{run_id}'
    jp=REPORTS_DIR/f'results_{stem}.json'; cp=REPORTS_DIR/f'scores_{stem}.csv'; mp=REPORTS_DIR/f'report_{stem}.md'; jp.write_text(json.dumps(ev,indent=2,ensure_ascii=False),encoding='utf-8')
    with cp.open('w',newline='',encoding='utf-8') as f:
        fields=['model','id','category','difficulty','score','reason']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows({k:r.get(k,'') for k in fields} for r in ev['results'])
    lines=[f"# LLM Evaluation Report — {ev['model']}",'',f"- Benchmark version: {ev['benchmark_version']}",f"- Items: {ev['total_items']}",f"- Responses provided: {ev['responses_provided']}",f"- Missing responses: {len(ev['missing_ids'])}",f"- Overall rule-based score: **{ev['overall_score']:.1%}**",'','## Category scores','','| Category | Mean score |','|---|---:|']
    lines += [f'| {k} | {v:.1%} |' for k,v in ev['category_scores'].items()]; lines += ['','## Failure analysis','']; failures=[r for r in ev['results'] if r['score']<1]
    lines += [f"- **{r['id']} ({r['category']}, score {r['score']:.2f})** — {r['reason']}" for r in failures] if failures else ['No item received a score below 1.0 under the configured checks.']
    lines += ['','## Interpretation and limitations','','Scores reflect explicit deterministic checks, not a universal measure of model quality. Keyword checks can reward superficial matches and miss nuanced errors; coding tests cover only selected cases. Review outputs manually, especially for safety and factuality. The sample is small and may not generalize.','']; mp.write_text('\n'.join(lines),encoding='utf-8')
    return {'json':str(jp),'csv':str(cp),'report':str(mp)}

def compare_evaluations(evaluations,names=None,run_id=None):
    if len(evaluations)<2: raise ValueError('Comparison requires at least two evaluations.')
    names=names or [e['model'] for e in evaluations]; run_id=run_id or time.strftime('%Y%m%d_%H%M%S'); REPORTS_DIR.mkdir(parents=True,exist_ok=True); cp=REPORTS_DIR/f'comparison_{run_id}.csv'; mp=REPORTS_DIR/f'comparison_{run_id}.md'; ids=[r['id'] for r in evaluations[0]['results']]; maps=[{r['id']:r for r in e['results']} for e in evaluations]
    with cp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['id','category']+names)
        for iid in ids: w.writerow([iid,maps[0][iid]['category']]+[m.get(iid,{}).get('score',0) for m in maps])
    lines=['# Model Comparison','','| Model | Overall score |','|---|---:|']+[f"| {n} | {e['overall_score']:.1%} |" for n,e in zip(names,evaluations)]; cats=sorted(set().union(*(e['category_scores'].keys() for e in evaluations))); lines+=['','## Category comparison','','| Category | '+' | '.join(names)+' |','|---|'+'|'.join(['---:']*len(names))+'|']
    for cat in cats: lines.append('| '+cat+' | '+' | '.join(f"{e['category_scores'].get(cat,0):.1%}" for e in evaluations)+' |')
    lines+=['','## Per-item disagreements','']
    for iid in ids:
        scores=[m.get(iid,{}).get('score',0) for m in maps]
        if max(scores)-min(scores)>=.5: lines.append(f"- **{iid}**: "+'; '.join(f'{n}={s:.2f}' for n,s in zip(names,scores)))
    lines+=['','Scores are rule-based proxies. Check matched settings, manually inspect failures, and avoid treating this small benchmark as a definitive ranking.','']; mp.write_text('\n'.join(lines),encoding='utf-8'); return {'csv':str(cp),'report':str(mp)}
