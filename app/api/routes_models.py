"""Local model settings. API keys are never accepted or returned."""
import asyncio
import httpx
from fastapi import APIRouter
from app.core.config import settings
from app.llm.preferences import Preferences, get_preferences, save_preferences
from app.llm.router import breaker, has_key, last_outcome

router = APIRouter(prefix='/settings', tags=['models'])


def provider_state(provider, local_online):
    """Honest availability. A configured key is not the same thing as a working provider."""
    if provider == 'ollama':
        return {'configured': True, 'available': local_online,
                'label': 'Ollama running' if local_online else 'Ollama offline',
                'detail': '' if local_online else 'Start Ollama before using local answers or fallback.'}
    if not has_key(provider):
        return {'configured': False, 'available': False, 'label': 'No API key',
                'detail': 'Add a key to .env and restart to use this provider.'}
    outcome = last_outcome(provider)
    if not breaker.available(provider):
        return {'configured': True, 'available': False, 'label': 'Paused after failures',
                'detail': outcome or 'Recent requests failed; this provider is skipped for a short cooldown.'}
    if outcome and '429' in outcome:
        return {'configured': True, 'available': False, 'label': 'Quota or rate limit reached',
                'detail': 'The last request was refused with HTTP 429. Local fallback will answer.'}
    if outcome and outcome != 'ok':
        return {'configured': True, 'available': True, 'label': 'Key configured · last call failed',
                'detail': outcome}
    if outcome == 'ok':
        return {'configured': True, 'available': True, 'label': 'Answered successfully', 'detail': ''}
    return {'configured': True, 'available': True, 'label': 'Key configured · not yet used',
            'detail': 'A configured key does not guarantee available quota.'}

async def model_status(preferences):
    installed, online = [], False
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            response = await client.get(settings.ollama_base_url + '/api/tags')
            response.raise_for_status()
            online = True
            async def chat_model(entry):
                name = entry.get('name', '')
                capabilities = entry.get('capabilities', [])
                if not name or name.removesuffix(':latest')==settings.embedding_model.removesuffix(':latest') or 'embed' in name.lower():
                    return None
                if not capabilities:
                    try:
                        detail=await client.post(settings.ollama_base_url+'/api/show',json={'model':name})
                        detail.raise_for_status()
                        capabilities=detail.json().get('capabilities',[])
                    except (httpx.HTTPError,ValueError):
                        return None
                return name if 'completion' in capabilities else None
            installed=[name for name in await asyncio.gather(*(chat_model(entry) for entry in response.json().get('models', []))) if name]
    except (httpx.HTTPError, ValueError):
        pass
    return {
        **preferences.model_dump(),
        'configured': {p: has_key(p) for p in ('anthropic', 'openai', 'gemini')},
        'provider_state': {p: provider_state(p, online) for p in ('anthropic', 'openai', 'gemini', 'ollama')},
        'installed_ollama_models': sorted(set(installed)),
        'local_online': online,
    }

@router.get('/models')
async def get_models():
    return await model_status(get_preferences())

@router.put('/models')
async def update_models(preferences: Preferences):
    saved = save_preferences(preferences)
    breaker.states.clear()
    return await model_status(saved)
