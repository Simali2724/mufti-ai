import time,asyncio,sqlite3,os
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.agents.graph import graph_context,PersistentGraph
from app.api import routes_chat,routes_voice,routes_admin,routes_models,routes_feedback,routes_saved,routes_quiz,routes_attach
from app.core.config import ROOT,settings
from app.core.logging import logger
@asynccontextmanager
async def lifespan(app):
    async with graph_context(): pass
    app.state.graph=PersistentGraph();app.state.session_locks={}
    # Warm search in the background so the first question does not pay ~30 s of cold loading.
    if settings.warmup_on_start:
        from app.core.warmup import warm
        import asyncio as _asyncio
        app.state.warmup=_asyncio.create_task(warm())
    yield
app=FastAPI(title='Mufti AI · Your private Islamic library',lifespan=lifespan)
@app.exception_handler(sqlite3.Error)
async def storage_error(request,exc):
    code=getattr(exc,'sqlite_errorname',type(exc).__name__)
    logger.error('Conversation storage error: %s',code)
    return JSONResponse({'detail':'Conversation storage is temporarily unavailable. Please retry.','error_code':code},status_code=503)
# CORS: in cloud mode allow all origins; locally restrict to localhost
_cloud = settings.deploy_mode == 'cloud'
_origins = ['*'] if _cloud else [f'http://localhost:{settings.port}',f'http://127.0.0.1:{settings.port}']
app.add_middleware(CORSMiddleware,allow_origins=_origins,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Content-Type'])
rates=defaultdict(deque)
@app.middleware('http')
async def guard(request:Request,call_next):
    # In cloud mode skip origin guard (reverse proxy handles it)
    origin=request.headers.get('origin')
    if not _cloud and request.method not in ['GET','HEAD','OPTIONS'] and origin and origin not in [f'http://localhost:{settings.port}',f'http://127.0.0.1:{settings.port}']:
        return JSONResponse({'detail':'Local requests only'},status_code=403)
    if request.url.path in ['/chat','/voice','/transcribe','/ingest','/feedback','/saved','/quiz','/extract','/find']:
        key=request.client.host if request.client else 'local';now=time.monotonic();queue=rates[key]
        while queue and now-queue[0]>60: queue.popleft()
        if len(queue)>=15: return JSONResponse({'detail':'Please wait a minute before sending more requests'},status_code=429)
        queue.append(now)
    started=time.monotonic();result=await call_next(request)
    if request.method=='GET' and (request.url.path=='/' or request.url.path.endswith(('.js','.css','.html'))):
        result.headers['Cache-Control']='no-cache'
    logger.info('%s %s %s %.0fms',request.method,'/sessions/[id]' if '/sessions/' in request.url.path else request.url.path,result.status_code,(time.monotonic()-started)*1000)
    return result
_routers = [routes_chat.router,routes_admin.router,routes_models.router,routes_feedback.router,routes_saved.router,routes_quiz.router,routes_attach.router]
# Voice/whisper only in local mode (needs local model files)
if settings.deploy_mode != 'cloud':
    _routers.append(routes_voice.router)
for router in _routers: app.include_router(router)
app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True),name='frontend')
