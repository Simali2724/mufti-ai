import asyncio
import httpx
from json_repair import repair_json
from app.core.config import settings,config
from app.core.logging import logger
from app.llm.providers import complete
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.structured import SCHEMAS
from app.llm.progress import report
from app.core import diagnostics
from app.llm.preferences import get_preferences,build_provider_order,request_preferences,request_trace
class ProviderUnavailable(RuntimeError): pass
breaker=CircuitBreaker(config['circuit_failures'],config['circuit_cooldown'])
# Last real outcome per provider, so the UI can separate "key configured" from "works".
_outcomes={}
def last_outcome(provider): return _outcomes.get(provider,'')
def note_outcome(provider,outcome): _outcomes[provider]=outcome
def has_key(provider):
    from app.llm.preferences import request_api_keys
    custom = (request_api_keys.get() or {}).get(provider, '')
    if custom and custom.strip(): return True
    attribute={'anthropic':'anthropic_api_key','openai':'openai_api_key','gemini':'google_api_key'}.get(provider)
    return provider=='ollama' or bool(getattr(settings,attribute,'').strip())
def retryable(error):
    if isinstance(error,httpx.HTTPStatusError):
        return error.response.status_code in (408,429) or error.response.status_code>=500
    return isinstance(error,(httpx.TransportError,TimeoutError))
# Status codes after which another model of the SAME provider is worth trying before falling
# through to the next provider: overloaded (503), per-model quota (429), retired model (404).
# Measured 2026-11-16: gemini-2.5-flash answered 503 (overloaded) while gemini-3.5-flash on the
# same key answered normally.
SWITCH_MODEL=(404,429,503)
# Free-tier Gemini quotas are PER MODEL and some are tiny (measured 2026-11-16:
# gemini-2.5-flash = 20 requests/day). A model that reported a quota with a retry delay is
# skipped until then, instead of spending a failed call on it for every request.
_model_cooldown={}
def cooldown_seconds(exc):
    try:
        details=exc.response.json().get('error',{}).get('details',[])
        for d in details:
            if 'retryDelay' in d: return float(str(d['retryDelay']).rstrip('s'))
    except Exception: pass
    return 60.0
def model_available(provider,model):
    import time
    return _model_cooldown.get((provider,model),0)<=time.monotonic()
def models_for(provider,selected,task='',only_preferred=False):
    alternates=config.get(provider+'_alternates') or []
    # A judging task can run on a lighter model, keeping the main model's quota for answers.
    preferred=((config.get('task_models') or {}).get(task) or {}).get(provider) or []
    # only_preferred: a task that must run on exactly its listed models (the strong audit must not
    # silently drift onto the answering model's quota or onto a lite model; it has its own fallback).
    if only_preferred and preferred:
        ready=[m for m in preferred if model_available(provider,m)]
        return ready
    ordered=list(dict.fromkeys([*preferred,selected,*alternates]))
    ready=[m for m in ordered if m and model_available(provider,m)]
    return ready or [selected]
class ChatModel:
    def __init__(self,task,local_ok=True,only_preferred=False):
        self.task=task
        self.only_preferred=only_preferred
        # A judging task (the explanation audit) must not fall back to the local 1.7B model:
        # measured 2026-11-16, its "fixes" overwrote a correct cloud answer with a repeated
        # meaningless sentence. No audit is better than that audit.
        self.local_ok=local_ok
    async def _route(self,call,on_failure=None):
        preferences=request_preferences.get() or get_preferences()
        order=build_provider_order(preferences)
        errors=[]
        for position,provider in enumerate(order):
            selected=preferences.models[provider]
            if provider=='ollama' and not self.local_ok:
                errors.append('ollama:not_used_for_'+self.task);continue
            if not has_key(provider):
                await report(self.task,provider,selected,'skipped: key missing')
                diagnostics.note_model(self.task,provider,selected,'skipped','key missing')
                errors.append(provider+':not_configured');continue
            if provider!='ollama' and not breaker.available(provider):
                await report(self.task,provider,selected,'skipped: temporarily unavailable')
                diagnostics.note_model(self.task,provider,selected,'skipped','temporarily unavailable')
                errors.append(provider+':cooldown');continue
            candidates=models_for(provider,selected,self.task,self.only_preferred) if provider!='ollama' else [selected]
            if not candidates:
                errors.append(provider+':no_preferred_model_available');continue
            for index,model in enumerate(candidates):
                switch=False
                for attempt in range(2):
                    try:
                        await report(self.task,provider,model,'running')
                        result=await call(provider,model)
                        breaker.success(provider);note_outcome(provider,'ok');logger.info('task=%s provider=%s model=%s',self.task,provider,model)
                        trace=request_trace.get()
                        if trace is not None: trace.append({'task':self.task,'provider':provider,'model':model,'fallback':position>0 or index>0})
                        await report(self.task,provider,model,'complete')
                        diagnostics.note_model(self.task,provider,model,'complete','')
                        return result,provider
                    except Exception as exc:
                        status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
                        if on_failure: await on_failure()
                        await report(self.task,provider,model,'failed: '+str(status or type(exc).__name__))
                        diagnostics.note_model(self.task,provider,model,'failed',str(status or type(exc).__name__))
                        errors.append(f'{provider}:{status or type(exc).__name__}')
                        # A dedicated-model task (only_preferred, e.g. the strong audit) failing says nothing
                        # about the provider: measured 2026-11-18, its HTTP 400 tripped Gemini, the lite audit
                        # was skipped and the NEXT question fell back to the local model (216 s, unverified).
                        if not self.only_preferred: breaker.fail(provider)
                        note_outcome(provider,('HTTP '+str(status)) if status else type(exc).__name__)
                        logger.warning('task=%s provider=%s model=%s failure=%s',self.task,provider,model,status or type(exc).__name__)
                        if status==429:
                            import time
                            _model_cooldown[(provider,model)]=time.monotonic()+min(cooldown_seconds(exc),6*3600)
                        # A timeout also moves to the next model: measured 2026-11-16, one
                        # alternate timed out on every call, and retrying it cost 6 minutes.
                        if (status in SWITCH_MODEL or isinstance(exc,httpx.TimeoutException)) and index<len(candidates)-1:
                            switch=True;break
                        if attempt==0 and retryable(exc):
                            await asyncio.sleep(.5);continue
                        break
                if not switch: break
            if provider!='ollama' and not self.only_preferred: breaker.trip(provider)
        raise ProviderUnavailable('No provider available: '+', '.join(errors))
    async def invoke(self,system,user,structured=False):
        async def call(provider,model):
            result=await complete(provider,model,[{'role':'system','content':system},{'role':'user','content':user}],structured,SCHEMAS.get(self.task),self.task)
            if structured:
                result=repair_json(result,return_objects=True)
                if not isinstance(result,dict): raise ValueError('Invalid structured output')
            return result
        return await self._route(call)
    async def stream(self,system,user,on_token=None):
        """Plain-text generation, streamed, with the same provider order and fallback as invoke.

        A provider that fails after it has started writing is abandoned and the reader's live
        preview is reset before the next attempt, so two half-answers never mix.
        """
        from app.llm.providers import stream_complete
        from app.llm.progress import draft_token,draft_reset
        sink=on_token or draft_token
        started=[False]
        async def forward(text):
            started[0]=True
            await sink(text)
        async def reset():
            if started[0]:
                started[0]=False
                await draft_reset()
        async def call(provider,model):
            text=await stream_complete(provider,model,[{'role':'system','content':system},{'role':'user','content':user}],forward)
            if not text.strip(): raise ValueError('Empty answer')
            return text
        return await self._route(call,on_failure=reset)
def get_chat_model(task):
    if task=='audit': return ChatModel(task,local_ok=settings.audit_local)
    # Strong first-pass audit (2026-11-18): only its listed models, never local.
    if task=='audit_strong': return ChatModel(task,local_ok=False,only_preferred=True)
    return ChatModel(task)
