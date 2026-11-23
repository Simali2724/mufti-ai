import asyncio,tempfile,os
from fastapi import APIRouter,Request,UploadFile,File,Form,HTTPException
from app.voice.stt import transcribe
from app.core.schemas import ChatRequest
from app.agents.graph import ask
router=APIRouter()
MAX_AUDIO=20*1024*1024
LANGUAGES=('auto','Hindi','Urdu','English','Hinglish')
@router.post('/transcribe')
async def transcribe_only(audio:UploadFile=File(...),language_hint:str=Form('auto')):
    """Speech -> text ONLY (2026-11-17). The UI puts the text into the question box so the reader
    can check or correct it and press Send; nothing is asked or answered here. A wrong word from
    the recogniser (common with Urdu/Hinglish) would otherwise go straight into a minutes-long answer."""
    data=await audio.read(MAX_AUDIO+1)
    if len(data)>MAX_AUDIO: raise HTTPException(413,'Audio limit is 20 MB')
    if not data: raise HTTPException(422,'No audio received')
    path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm',delete=False) as f: f.write(data);path=f.name
        text,detected=await asyncio.to_thread(transcribe,path,language_hint if language_hint in LANGUAGES else None)
        return {'transcript':text,'detected_language':detected}
    except RuntimeError as e: raise HTTPException(503,str(e))
    except Exception:
        from app.core.logging import logger
        logger.exception('Local voice transcription failed')
        raise HTTPException(503,'Local speech transcription failed. Check the local speech model and audio dependencies.')
    finally:
        if path: os.unlink(path)
@router.post('/voice')
async def voice(request:Request,audio:UploadFile=File(...),session_id:str=Form('default'),language_hint:str=Form('auto'),answer_style:str=Form('detailed')):
    data=await audio.read(20*1024*1024+1)
    if len(data)>20*1024*1024: raise HTTPException(413,'Audio limit is 20 MB')
    path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm',delete=False) as f: f.write(data);path=f.name
        text,detected=await asyncio.to_thread(transcribe,path,language_hint if language_hint in LANGUAGES else None)
        if not text: raise HTTPException(422,'No speech detected')
        body=ChatRequest(question=text,session_id=session_id,language_hint=language_hint,answer_style=answer_style)
        lock=request.app.state.session_locks.setdefault(session_id,asyncio.Lock())
        async with lock: result=await ask(request.app.state.graph,body,'audio')
        return {'transcript':text,'detected_voice_language':detected,**result.model_dump()}
    except RuntimeError as e: raise HTTPException(503,str(e))
    except ValueError as e: raise HTTPException(422,str(e))
    except HTTPException: raise
    except Exception:
        from app.core.logging import logger
        logger.exception('Local voice transcription failed')
        raise HTTPException(503,'Local speech transcription failed. Check the local speech model and audio dependencies.')
    finally:
        if path: os.unlink(path)
