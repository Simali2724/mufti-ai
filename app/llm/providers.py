import json
import httpx
from app.core.config import settings,config
from app.llm.structured import relax_for_grammar
# A cloud call that has not answered in a few minutes is a failure worth falling through.
# A local call on this 2 GB GPU legitimately takes minutes: qwen3:1.7b generates this
# schema at about 3 tokens/s, so a sectioned answer needs 200-400s. The old single 180s
# timeout cut those calls off and the reader was told no answering model could be reached,
# which looked like the book had no evidence. Keep the cloud timeout short, give local room.
def provider_timeout(provider):
    if provider!='ollama': return config['provider_timeout']
    return config.get('ollama_timeout',900)
# Longest silence allowed between two chunks of a STREAMED cloud answer (including the wait for
# the first chunk). Measured 2026-11-17: gemini-3.5-flash sent nothing for the full 180 s
# provider timeout on two live questions, then gemini-2.5-flash answered in ~20 s; the reader
# waited 2-3 minutes for nothing. A working stream sends a chunk every second or two, so a
# 60 s silence is a stall and the router moves to the next model (timeouts switch model).
def stream_read_timeout(provider):
    if provider=='ollama': return provider_timeout(provider)
    return min(config.get('stream_read_timeout',60),config['provider_timeout'])
# Output token budget per task for local models. Too small a budget truncates the JSON, and a
# truncated verifier reply loses verdicts, which the verifier then has to treat as rejections.
# Sized against the schemas in app/llm/structured.py, not guessed.
# Local generation runs at 1.6-3.0 tok/s here, so the answer budget is a latency decision as
# much as a completeness one: 1100 tokens is about 6 minutes. The prompt asks for claims of at
# most 30 words, which is what makes that budget enough for a sectioned answer.
OLLAMA_OUTPUT_BUDGET={'router':120,'language':260,'subtopics':160,'verifier':900,'answer':1100,'quiz':800}
def ollama_budget(task,schema):
    if task in OLLAMA_OUTPUT_BUDGET: return OLLAMA_OUTPUT_BUDGET[task]
    properties=(schema or {}).get('properties',{})
    return (120 if 'intent' in properties else 260 if 'standalone' in properties
            else 160 if 'queries' in properties else 900 if 'language_correct' in properties
            else 1600 if 'coverage' in properties else 500)
async def complete(provider,model,messages,json_mode=False,schema=None,task=''):
    async with httpx.AsyncClient(timeout=provider_timeout(provider),trust_env=False) as client:
        if provider=='ollama':
            budget=ollama_budget(task,schema)
            # Fit the window to this prompt instead of assuming a small GPU can hold any context.
            prompt=''.join(m['content'] for m in messages)
            ascii_chars=sum(c.isascii() for c in prompt)
            estimate=int(ascii_chars/3.6+(len(prompt)-ascii_chars)/1.4)+budget+512
            num_ctx=min(config.get('ollama_max_num_ctx',8192),max(2048,1<<max(11,(estimate-1).bit_length())))
            payload={'model':model,'messages':messages,'stream':False,'think':False,'keep_alive':'5m','options':{'temperature':0,'num_ctx':num_ctx,'num_predict':budget,'num_thread':4}}
            # Bounds are stripped only from the grammar; code re-applies them after parsing.
            if json_mode: payload['format']=relax_for_grammar(schema) if schema else 'json'
            from app.core.resources import ollama_lock,select_model
            async with ollama_lock:
                await select_model(client,model)
                r=await client.post(settings.ollama_base_url+'/api/chat',json=payload)
            r.raise_for_status(); return r.json()['message']['content']
        if provider=='openai':
            if not settings.openai_api_key: raise ValueError('Missing OpenAI key')
            payload={'model':model,'messages':messages,'temperature':0}
            if json_mode: payload['response_format']={'type':'json_schema','json_schema':{'name':'mufti_output','strict':True,'schema':schema}} if schema else {'type':'json_object'}
            r=await client.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+settings.openai_api_key},json=payload); r.raise_for_status(); return r.json()['choices'][0]['message']['content']
        if provider=='anthropic':
            if not settings.anthropic_api_key: raise ValueError('Missing Anthropic key')
            payload={'model':model,'max_tokens':2000,'system':'\n'.join(m['content'] for m in messages if m['role']=='system'),'messages':[m for m in messages if m['role']!='system']}
            if json_mode and schema:
                payload['tools']=[{'name':'mufti_output','description':'Return the requested structured result.','input_schema':schema}]
                payload['tool_choice']={'type':'tool','name':'mufti_output'}
            r=await client.post('https://api.anthropic.com/v1/messages',headers={'x-api-key':settings.anthropic_api_key,'anthropic-version':'2023-06-01'},json=payload)
            r.raise_for_status()
            content=r.json()['content']
            if json_mode and schema:
                tool=next((item for item in content if item.get('type')=='tool_use' and item.get('name')=='mufti_output'),None)
                if tool is None: raise ValueError('Missing structured result')
                return json.dumps(tool['input'],ensure_ascii=False)
            return ''.join(item.get('text','') for item in content)
        if provider=='gemini':
            from app.llm.preferences import request_api_keys
            gkey = (request_api_keys.get() or {}).get('gemini') or settings.google_api_key
            if not gkey: raise ValueError('Missing Gemini key')
            payload={'systemInstruction':{'parts':[{'text':'\n'.join(m['content'] for m in messages if m['role']=='system')}]},'contents':[{'role':'user' if m['role']=='user' else 'model','parts':[{'text':m['content']}]} for m in messages if m['role']!='system'],'generationConfig':{'temperature':0}}
            # Gemini 3 thinking models as the strong fact-checker: measured 2026-11-18 under high demand,
            # gemini-3-flash-preview timed out with default thinking and answered the same audit in 2.3 s
            # with thinkingLevel=low (7.4 s default when it did answer).
            if task=='audit_strong' and model.removeprefix('models/').startswith('gemini-3'):
                payload['generationConfig']['thinkingConfig']={'thinkingLevel':'low'}
            if json_mode:
                payload['generationConfig']['responseMimeType']='application/json'
                if schema: payload['generationConfig']['responseJsonSchema']=schema
            model=model.removeprefix('models/')
            r=await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',headers={'x-goog-api-key':gkey},json=payload)
            r.raise_for_status()
            return ''.join(part.get('text','') for part in r.json()['candidates'][0]['content']['parts'] if not part.get('thought'))
        raise ValueError('Unknown provider')


# ---------------------------------------------------------------------------------------------
# Streaming text generation for the explanation answer path (app/agents/explain_agent.py).
# Returns the full text; every piece is also handed to `on_token` as it arrives so the reader
# sees the answer being written. Plain text only: structured JSON stays on `complete`.
# ---------------------------------------------------------------------------------------------
EXPLAIN_MAX_TOKENS = 4096
OLLAMA_EXPLAIN_BUDGET = 1100


async def stream_complete(provider, model, messages, on_token, temperature=0.3, max_tokens=EXPLAIN_MAX_TOKENS):
    system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
    turns = [m for m in messages if m['role'] != 'system']
    parts = []

    async def emit(text):
        if text:
            parts.append(text)
            await on_token(text)

    timeout = httpx.Timeout(provider_timeout(provider), connect=20, read=stream_read_timeout(provider))
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        if provider == 'ollama':
            prompt =''.join(m['content'] for m in messages)
            ascii_chars = sum(c.isascii() for c in prompt)
            estimate = int(ascii_chars / 3.6 + (len(prompt) - ascii_chars) / 1.4) + OLLAMA_EXPLAIN_BUDGET + 512
            num_ctx = min(config.get('ollama_max_num_ctx', 8192), max(2048, 1 << max(11, (estimate - 1).bit_length())))
            payload = {'model': model, 'messages': messages, 'stream': True, 'think': False, 'keep_alive': '5m',
                       'options': {'temperature': temperature, 'num_ctx': num_ctx,
                                   'num_predict': OLLAMA_EXPLAIN_BUDGET, 'num_thread': 4}}
            from app.core.resources import ollama_lock, select_model
            async with ollama_lock:
                await select_model(client, model)
                async with client.stream('POST', settings.ollama_base_url + '/api/chat', json=payload) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        await emit((data.get('message') or {}).get('content', ''))
            return ''.join(parts)
        if provider == 'gemini':
            from app.llm.preferences import request_api_keys
            gkey = (request_api_keys.get() or {}).get('gemini') or settings.google_api_key
            if not gkey: raise ValueError('Missing Gemini key')
            generation = {'temperature': temperature, 'maxOutputTokens': max_tokens}
            name = model.removeprefix('models/')
            # 2.5 Flash thinks by default, which adds latency without improving a grounded
            # explanation of supplied passages. A small budget keeps a little planning.
            if name.startswith('gemini-2.5-flash'):
                generation['thinkingConfig'] = {'thinkingBudget': 512}
            payload = {'systemInstruction': {'parts': [{'text': system}]},
                       'contents': [{'role': 'user' if m['role'] == 'user' else 'model', 'parts': [{'text': m['content']}]} for m in turns],
                       'generationConfig': generation}
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{name}:streamGenerateContent?alt=sse'
            async with client.stream('POST', url, headers={'x-goog-api-key': gkey}, json=payload) as r:
                if r.status_code >= 400:
                    await r.aread(); r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    chunk = json.loads(line[5:])
                    for candidate in chunk.get('candidates') or []:
                        for part in (candidate.get('content') or {}).get('parts') or []:
                            if not part.get('thought'):
                                await emit(part.get('text', ''))
            return ''.join(parts)
        if provider == 'openai':
            if not settings.openai_api_key: raise ValueError('Missing OpenAI key')
            payload = {'model': model, 'messages': messages, 'temperature': temperature, 'stream': True}
            async with client.stream('POST', 'https://api.openai.com/v1/chat/completions',
                                     headers={'Authorization': 'Bearer ' + settings.openai_api_key}, json=payload) as r:
                if r.status_code >= 400:
                    await r.aread(); r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith('data:') or line[5:].strip() == '[DONE]':
                        continue
                    choice = (json.loads(line[5:]).get('choices') or [{}])[0]
                    await emit((choice.get('delta') or {}).get('content') or '')
            return ''.join(parts)
        if provider == 'anthropic':
            if not settings.anthropic_api_key: raise ValueError('Missing Anthropic key')
            payload = {'model': model, 'max_tokens': max_tokens, 'system': system, 'messages': turns,
                       'temperature': temperature, 'stream': True}
            async with client.stream('POST', 'https://api.anthropic.com/v1/messages',
                                     headers={'x-api-key': settings.anthropic_api_key, 'anthropic-version': '2023-06-01'},
                                     json=payload) as r:
                if r.status_code >= 400:
                    await r.aread(); r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    event = json.loads(line[5:])
                    if event.get('type') == 'content_block_delta':
                        await emit((event.get('delta') or {}).get('text', ''))
            return ''.join(parts)
        raise ValueError('Unknown provider')
