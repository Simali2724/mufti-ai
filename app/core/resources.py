import asyncio
from contextlib import asynccontextmanager
# Serialize model work so embedding and generation do not compete for a small GPU.
ollama_lock=asyncio.Lock()
current_model=None
interactive_count=0
async def select_model(client,model):
    global current_model
    from app.core.config import settings
    previous=current_model
    # Only unload a model this process actually selected. Guessing a default
    # can block embeddings when that unrelated chat model is not installed.
    if previous is not None and previous!=model:
        r=await client.post(settings.ollama_base_url+'/api/generate',json={'model':previous,'keep_alive':0})
        # A removed model is already unloaded; other failures remain visible.
        if r.status_code!=404: r.raise_for_status()
    current_model=model
@asynccontextmanager
async def interactive_work():
    global interactive_count
    interactive_count+=1
    try: yield
    finally: interactive_count-=1
