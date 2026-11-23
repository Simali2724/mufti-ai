import asyncio,json,re,time
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import StreamingResponse
from app.core.schemas import ChatRequest
from app.agents.graph import ask
router=APIRouter()
def validate_session(s):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',s): raise HTTPException(400,'Invalid session ID')
def sse(event,data):
    return f'event: {event}\ndata: {json.dumps(data,ensure_ascii=False)}\n\n'
@router.post('/chat')
async def chat(body:ChatRequest,request:Request):
    from app.llm.preferences import request_api_keys
    user_gemini_key = request.headers.get('x-gemini-key', '').strip()
    if user_gemini_key:
        request_api_keys.set({'gemini': user_gemini_key})
    # Streams status, a live draft preview of the explanation as it is written, and finally the
    # checked answer in `done`, which always replaces the draft (the audit may have corrected it).
    lock=request.app.state.session_locks.setdefault(body.session_id,asyncio.Lock())
    queue=asyncio.Queue()
    async def run():
        async with lock: return await ask(request.app.state.graph,body,progress=queue.put if body.stream else None)
    if not body.stream: return await run()
    async def events():
        started=time.monotonic();last_tick=0
        task=asyncio.create_task(run())
        try:
            yield sse('status',{'message':'Searching the book…'})
            while not task.done() or not queue.empty():
                try:
                    update=await asyncio.wait_for(queue.get(),timeout=1)
                    kind=update.get('kind')
                    if kind=='draft': yield sse('draft',{'text':update['text']})
                    elif kind=='draft_reset': yield sse('draft_reset',{})
                    else: yield sse('status',update)
                except asyncio.TimeoutError: pass
                elapsed=int(time.monotonic()-started)
                if not task.done() and elapsed>=last_tick+10:
                    last_tick=elapsed
                    yield sse('status',{'message':f'Preparing your answer · {elapsed}s elapsed'})
            result=await task
            yield 'event: done\ndata: '+result.model_dump_json()+'\n\n'
        except Exception:
            yield sse('error',{'message':'Request failed. Check local server logs.'})
        finally:
            if not task.done(): task.cancel()
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@router.get('/sessions/{session_id}')
async def session(session_id:str,request:Request):
    validate_session(session_id)
    state=await request.app.state.graph.aget_state({'configurable':{'thread_id':session_id}})
    return {'session_id':session_id,'history':state.values.get('history',[])}
@router.delete('/sessions/{session_id}')
async def wipe(session_id:str,request:Request):
    validate_session(session_id)
    lock=request.app.state.session_locks.setdefault(session_id,asyncio.Lock())
    async with lock: await request.app.state.graph.checkpointer.adelete_thread(session_id)
    from app.retrieval.vector_store import _query_vectors
    _query_vectors.clear()
    return {'deleted':True}
