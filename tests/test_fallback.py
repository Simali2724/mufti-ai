import pytest,httpx
from app.llm import router
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.preferences import Preferences
@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['quota','timeout','missing'])
async def test_fallback(monkeypatch,failure):
    seen=[]
    async def fake(provider,*args):
        seen.append(provider)
        if provider!='ollama':
            if failure=='timeout': raise httpx.ReadTimeout('timeout')
            if failure=='missing': raise ValueError('Missing key')
            raise httpx.HTTPStatusError('quota',request=httpx.Request('POST','https://example.com'),response=httpx.Response(429))
        return 'local answer'
    preferences=Preferences(cloud_order=['openai','gemini','anthropic'])
    monkeypatch.setattr(router,'get_preferences',lambda: preferences)
    monkeypatch.setattr(router.settings,'openai_api_key','test-key')
    monkeypatch.setattr(router.settings,'google_api_key','test-key')
    monkeypatch.setattr(router.settings,'anthropic_api_key','')
    monkeypatch.setattr(router,'breaker',CircuitBreaker())
    monkeypatch.setattr(router,'complete',fake)
    async def no_sleep(_): pass
    monkeypatch.setattr(router.asyncio,'sleep',no_sleep)
    answer,provider=await router.get_chat_model('answer').invoke('system','question')
    assert answer=='local answer';assert provider=='ollama';assert 'openai' in seen and 'gemini' in seen
def test_circuit():
    b=CircuitBreaker(limit=2);b.fail('x');assert b.available('x');b.fail('x');assert not b.available('x');b.success('x');assert b.available('x')
@pytest.mark.asyncio
async def test_only_unload_when_switching_models(monkeypatch):
    from app.core import resources
    monkeypatch.setattr(resources,'current_model','first-model')
    calls=[]
    class Response:
        status_code=200
        def raise_for_status(self): pass
    class Client:
        async def post(self,url,json): calls.append(json);return Response()
    c=Client()
    await resources.select_model(c,'first-model')
    assert calls==[]
    await resources.select_model(c,'second-model')
    await resources.select_model(c,'second-model')
    assert calls==[{'model':'first-model','keep_alive':0}]
    assert resources.current_model=='second-model'
