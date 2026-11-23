import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.graph import build_graph, ask
from app.agents import language_agent, router_agent, retriever_agent, answer_agent, verifier_agent
from app.agents.verifier_agent import validate_claims
from app.core.schemas import ChatRequest
from app.core.language import NOT_FOUND


def window(text, page=2, source_id=1):
    from app.retrieval.evidence import spans_for
    return {'source_id': source_id, 'chunk_id': f'c{source_id}', 'parent_id': f'p{source_id}', 'book_id': 'b',
            'book_title': 'Sample', 'page_start': page, 'page_end': page, 'printed_label': page - 1,
            'chapter': '', 'ocr': False, 'corrected': False, 'correction_source': '',
            'relation': 'same_concept', 'relevance': .9, 'dense_score': .9, 'lexical_score': .5,
            'matched_queries': [], 'text': text, 'spans': spans_for(text), 'tokens': 40}


def test_fake_citation_rejected():
    c = [{'text': 'A real original passage about history.'}]
    assert not validate_claims({'claims': [{'text': 'invented', 'support': 'invented quote goes here',
                                            'source_id': 1}]}, c, 'English')[0]


def test_outside_citation_rejected():
    assert not validate_claims({'claims': [{'text': 'x', 'support': 'a sufficiently long quote',
                                            'source_id': 7}]}, [], 'English')[0]


def test_bidi_quote_maps_to_original():
    from app.agents.verifier_agent import locate_quote
    source = 'prefix ‏اصل عبارت یہاں موجود ہے‎ suffix'
    matched = locate_quote(source, 'اصل عبارت یہاں موجود ہے')
    assert matched in source and matched == 'اصل عبارت یہاں موجود ہے'


def test_incomplete_claim_is_rejected():
    source = 'سیرت کے بیان میں کیا کیوں اور'
    draft = {'claims': [{'text': source, 'source_id': 1, 'support': source}]}
    assert not validate_claims(draft, [{'text': source}], 'Urdu')[0]


def test_punctuation_only_claim_is_rejected():
    source = 'An original supporting source sentence.'
    draft = {'claims': [{'text': '.', 'source_id': 1, 'support': source}]}
    assert not validate_claims(draft, [{'text': source}], 'English')[0]


def test_cited_spans_resolve_to_verbatim_source():
    """Replaces the old 25-word fragment check: spans must still be real source text."""
    source = ('Heading about history\n' + ' '.join(['original'] * 70) + '۔\nA final supporting source sentence.')
    built = window(source)
    assert built['spans'], 'a passage must produce at least one span'
    flat = ' '.join(source.split())
    assert all(span['text'] in flat for span in built['spans'])


@pytest.mark.asyncio
async def test_unrelated_returns_not_found(monkeypatch):
    async def language(s):
        return {'detected_language': 'English', 'normalized_query_en_ur_ar': [], 'search_queries': [],
                'retrieval_query': s['user_input']}

    async def intent(s):
        return {'intent': 'general', 'topics': []}

    async def retrieve(s):
        return {'retrieved_chunks': [], 'evidence_windows': [], 'retrieval_failed': False, 'search_rounds': 1}

    monkeypatch.setattr(language_agent, 'run', language)
    monkeypatch.setattr(router_agent, 'run', intent)
    monkeypatch.setattr(retriever_agent, 'run', retrieve)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='How do I repair a spaceship?'))
    assert not r.grounded and not r.citations
    assert r.answer == NOT_FOUND['English']
    assert r.reason_code == 'no_matching_passages'


@pytest.mark.asyncio
async def test_supported_pipeline(monkeypatch):
    passage = 'The book describes the history of Madinah. It records the charter agreed there.'

    async def language(s):
        return {'detected_language': 'English', 'normalized_query_en_ur_ar': [], 'search_queries': [],
                'retrieval_query': s['user_input']}

    async def intent(s):
        return {'intent': 'history', 'topics': []}

    async def retrieve(s):
        return {'retrieved_chunks': [{'id': 'c'}], 'evidence_windows': [window(passage)],
                'retrieval_failed': False, 'search_rounds': 1}

    async def answer(s):
        from app.agents.answer_agent import attach_support
        draft = attach_support({'coverage': 'full', 'missing_aspects': [], 'sections': [
            {'heading': 'History', 'claims': [{'text': 'This passage concerns the history of Madinah.',
                                               'source_id': 1, 'span_ids': [1]}]}]}, s['evidence_windows'])
        return {'draft_answer': draft, 'provider_used': 'mock'}

    async def verify(s):
        kept, rejected = verifier_agent.structural_pass(s['draft_answer'], s['evidence_windows'], 'English')
        return {'verification_report': {'passed': bool(kept) and not rejected, 'verified_claims': len(kept),
                                        'rejected': rejected, 'feedback': ''},
                'draft_answer': {**s['draft_answer'], 'coverage': 'full'}, 'retries': 1}

    for module, func in [(language_agent, language), (router_agent, intent), (retriever_agent, retrieve),
                         (answer_agent, answer), (verifier_agent, verify)]:
        monkeypatch.setattr(module, 'run', func)
    graph = build_graph(InMemorySaver())
    r = await ask(graph, ChatRequest(question='What history is described?'))
    assert r.grounded and r.citations[0].page == 2 and '[1]' in r.answer
    assert r.coverage == 'full'
    assert r.citations[0].excerpt.startswith('The book describes the history of Madinah.')
    assert r.citations[0].full_support in ' '.join(passage.split())
    assert r.selected_provider and r.answering_model == ''


@pytest.mark.asyncio
async def test_partial_coverage_states_what_is_missing(monkeypatch):
    passage = 'The right to vote shall be above gender discrimination under the charter.'

    async def language(s):
        return {'detected_language': 'English', 'normalized_query_en_ur_ar': [], 'search_queries': [],
                'retrieval_query': s['user_input']}

    async def intent(s):
        return {'intent': 'general', 'topics': []}

    async def retrieve(s):
        return {'retrieved_chunks': [{'id': 'c'}],
                'evidence_windows': [window(passage, page=257), window('An unrelated nearby passage here.', page=99,
                                                                      source_id=2)],
                'retrieval_failed': False, 'search_rounds': 2}

    async def answer(s):
        from app.agents.answer_agent import attach_support
        draft = attach_support({'coverage': 'partial', 'missing_aspects': ['inheritance', 'testimony'],
                                'sections': [{'heading': 'Voting rights', 'claims': [
                                    {'text': 'The charter bars gender discrimination in the right to vote.',
                                     'source_id': 1, 'span_ids': [1]}]}]}, s['evidence_windows'])
        return {'draft_answer': draft, 'provider_used': 'mock'}

    async def verify(s):
        return {'verification_report': {'passed': True, 'verified_claims': 1, 'rejected': [], 'feedback': ''},
                'draft_answer': {**s['draft_answer'], 'coverage': 'partial'}, 'retries': 3}

    for module, func in [(language_agent, language), (router_agent, intent), (retriever_agent, retrieve),
                         (answer_agent, answer), (verifier_agent, verify)]:
        monkeypatch.setattr(module, 'run', func)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Explain gender equality in detail'))
    assert r.grounded and r.coverage == 'partial'
    assert r.reason_code == 'partial_coverage'
    assert 'inheritance' in r.answer and 'Not covered in this book' in r.answer
    assert r.missing_aspects == ['inheritance', 'testimony']
    # Related material is shown separately, never as a verified claim.
    assert [p.page for p in r.related] == [99]
    assert [c.page for c in r.citations] == [257]
