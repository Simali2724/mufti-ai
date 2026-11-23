"""Explanation answer path (app/agents/explain_agent.py), offline with mocked models."""
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.graph import build_graph, ask
from app.agents import language_agent, router_agent, retriever_agent, explain_agent, expand_agent
from app.agents.explain_agent import split_marker, renumber, sentence_units, apply_fixes, cited_ids
from app.core.schemas import ChatRequest
from app.llm.router import ProviderUnavailable
from tests.test_graph_e2e import window

PAGE_50 = ('Ronald Inglehart and Pippa Norris write that the most basic cultural fault line between the '
           'west and Islam involves issues of gender equality and sexual liberalization. They argue that '
           'this gap could plausibly be wider than differences over democracy.')
PAGE_257 = ('Article 27 of the Charter establishes that there shall be no gender discrimination in adult '
            'franchise. Every adult man and woman of the community has an equal right to vote.')


class FakeModel:
    def __init__(self, text='', audit=None, provider='gemini', fail=False, tokens=None):
        self.text, self.audit_result, self.provider, self.fail = text, audit, provider, fail
        self.tokens = tokens

    async def stream(self, system, user, on_token=None):
        if self.fail:
            raise ProviderUnavailable('No provider available: gemini:429, ollama:ConnectError')
        from app.llm.progress import draft_token
        for piece in (self.tokens or [self.text]):
            await draft_token(piece)
        return self.text, self.provider

    async def invoke(self, system, user, structured=False):
        if self.audit_result is None:
            raise RuntimeError('audit unavailable')
        return self.audit_result, self.provider


def install(monkeypatch, model, windows, expand_windows=None):
    async def language(s):
        return {'detected_language': 'English', 'normalized_query_en_ur_ar': [], 'search_queries': [],
                'retrieval_query': s['user_input'], 'matched_concepts': []}

    async def intent(s):
        return {'intent': 'seerah', 'topics': []}

    async def retrieve(s):
        return {'retrieved_chunks': windows, 'evidence_windows': windows, 'retrieval_failed': False,
                'search_rounds': 1}

    async def expand(s):
        return {'evidence_windows': expand_windows or s['evidence_windows'], 'expanded': True,
                'search_rounds': s.get('search_rounds', 1) + 1}

    monkeypatch.setattr(language_agent, 'run', language)
    monkeypatch.setattr(router_agent, 'run', intent)
    monkeypatch.setattr(retriever_agent, 'run', retrieve)
    monkeypatch.setattr(expand_agent, 'run', expand)
    monkeypatch.setattr(explain_agent, 'get_chat_model', lambda task: model)


def two_windows():
    return [window(PAGE_50, page=50, source_id=1), window(PAGE_257, page=257, source_id=2)]


# ------------------------------------------------------------------ parsing units
def test_marker_is_read_and_removed():
    assert split_marker('<<partial>>\nText here [1].') == ('partial', 'Text here [1].')
    assert split_marker('<<none>>') == ('none', '')
    assert split_marker('No marker but an answer [1].')[0] == 'full'


def test_citations_renumbered_in_order_of_use_and_invalid_dropped():
    text, order = renumber('First [2]. Second [1][2]. Bogus [9]. Pair [2, 1].', limit=2)
    assert order == [2, 1]
    assert text == 'First [1]. Second [2][1]. Bogus. Pair [1][2].'


def test_citation_variants_are_understood():
    assert cited_ids('A [Source 2] b [S1] c [1، 2]', 3) == [2, 1]


def test_audit_fix_replaces_and_empty_fix_removes():
    body = ('### Heading\n'
            'Inglehart and Norris write that gender equality is a fault line [1].\n'
            '- Gender equality is a fundamental principle in Islam with equal rights [1].\n'
            '- The Charter bars gender discrimination in adult franchise [2].')
    units = sentence_units(body)
    assert len(units) == 3
    fabricated = next(u for u in units if 'fundamental principle' in u['text'])
    first = units[0]
    fixed, changed, removed = apply_fixes(body, units, [
        {'id': fabricated['id'], 'issue': 'unsupported', 'fix': ''},
        {'id': first['id'], 'issue': 'overstated',
         'fix': 'Inglehart and Norris write that gender equality could be the deepest fault line'}], 2)
    assert 'fundamental principle' not in fixed
    assert 'could be the deepest fault line[1]' in fixed or 'could be the deepest fault line [1]' in fixed
    assert 'adult franchise [2]' in fixed
    assert (changed, removed) == (1, 1)
    assert '\n- \n' not in fixed and not fixed.endswith('-')


# ------------------------------------------------------------------ graph
@pytest.mark.explain
@pytest.mark.asyncio
async def test_explanation_answers_with_markdown_and_citations(monkeypatch):
    text = ('<<full>>\nThe book discusses gender equality in two places [2][1].\n\n'
            '### The Charter of Madinah\n- The Charter bars gender discrimination in adult franchise [2].\n\n'
            '### A quoted Western view\nInglehart and Norris write that gender equality could plausibly be '
            'the deepest divide between the West and Islam [1].')
    install(monkeypatch, FakeModel(text, audit={'problems': []}), two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Explain gender equality in detail'))
    assert r.grounded and r.coverage == 'full' and r.reason_code == ''
    assert r.answer_format == 'markdown' and r.verification == 'audited'
    assert [c.page for c in r.citations] == [257, 50]          # renumbered by first use
    assert '<<' not in r.answer and '### The Charter of Madinah' in r.answer
    assert 'adult franchise' in r.citations[0].excerpt


@pytest.mark.explain
@pytest.mark.asyncio
async def test_audit_removes_fabrication_but_keeps_the_rest(monkeypatch):
    text = ('<<full>>\nInglehart and Norris write that gender equality is a cultural fault line [1].\n'
            'Gender equality is a fundamental principle in Islam with equal rights for all [1].\n'
            'The Charter bars gender discrimination in adult franchise [2].')
    units = sentence_units(split_marker(text)[1])
    bad = next(u['id'] for u in units if 'fundamental' in u['text'])
    model = FakeModel(text, audit={'problems': [{'id': bad, 'issue': 'unsupported', 'fix': ''}]})
    install(monkeypatch, model, two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='What does the book say about gender equality?'))
    assert r.grounded
    assert 'fundamental principle' not in r.answer
    assert 'cultural fault line' in r.answer and 'adult franchise' in r.answer


@pytest.mark.explain
@pytest.mark.asyncio
async def test_none_marker_searches_again_then_reports_honestly(monkeypatch):
    calls = []

    class CountingModel(FakeModel):
        async def stream(self, system, user, on_token=None):
            calls.append(user)
            return '<<none: 2>>', 'gemini'

    install(monkeypatch, CountingModel(), two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='What do the elections in the Charter cover?'))
    assert len(calls) == 2, 'a second search round must run before saying the book has no answer'
    assert not r.grounded and not r.citations
    assert r.reason_code == 'insufficient_coverage'
    assert [p.page for p in r.related] == [257], 'only the source the model judged same-subject is shown'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_plain_none_shows_no_related_pages_even_with_strong_scores(monkeypatch):
    """Live 2026-11-16: "how do I fix my bicycle chain?" listed pages about amino-acid chains."""
    class NoAnswer(FakeModel):
        async def stream(self, system, user, on_token=None):
            return '<<none>>', 'gemini'

    install(monkeypatch, NoAnswer(), two_windows())     # dense .9 / lexical .5 in the fixture
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='how do I fix my bicycle chain?'))
    assert r.reason_code == 'not_in_library' and not r.related


@pytest.mark.explain
@pytest.mark.asyncio
async def test_answer_without_any_valid_citation_is_not_presented_as_the_book(monkeypatch):
    install(monkeypatch, FakeModel('<<full>>\nGender equality is central to Islam [7].', audit={'problems': []}),
            two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='gender equality?'))
    assert not r.grounded
    assert r.reason_code == 'explanation_unverified'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_provider_failure_is_not_reported_as_missing_evidence(monkeypatch):
    install(monkeypatch, FakeModel(fail=True), two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Explain gender equality'))
    assert not r.grounded
    assert r.reason_code in ('provider_unavailable', 'provider_quota_exhausted')


@pytest.mark.explain
@pytest.mark.asyncio
async def test_local_answer_is_labelled_not_audited(monkeypatch):
    model = FakeModel('<<partial>>\nThe Charter bars gender discrimination in adult franchise [2].',
                      audit={'problems': []}, provider='ollama')
    install(monkeypatch, model, two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Explain gender equality'))
    assert r.grounded and r.verification == 'citations_checked'
    assert r.coverage == 'partial' and r.reason_code == 'partial_coverage'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_audit_outage_keeps_answer_but_says_not_audited(monkeypatch):
    install(monkeypatch, FakeModel('<<full>>\nThe Charter bars gender discrimination in adult franchise [2].',
                                   audit=None), two_windows())
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='voting rights of women?'))
    assert r.grounded and r.verification == 'citations_checked'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_draft_tokens_stream_to_the_reader(monkeypatch):
    text = '<<full>>\nThe Charter bars gender discrimination in adult franchise [2].'
    install(monkeypatch, FakeModel(text, audit={'problems': []}, tokens=[text[:20], text[20:]]), two_windows())
    events = []

    async def sink(update):
        events.append(update)

    from app.agents.graph import ask as ask_with_progress
    await ask_with_progress(build_graph(InMemorySaver()), ChatRequest(question='voting?'), progress=sink)
    drafts = ''.join(e['text'] for e in events if e.get('kind') == 'draft')
    assert drafts == text


@pytest.mark.explain
@pytest.mark.asyncio
async def test_unreadable_ocr_is_never_sent_as_a_source(monkeypatch):
    seen = []

    class Spy(FakeModel):
        async def stream(self, system, user, on_token=None):
            seen.append(user)
            return '<<full>>\nThe Charter bars gender discrimination in adult franchise [1].', 'gemini'

    junk = window('vii h V g ujo f ujo f ujo f o F o F i Zi F o F mF o F i i F', page=626, source_id=1)
    install(monkeypatch, Spy(audit={'problems': []}), [junk, window(PAGE_257, page=257, source_id=2)])
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='voting?'))
    assert 'ujo f' not in seen[0]
    assert [c.page for c in r.citations] == [257]


# ------------------------------------------------------------------ regressions from the first live run
def test_repeated_meta_fix_from_a_weak_auditor_is_ignored():
    """Live 2026-11-16: a local fallback auditor replaced several sentences with one meta line."""
    body = ('Inglehart and Norris write that gender equality is a fault line [1].\n'
            'The Charter bars gender discrimination in adult franchise [2].')
    units = sentence_units(body)
    meta = 'This is supported by sources 2, 4, 7, and 12.'
    fixed, changed, removed = apply_fixes(body, units, [
        {'id': units[0]['id'], 'issue': 'unsupported', 'fix': meta},
        {'id': units[1]['id'], 'issue': 'unsupported', 'fix': meta}], 2)
    assert fixed == body and (changed, removed) == (0, 0)


def _preferences(mode):
    from app.llm.preferences import Preferences
    return Preferences(mode=mode, cloud_order=['gemini', 'anthropic', 'openai'],
                       models={'gemini': 'gemini-2.5-flash', 'anthropic': 'a', 'openai': 'o', 'ollama': 'qwen3:1.7b'})


@pytest.mark.asyncio
async def test_audit_never_falls_back_to_the_local_model(monkeypatch):
    import httpx
    from app.llm import router
    from app.llm.preferences import request_preferences
    calls = []

    async def complete(provider, model, *args, **kwargs):
        calls.append((provider, model))
        raise httpx.HTTPStatusError('busy', request=httpx.Request('POST', 'http://x'),
                                    response=httpx.Response(503))

    monkeypatch.setattr(router, 'complete', complete)
    monkeypatch.setattr(router.settings, 'google_api_key', 'test-key')
    monkeypatch.setattr(router.breaker, 'available', lambda provider: True)
    token = request_preferences.set(_preferences('gemini'))
    try:
        with pytest.raises(router.ProviderUnavailable):
            await router.get_chat_model('audit').invoke('s', 'u', True)
    finally:
        request_preferences.reset(token)
    assert calls and all(provider != 'ollama' for provider, _ in calls)


@pytest.mark.asyncio
async def test_overloaded_gemini_model_switches_to_an_alternate_gemini_model(monkeypatch):
    import httpx
    from app.llm import router
    from app.llm.preferences import request_preferences
    calls = []

    async def complete(provider, model, *args, **kwargs):
        calls.append(model)
        if model == 'gemini-2.5-flash':
            raise httpx.HTTPStatusError('busy', request=httpx.Request('POST', 'http://x'),
                                        response=httpx.Response(503))
        return '{"ok": true}'

    monkeypatch.setattr(router, 'complete', complete)
    monkeypatch.setattr(router.settings, 'google_api_key', 'test-key')
    monkeypatch.setattr(router.breaker, 'available', lambda provider: True)
    monkeypatch.setitem(router.config, 'gemini_alternates', ['gemini-3.5-flash'])
    token = request_preferences.set(_preferences('gemini'))
    try:
        result, provider = await router.get_chat_model('answer').invoke('s', 'u', True)
    finally:
        request_preferences.reset(token)
    assert provider == 'gemini' and calls == ['gemini-2.5-flash', 'gemini-3.5-flash']


@pytest.mark.asyncio
async def test_daily_quota_model_is_skipped_until_its_retry_delay(monkeypatch):
    """Live 2026-11-16: gemini-2.5-flash free tier is 20 requests/day; do not retry it per request."""
    import httpx
    from app.llm import router
    from app.llm.preferences import request_preferences
    calls = []
    body = {'error': {'details': [{'retryDelay': '12334s'}]}}

    async def complete(provider, model, *args, **kwargs):
        calls.append(model)
        if model == 'gemini-2.5-flash':
            raise httpx.HTTPStatusError('quota', request=httpx.Request('POST', 'http://x'),
                                        response=httpx.Response(429, json=body))
        return '{"ok": true}'

    monkeypatch.setattr(router, 'complete', complete)
    monkeypatch.setattr(router.settings, 'google_api_key', 'test-key')
    monkeypatch.setattr(router.breaker, 'available', lambda provider: True)
    monkeypatch.setitem(router.config, 'gemini_alternates', ['gemini-3.5-flash'])
    token = request_preferences.set(_preferences('gemini'))
    try:
        await router.get_chat_model('answer').invoke('s', 'u', True)
        await router.get_chat_model('answer').invoke('s', 'u', True)
    finally:
        request_preferences.reset(token)
    assert calls == ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-3.5-flash']


def test_audit_prefers_its_light_model():
    from app.llm import router
    order = router.models_for('gemini', 'gemini-2.5-flash', 'audit')
    assert order[0] == router.config['task_models']['audit']['gemini'][0]
    assert 'gemini-2.5-flash' in order


def test_readable_sentence_merged_with_urdu_reference_noise_still_reaches_the_model():
    """Live 2026-11-16, PDF page 375: the Duguit sentence was lost to a merged noisy span."""
    from app.retrieval.evidence import legible_pieces
    text = ('خادم اور امین ہونے کا تصور پروان چڑھا۔ جان لاک ) (کی\n)۱1(\n)2(\n'
            '۔ مسلم، الصہ ، ک الامارۃ، با ف وو طاعۃ الاأمراء ؤ غیر\nمعصیۃ، ا، رقم:\n'
            'Leon Duguit 1859-1928 Sovereignty is an essential attribute of the state was a myth to be '
            'discarded. He presented the idea of the "social group" instead of "Social Contract."\n'
            'o MV Q S M EPD M p vn x j^ h o (e^ h o o RV EQD U P R L O T R N vn x j^ h h o q h o OV U R P L')
    joined = ' '.join(legible_pieces(text))
    assert 'Sovereignty is an essential attribute of the state was a myth' in joined
    assert 'EPD M p vn' not in joined and 'RV EQD' not in joined


def test_initials_and_abbreviations_do_not_split_sentences():
    """Live 2026-11-16: "Philip K. Hitti" was split at "K." and an audit fix broke the sentence."""
    body = 'Philip K. Hitti writes that the new community soon controlled western Arabia [2]. Dr. Qadri adds more [1].'
    units = sentence_units(body)
    assert [u['text'] for u in units] == [
        'Philip K. Hitti writes that the new community soon controlled western Arabia [2].',
        'Dr. Qadri adds more [1].']


# ------------------------------------------------------------------ "which book / reference?" (2026-11-16)
@pytest.mark.parametrize('question,expected', [
    ('ye kis book se hai?', True), ('reference kahan se hai', True), ('Which book is this from?', True),
    ('اس کا حوالہ کیا ہے؟', True), ('यह किस किताब से है?', True), ('is answer ka reference do', True),
    ('What does the book say about references to hadith?', False),
    ('What was the source of law in Madinah?', False), ('Which book did Watt write?', False),
    ('Misaq-e-Madina ke baare mein batao', False),
])
def test_reference_questions_are_told_apart_from_content_questions(question, expected):
    from app.agents.bibliography import is_reference_question
    assert is_reference_question(question) is expected


@pytest.mark.asyncio
async def test_reference_card_names_the_book_and_the_previous_answers_pages(monkeypatch):
    from app.agents import bibliography
    book = {'id': 'b', 'title': 'Sample', 'pages': 700}
    record = {'facts': {
        'title': {'page': 3, 'quote': 'T', 'values': {'English': 'Muqaddima Seerat-ur-Rasool (Part One)'}},
        'author': {'page': 3, 'quote': 'A', 'values': {'English': 'Dr. Muhammad Tahir-ul-Qadri'}},
        'publisher': {'page': 2, 'quote': 'P', 'values': {'English': 'Minhaj-ul-Quran Publications'}}}}
    monkeypatch.setattr(bibliography, 'catalog', lambda: [book])
    monkeypatch.setattr(bibliography, 'read_reviewed', lambda b: record)
    history = [{'question': 'q', 'answer': 'a', 'provider_used': 'gemini',
                'citations': [{'book_id': 'b', 'page': 257, 'chapter': 'Charter of Madinah', 'excerpt': 'x'}]}]
    out = await bibliography.run({'user_input': 'Which book is this from?', 'language_hint': 'auto',
                                  'history': history})
    assert out['bibliography_answered'] and out['answer_format'] == 'markdown'
    answer = out['final_answer']
    assert 'Muqaddima Seerat-ur-Rasool (Part One)' in answer and 'Dr. Muhammad Tahir-ul-Qadri' in answer
    assert 'Minhaj-ul-Quran Publications' in answer and 'PDF page 257' in answer
    assert sorted(c['page'] for c in out['citations']) == [2, 3, 257]


def test_explain_prompt_asks_for_direct_voice_and_detail():
    from app.llm.prompts import EXPLAIN_RULES, AUDIT_RULES
    assert 'Do NOT keep writing "the book says"' in EXPLAIN_RULES
    assert '450-1100 words' in EXPLAIN_RULES
    assert 'direct voice' in AUDIT_RULES


def test_quoted_writers_keep_their_full_names():
    """Live 2026-11-16, page 51: initials split names, so "Nettler" and "Cardinal R. W." were lost."""
    from app.retrieval.evidence import legible_pieces
    line = ('Islam (is) personal piety and worship of God in a framework of revealed universal ethical '
            'principles. Cardinal R. W. Southern David Marquand, Ronald L. Nettler, Religion and Democracy , pp. '
            'Maxime Rodinson, The Western Image & Western Studies of Islam p.9.')
    joined = ' '.join(legible_pieces(line))
    assert 'Cardinal R. W. Southern' in joined and 'Ronald L. Nettler' in joined


def test_a_glyph_run_on_the_same_line_is_still_removed():
    from app.retrieval.evidence import legible_pieces
    line = ('Rosenthal, Political Thought in Medieval Islam , pp. 51-62. o MV Q S M EPD M p vn x j^ h o '
            '(e^ h o o RV EQD U P R L O T R N vn x j^ h h o q h o OV U R P L P T M')
    joined = ' '.join(legible_pieces(line))
    assert 'Rosenthal, Political Thought in Medieval Islam' in joined
    assert 'EPD M p vn' not in joined


def test_source_notes_name_quoted_writers_in_full():
    """Live 2026-11-16, page 51: the note listed loose words, and the answer dropped attribution."""
    from app.agents.explain_agent import quoted_writers, sources_block, build_sources
    assert quoted_writers('Ronald Inglehart and Pippa Norris, The True Clash of Civilizations, p. 155.') == [
        'Ronald Inglehart', 'Pippa Norris']
    text = ('Islam (is) personal piety and worship of God in a framework of revealed universal ethical '
            'principles. Ronald L. Nettler, Religion and Democracy , pp. 12.')
    block = sources_block(build_sources([window(text, page=51)]))
    assert 'credited in its footnotes to Ronald L. Nettler' in block


@pytest.mark.asyncio
async def test_reference_card_reports_full_coverage_and_says_yes(monkeypatch):
    """Live 2026-11-16: the card came back with coverage 'none', so the UI said 'No verified book answer'."""
    from app.agents import bibliography
    monkeypatch.setattr(bibliography, 'catalog', lambda: [{'id': 'b', 'title': 'Sample', 'pages': 700}])
    monkeypatch.setattr(bibliography, 'read_reviewed', lambda b: {'facts': {
        'author': {'page': 3, 'quote': 'A', 'values': {'English': 'Dr. Muhammad Tahir-ul-Qadri'}}}})
    history = [{'question': 'Misaq-e-Madina kya tha?', 'answer': 'a', 'provider_used': 'gemini',
                'citations': [{'book_id': 'b', 'page': 430, 'chapter': 'باب 5', 'excerpt': 'x'}]}]
    out = await bibliography.run({'user_input': 'ye kis book se hai?', 'language_hint': 'auto', 'history': history})
    assert out['coverage'] == 'full' and out['history'][-1]['coverage'] == 'full'
    assert out['final_answer'].splitlines()[1].startswith('Ji haan')
    assert 'Misaq-e-Madina kya tha?' in out['final_answer']


@pytest.mark.explain
@pytest.mark.asyncio
async def test_two_passages_of_one_page_share_one_citation(monkeypatch):
    """Live 2026-11-16 (cm-en-5): page 350 appeared twice in the source list."""
    a = window(PAGE_257, page=257, source_id=1)
    b = window('Article 28 adds that every adult citizen may stand for office without any gender discrimination.',
               page=257, source_id=2)
    c = window(PAGE_50, page=50, source_id=3)
    text = ('<<full>>\nThe Charter bars gender discrimination in adult franchise [1]. '
            'Citizens may also stand for office [2]. Inglehart and Norris call gender equality a fault line [3].')
    install(monkeypatch, FakeModel(text, audit={'problems': []}), [a, b, c])
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='voting and office?'))
    assert [c.page for c in r.citations] == [257, 50]
    assert '[2]' in r.answer and r.answer.count('[1]') == 2
    assert 'stand for office' in r.citations[0].full_support and 'adult franchise' in r.citations[0].full_support


@pytest.mark.explain
@pytest.mark.asyncio
async def test_hindi_answer_in_mixed_script_is_rewritten_once(monkeypatch):
    """Live 2026-11-16 (absent-hi-1): a lite model answered Hindi half in Urdu script."""
    from app.agents.explain_agent import wrong_script_share
    mixed = '<<full>>\nاس کتاب میں ووٹ کے حق میں صنفی امتیاز نہیں ہے [1]। चार्टर में वोट का अधिकार है [1]।'
    clean = '<<full>>\nचार्टर वयस्क मताधिकार में लैंगिक भेदभाव नहीं करता [1]। हर वयस्क को वोट का बराबर हक़ है [1]।'
    assert wrong_script_share(mixed, 'Hindi') > .15 and wrong_script_share(clean, 'Hindi') == 0
    calls = []

    class Mixed(FakeModel):
        async def stream(self, system, user, on_token=None):
            calls.append(user)
            return (mixed if len(calls) == 1 else clean), 'gemini'

    async def hindi(s):
        return {'detected_language': 'Hindi', 'normalized_query_en_ur_ar': [], 'search_queries': [],
                'retrieval_query': s['user_input'], 'matched_concepts': []}

    install(monkeypatch, Mixed(audit={'problems': []}), [window(PAGE_257, page=257, source_id=1)])
    monkeypatch.setattr(language_agent, 'run', hindi)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='वोट का अधिकार?'))
    assert len(calls) == 2 and 'Devanagari script only' in calls[1]
    assert wrong_script_share(r.answer, 'Hindi') == 0


@pytest.mark.asyncio
async def test_author_question_names_each_book_or_the_one_being_discussed(monkeypatch):
    """Two books (2026-11-16): the old lookup gave up when two books matched."""
    from app.agents import bibliography
    b1 = {'id': 'b1', 'title': 'Muqaddima 1 1', 'pages': 700}
    b2 = {'id': 'b2', 'title': 'creation man 1', 'pages': 102}
    facts = {'b1': ('Muqaddima Seerat-ur-Rasool', 'Dr. Muhammad Tahir-ul-Qadri', 3),
             'b2': ('Creation of Man', 'Prof. Dr. Muhammad Tahir-ul-Qadri', 1)}
    monkeypatch.setattr(bibliography, 'catalog', lambda: [b1, b2])
    monkeypatch.setattr(bibliography, 'read_reviewed', lambda b: {'facts': {
        'title': {'page': facts[b['id']][2], 'quote': 'T', 'values': {'English': facts[b['id']][0]}},
        'author': {'page': facts[b['id']][2], 'quote': 'A', 'values': {'English': facts[b['id']][1]}}}})
    out = await bibliography.run({'user_input': 'Who is the author of this book?', 'language_hint': 'auto', 'history': []})
    assert 'Creation of Man' in out['final_answer'] and 'Muqaddima Seerat-ur-Rasool' in out['final_answer']
    history = [{'question': 'q', 'answer': 'a', 'provider_used': 'gemini', 'citations': [{'book_id': 'b2', 'page': 40}]}]
    out = await bibliography.run({'user_input': 'Who is the author of this book?', 'language_hint': 'auto', 'history': history})
    assert 'Prof. Dr. Muhammad Tahir-ul-Qadri' in out['final_answer'] and 'Muqaddima' not in out['final_answer']


@pytest.mark.asyncio
async def test_unsure_question_is_searched_not_refused(monkeypatch):
    """Live 2026-11-16: "Tissues and Body Form explain this in detail" was routed out_of_scope by a
    lite model, so the books were never searched although Creation of Man p. 73 covers it."""
    from app.agents import router_agent

    def forbidden(task):
        raise AssertionError('the router must not ask a model')

    monkeypatch.setattr(router_agent, 'get_chat_model', forbidden)
    out = await router_agent.run({'user_input': 'Tissues and Body Form explain this in detail',
                                  'matched_concepts': []})
    assert out['intent'] == 'general'


def test_short_clean_english_lines_are_kept_but_glyph_runs_are_not():
    """Live 2026-11-16, Creation of Man p.73: the heading and a wrapped sentence end were dropped."""
    from app.retrieval.evidence import short_clean_latin, legible_pieces
    assert short_clean_latin('Tissues and Body Form') and short_clean_latin('muscular system.')
    assert not short_clean_latin('vii h V g ujo f') and not short_clean_latin('o F o F i Zi F')
    text = ('In fact this can also be seen as referring to the\nmuscular system.\n'
            'Tissues and Body Form\no F o F i Zi F o F mF')
    joined = ' '.join(legible_pieces(text))
    assert 'muscular system.' in joined and 'Tissues and Body Form' in joined and 'Zi F' not in joined


def test_a_matched_heading_brings_its_paragraph(monkeypatch):
    """Live 2026-11-16: a 113-char heading matched and the 821-char body under it was skipped."""
    from app.retrieval import evidence
    heading = 'Development of Human Bones, Tissues and Body Form'
    body = 'Formation of Bones and Muscles: ' + 'The bones are later covered with intact flesh. ' * 17
    monkeypatch.setattr(evidence.segment_index, 'page_parents', lambda book, page: [heading, body])
    text = evidence.window_text({'parent_text': heading, 'parent_id': 'p1', 'book_id': 'b', 'page_start': 73})
    assert heading in text and 'intact flesh' in text


@pytest.mark.explain
@pytest.mark.asyncio
async def test_slow_audit_does_not_hold_the_answer(monkeypatch):
    """Live 2026-11-16: a 53 s flash-lite audit made a 9 s answer take 71 s."""
    import asyncio
    from app.core.config import settings

    class SlowAudit(FakeModel):
        async def invoke(self, system, user, structured=False):
            await asyncio.sleep(5)
            return {'problems': []}, 'gemini'

    monkeypatch.setattr(settings, 'audit_timeout', 0.2)
    monkeypatch.setattr(settings, 'strong_audit_timeout', 0.2)   # both tiers are bounded (2026-11-18)
    install(monkeypatch, SlowAudit('<<full>>\nThe Charter bars gender discrimination in adult franchise [1].'),
            [window(PAGE_257, page=257, source_id=1)])
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='voting?'))
    assert r.grounded and r.verification == 'citations_checked' and r.latency_ms < 3000


@pytest.mark.explain
@pytest.mark.asyncio
async def test_off_topic_question_shows_no_unrelated_passages(monkeypatch):
    """Live 2026-11-16: "write me a code of adding two number in C" listed three unrelated pages."""
    weak = []
    for n, page in enumerate((27, 468, 585), start=1):
        w = window(PAGE_257, page=page, source_id=n)
        w.update(dense_score=.49, lexical_score=0.0)
        weak.append(w)

    class NoAnswer(FakeModel):
        async def stream(self, system, user, on_token=None):
            return '<<none>>', 'gemini'

    install(monkeypatch, NoAnswer(), weak)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='how do I fix my bicycle chain?'))
    assert not r.grounded and not r.related and not r.citations
    assert r.reason_code == 'not_in_library'
    assert 'none of them discusses this subject' in r.answer


def test_programming_requests_are_recognised_without_a_model():
    from app.agents.router_agent import deterministic_intent
    for q in ('write me a code of addting two number in C', 'do number jodne ka code likho', 'C++ program for factorial'):
        assert deterministic_intent(q) == ('out_of_scope', True)
    for q in ('Code of conduct in the Charter of Madinah', 'Write about the life of the Prophet',
              'Tissues and Body Form explain this in detail'):
        assert deterministic_intent(q)[0] != 'out_of_scope'
