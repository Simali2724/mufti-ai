import asyncio,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.agents.graph import graph_context,ask
from app.core.schemas import ChatRequest
from app.ingestion.indexer import get_page
from app.core.language import detect
async def main():
    rows=[]
    async with graph_context() as graph:
        for n,line in enumerate(Path(__file__).with_name('golden_questions.jsonl').read_text(encoding='utf-8').splitlines()):
            case=json.loads(line);r=await ask(graph,ChatRequest(question=case['question'],language_hint=case.get('language','auto'),session_id=f'eval-{time.time_ns()}'))
            valid=all(c.excerpt in (get_page(c.book_id,c.page) or {}).get('text','') for c in r.citations)
            row={**case,**r.model_dump(),'citations_valid':bool(r.citations) and valid,'language_match':r.language==detect(case['question'],case.get('language','auto'))}
            rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    summary={'count':len(rows),'answered_with_verified_evidence_rate':sum(r['grounded'] for r in rows)/len(rows),'citation_validity_rate':sum(r['citations_valid'] for r in rows)/max(1,sum(bool(r['citations']) for r in rows)),'language_match_rate':sum(r['language_match'] for r in rows)/len(rows),'average_latency_ms':sum(r['latency_ms'] for r in rows)/len(rows),'providers':sorted({r['provider_used'] for r in rows})}
    print(json.dumps(summary,indent=2));Path(__file__).with_name('results.json').write_text(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': asyncio.run(main())
