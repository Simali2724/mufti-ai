"""Unreadable OCR must never be shown to a reader, and a question with no subject must not
be searched.

Both are written from one real session. The reader asked "muje kuch explain karo" ("explain
something to me"), which names no subject. It was searched anyway, matched legacy-font OCR
noise on three unrelated pages, spent 224 seconds drafting six claims that every guard then
rejected, and presented the reader with this, under a Sources heading, as the book's words:

    [1] PDF page 310 - «vii h V g ujo f ujo f ujo f»
    [2] PDF page 626 - «o F o F i Zi F o F mF o F i i F o o F o m ]m B o mF m F B mF m F j o o»
    [3] PDF page 297 - «i u h v ]i oF v ii u h v C v M o MV L L O EMD N u r o MV S P N O p QV L N O»
"""
import pytest
from app.retrieval import evidence
from app.agents import formatter, router_agent
from app.retrieval.query_expansion import content_words

# Verbatim from data/diagnostics/20261113-160141-muje-kuch-explain-karo.json.
GARBAGE = [
    'vii h V g ujo f ujo f ujo f',
    'o F o F i Zi F o F mF o F i i F o o F o m ]m B o mF m F B mF m F j o o',
    'i u h v ]i oF v ii u h v C v M o MV L L O EMD N u r o MV S P N O p QV L N O',
]
REAL = [
    'The most basic cultural fault line between the west and Islam does not concern '
    'democracy-it involves issues of gender equality and sexual liberalization.',
    '(Adult Franchise) (No Gender Discrimination in Adult Franchise) '
    '(Difference of Opinion as Fundamental Right)',
    'نوعی مساوات اورجنسی آزادروی کی ساہتی اقارشی طور پر اسلام اور مفرب میں کسی تصادم کی نیاد بن سکتی ہیں۔',
    'Ronald Inglehart, Pippa Norris, Sacred and Secular: Religion and Politics Worldwide , p. 155.',
    'میثاق مدینہ، آرٹیکل میثاق مدینہ، آرٹیکل Right of Equality in Obedience of Law',
]


@pytest.mark.parametrize('text', GARBAGE)
def test_legacy_font_glyph_runs_are_not_readable(text):
    assert evidence.readable(text) is False


@pytest.mark.parametrize('text', REAL)
def test_real_passages_in_any_script_stay_readable(text):
    assert evidence.readable(text) is True


def test_empty_and_whitespace_are_not_readable():
    assert evidence.readable('') is False
    assert evidence.readable('   \n  ') is False
    assert evidence.readable(None) is False


def test_an_unreadable_passage_is_demoted_but_not_discarded():
    """This book's Western-writer quotations sit in paragraphs that are part real English and
    part glyph soup, so dropping unreadable candidates outright would lose real material."""
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .6, 'lexical_score': .6,
            'rrf': .05, 'relation': 'same_concept', 'page_start': 310}
    junk = {**base, 'id': 'j', 'parent_id': 'pj', 'text': 'x', 'parent_text': GARBAGE[0]}
    good = {**base, 'id': 'g', 'parent_id': 'pg', 'page_start': 50, 'text': 'y',
            'parent_text': REAL[0]}
    ranked = evidence.rank([junk, good])
    assert [r['id'] for r in ranked] == ['g', 'j'], 'readable material must rank first'
    assert ranked[1]['readable'] is False
    assert ranked[1]['relevance'] < ranked[0]['relevance']
    assert len(ranked) == 2, 'demoted, not dropped'


def test_no_unreadable_span_is_ever_offered_as_an_excerpt():
    window = {'source_id': 1, 'page_start': 310, 'book_id': 'b', 'book_title': 'T',
              'relation': 'same_concept', 'text': GARBAGE[0],
              'spans': evidence.spans_for(GARBAGE[0])}
    assert evidence.readable_spans(window) == []
    assert formatter.best_span(window, ()) == ''
    text, related = formatter.related_block([window], set(), 'English')
    assert text == '' and related == []
    text, excerpts = formatter.excerpt_block([window], 'English')
    assert excerpts == []


def test_a_window_whose_other_spans_are_junk_still_shows_the_readable_one():
    """Filtering is per span, so a page that mixes real paragraphs with glyph runs still
    yields its real paragraph."""
    window = {'source_id': 1, 'page_start': 50, 'book_id': 'b', 'book_title': 'T',
              'relation': 'same_concept', 'text': GARBAGE[0] + '\n' + REAL[0],
              'spans': [{'span_id': 1, 'text': GARBAGE[0]}, {'span_id': 2, 'text': REAL[0]}]}
    shown = formatter.best_span(window, ())
    assert shown == REAL[0]
    assert [s['span_id'] for s in evidence.readable_spans(window)] == [2]


def test_known_limitation_junk_sharing_one_span_with_real_text_is_not_separated():
    """Documented limitation, not a passing behaviour.

    `spans_for` splits on sentence terminators, and a glyph run contains none, so it merges
    into the following sentence and rides along in the excerpt. The span still reads as real
    text overall, so the reader is not misled into thinking noise is the book's statement,
    and the fully-unreadable case that actually reached a reader IS filtered. Separating junk
    inside a span needs span segmentation to change, which would move retrieval boundaries
    across the whole corpus and must be measured against the benchmark before it is done."""
    mixed = GARBAGE[0] + ' ' + REAL[0]
    spans = evidence.spans_for(mixed)
    assert len(spans) == 1, 'the glyph run has no terminator to split on'
    assert evidence.readable(spans[0]['text']) is True
    assert 'ujo f' in formatter.best_span(
        {'spans': spans, 'text': mixed, 'relation': 'same_concept'}, ())


def test_unreadable_evidence_reports_an_extraction_problem_not_an_absent_answer():
    """The brief keeps extraction_problem distinct. Saying "no verified answer" about pages
    whose text simply failed to extract blames the book for a scanning failure."""
    windows = [{'source_id': i + 1, 'page_start': p, 'book_id': 'b', 'book_title': 'T',
                'relation': 'same_concept', 'text': g, 'spans': evidence.spans_for(g)}
               for i, (p, g) in enumerate(zip((310, 626, 297), GARBAGE))]
    state = {'evidence_windows': windows, 'draft_answer': {'claims': []},
             'verification_report': {'rejected': [{'reason': 'x'}]}, 'errors': []}
    assert formatter.failure_reason(state) == 'extraction_problem'


def test_a_question_naming_no_subject_is_not_searched():
    """"muje kuch explain karo" names nothing to look up. Guessing a subject would be
    inventing the reader's intent; asking which topic they mean is honest and instant."""
    assert content_words('muje kuch  explain karo') == []
    assert router_agent.names_a_topic('muje kuch  explain karo') is False
    assert router_agent.names_a_topic('explain something to me') is False
    assert router_agent.names_a_topic('What does the book say?') is False


def test_naming_any_subject_at_all_is_enough_to_search():
    """A single content word is a subject. This must not become a barrier to real questions."""
    assert router_agent.names_a_topic('mujhe seerat ke bare mein batao') is True
    assert router_agent.names_a_topic('Explain Gender Equality in detail') is True
    assert router_agent.names_a_topic('صنفی مساوات کیا ہے؟') is True
    assert router_agent.names_a_topic('इस किताब में सीरत का क्या महत्व है?') is True
    # Scaffolding-only wording still searches when the reviewed lexicon matched a concept.
    assert router_agent.names_a_topic('iske bare mein batao', ['gender_equality']) is True


@pytest.mark.asyncio
async def test_the_router_asks_for_a_topic_instead_of_searching():
    result = await router_agent.run({'user_input': 'muje kuch  explain karo',
                                     'matched_concepts': []})
    assert result['intent'] == 'needs_topic'


@pytest.mark.asyncio
async def test_a_greeting_is_still_a_greeting_not_a_topic_request():
    result = await router_agent.run({'user_input': 'assalamu alaikum', 'matched_concepts': []})
    assert result['intent'] == 'smalltalk'
