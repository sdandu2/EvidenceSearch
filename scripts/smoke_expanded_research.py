"""Verify five-domain local inference and source integrity. Run from EvidenceSearch root.

Does not upload private abstracts or inspect any locked holdout.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = 'http://127.0.0.1:8000'
CORPUS = ROOT/'data'/'research'/'corpus_expanded_PRIVATE.jsonl'
GUIDED = ROOT/'data'/'research'/'guided_questions_unjudged.csv'
OUT = ROOT/'reports'/'experiments'/'research_local_integration_seed31'
OUT.mkdir(parents=True,exist_ok=True)


def fetch(path, payload=None):
    headers={'content-type':'application/json'} if payload is not None else {}
    req=Request(API+path,data=json.dumps(payload).encode('utf-8') if payload is not None else None,
                headers=headers,method='POST' if payload is not None else 'GET')
    start=time.perf_counter()
    with urlopen(req,timeout=200) as response:
        data=json.load(response)
    return data,round((time.perf_counter()-start)*1000,1)


def main():
    import csv
    by_id={}
    with CORPUS.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                p=json.loads(line)
                by_id[str(p['paper_id'])]=p
    domain_response, _=fetch('/api/research/domains')
    questions={}
    with GUIDED.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            questions.setdefault(row['domain'],row['question'])
    measurements=[]
    for field in domain_response['fields']:
        domain=field['name']
        query=questions.get(domain) or (field['suggested_questions'] or [])[0]
        response,wall_ms=fetch('/api/research/search',{'query':query,'domain':domain,'limit':10})
        for method, docs in response['methods'].items():
            assert docs, f'{domain}: empty {method} results'
            assert len({str(d['paper_id']) for d in docs})==len(docs)
            assert all(d['title']==by_id[str(d['paper_id'])]['title'] for d in docs)
            assert all(d['abstract']==by_id[str(d['paper_id'])]['abstract'] for d in docs)
        measurements.append({'domain':domain,'matched_source':True,
                             'returned_by_method':{k:len(v) for k,v in response['methods'].items()},
                             'wall_ms':wall_ms,'inference_ms':response['elapsed_ms']})
        print(f"{domain}: PASS | wall={wall_ms:.0f} ms | server={response['elapsed_ms']:.0f} ms")
    assert len(measurements)==5
    report={'status':'PASS','paper_count':len(by_id),'fields':5,
            'cold_and_warm_mixed':True,'wall_ms_median':statistics.median(m['wall_ms'] for m in measurements),
            'measurements':measurements,'public_abstract_rights':'NOT_VERIFIED'}
    (OUT/'smoke_local_expanded.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Saved aggregate-only report:',OUT/'smoke_local_expanded.json')


if __name__=='__main__':main()
