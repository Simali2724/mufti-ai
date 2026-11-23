"""Regressions for the ranking failures that previously hid the right page.

The original versions of these checks ran against the old reranker and the 25-word quote
picker. The behaviour they protect is unchanged: an exact lexical hit must not be displaced
by a dense-only neighbour, and real content must survive selection.
"""
import json
import pytest
from app.retrieval import evidence, reranker


@pytest.mark.asyncio
async def test_hybrid_exact_match_is_not_displaced_by_dense_only(monkeypatch):
    monkeypatch.setattr(reranker.settings, 'enable_reranker', False)
    monkeypatch.setattr(reranker.settings, 'rerank_threshold', .3)
    result = await reranker.rerank('personal piety', [
        {'id': 'direct', 'dense_score': .55, 'rrf': .064},
        {'id': 'related', 'dense_score': .57, 'rrf': .044},
    ])
    assert result[0]['id'] == 'direct'


def test_lexical_only_hit_survives_the_dense_relevance_floor(monkeypatch):
    """The gender-equality failure: a BM25-only hit had dense_score 0 and was dropped."""
    monkeypatch.setattr(evidence.settings, 'rerank_threshold', .42)
    monkeypatch.setattr(evidence.settings, 'lexical_floor', .25)
    lexical_only = {'id': 'lexical', 'dense_score': 0.0, 'lexical_score': 1.0, 'rrf': .03}
    dense_only = {'id': 'dense', 'dense_score': .46, 'lexical_score': 0.0, 'rrf': .01}
    assert evidence.passes_floor(lexical_only)
    ranked = evidence.rank([dense_only, lexical_only])
    assert {c['id'] for c in ranked} == {'lexical', 'dense'}
    assert ranked[0]['id'] == 'lexical'


def test_windows_are_whole_passages_not_word_fragments():
    english = ('The most basic cultural fault line between the west and Islam does not concern democracy-it '
               'involves issues of gender equality and sexual liberalization. The social values of gender '
               'equality could plausibly lie at the heart of any clash between Islam and the west.')
    candidate = {'id': 'c1', 'parent_id': 'p1', 'parent_text': english, 'text': english[:200],
                 'page_start': 50, 'book_id': 'b', 'book_title': 'T', 'dense_score': .5, 'lexical_score': .9,
                 'rrf': .05, 'relation': 'same_concept'}
    windows, report = evidence.select([candidate])
    assert len(windows) == 1
    assert windows[0]['text'] == english
    assert len(windows[0]['spans']) >= 2
    assert all(span['text'] in ' '.join(english.split()) for span in windows[0]['spans'])
    assert report['selected_pages'] == [50]


def test_resolved_spans_are_verbatim_and_display_quote_is_short():
    text = 'One sentence here. A second sentence follows it. A third sentence closes the passage.'
    window = {'spans': evidence.spans_for(text), 'text': text}
    support = evidence.resolve_spans(window, [1, 2])
    assert support in ' '.join(text.split())
    assert evidence.display_quote(support, max_words=4).endswith('…')


def test_one_page_cannot_fill_every_window():
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .5, 'lexical_score': .5, 'rrf': .05,
            'relation': 'same_concept'}
    candidates = [{**base, 'id': f'a{i}', 'parent_id': f'pa{i}', 'parent_text': 'Same page text number %d. ' % i * 20,
                   'text': 'x', 'page_start': 7} for i in range(4)]
    candidates.append({**base, 'id': 'b1', 'parent_id': 'pb', 'parent_text': 'Another page entirely. ' * 20,
                       'text': 'y', 'page_start': 9})
    windows, _ = evidence.select(candidates, max_windows=3)
    assert 9 in [w['page_start'] for w in windows]


def test_evidence_payload_sends_each_passage_once():
    """The prompt must not carry the passage twice, or the real context is double the budget."""
    from app.agents.answer_agent import evidence_payload
    from app.retrieval.evidence import spans_for
    text = 'The first sentence of the passage. The second sentence of the passage.'
    window = {'source_id': 1, 'page_start': 50, 'chapter': '', 'relation': 'same_concept',
              'text': text, 'spans': spans_for(text)}
    payload = evidence_payload([window])[0]
    serialised = json.dumps(payload, ensure_ascii=False)
    assert 'passage_spans' in payload and 'passage' not in payload
    assert serialised.count('The first sentence of the passage') == 1
    # Every span is still present, so nothing the model needs to read was dropped.
    assert [s['span_id'] for s in payload['passage_spans']] == [s['span_id'] for s in window['spans']]


def test_claim_from_an_adjacent_concepts_span_is_not_accepted_as_support():
    """Measured false positive: a gender-equality question drew approved claims from a page
    about CONSTITUTIONAL equality between the Charter's parties, and the local verifier
    accepted statements about the Quran and "both genders" that the span never makes.
    The lexicon already keeps those two concepts apart; verification now uses that."""
    from app.agents import verifier_agent as v
    forms = v.concept_forms(['gender_equality'])
    assert forms, 'the reviewed lexicon must supply gender-equality surface forms'

    # The real page-280 span: constitutional equality, a different reviewed concept.
    other = 'سیرڈ الرسول ہ کی آیینی ووستوری آہیت ۲۷۹( )(۳( آینی مساوات کا جق الیرالہ ض من اھل ھذہ الصحیفۃ۔)۱('
    window = {'source_id': 1, 'text': other, 'spans': [{'span_id': 1, 'text': other}]}
    fabricated = {'source_id': 1, 'text': 'The Quran and Hadith state that men and women are equal.',
                  'support': other}
    assert 'different concept' in v.structural_problem(fabricated, window, 'English', forms)
    # Without a matched concept the check does not apply, so ordinary questions are unaffected.
    assert v.structural_problem(fabricated, window, 'English', ()) == ''

    # The real page-50 English span does carry the concept, so it is allowed through.
    real = ('The most basic cultural fault line between the west and Islam does not concern '
            'democracy-it involves issues of gender equality and sexual liberalization.')
    assert v.mentions_concept(real, forms) is True


def test_a_quoted_outside_writer_keeps_their_attribution():
    """Page 50 quotes Inglehart and Norris. Their view is not the book's own conclusion."""
    from app.agents import verifier_agent as v
    page = ('The most basic cultural fault line between the west and Islam does not concern '
            'democracy-it involves issues of gender equality and sexual liberalization. '
            'Ronald Inglehart, Pippa Norris, Sacred and Secular: Religion and Politics '
            'Worldwide , p. 155.')
    assert v.quoted_authorities(page) >= {'Inglehart', 'Norris'}
    window = {'source_id': 1, 'text': page, 'spans': [{'span_id': 1, 'text': page}]}
    forms = v.concept_forms(['gender_equality'])
    span = page.split(' Ronald')[0]
    unattributed = {'source_id': 1, 'support': span,
                    'text': 'The book concludes that gender equality is the main fault line.'}
    assert 'attribution' in v.structural_problem(unattributed, window, 'English', forms)
    attributed = {'source_id': 1, 'support': span,
                  'text': 'Inglehart and Norris describe gender equality as the main fault line.'}
    assert v.structural_problem(attributed, window, 'English', forms) == ''
