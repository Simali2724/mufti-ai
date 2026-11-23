"""Failure-driven tests for the answer stage, written from measured live failures.

Every test here reproduces something this application actually did wrong on the real book,
against the real page text where possible. The guards are tested in BOTH directions: each
relaxation has a negative case proving the protection it loosened is still in force, and each
new rejection has a positive case proving it does not refuse a sound claim.
"""
import pytest
from app.agents import verifier_agent as v
from app.agents import repair_agent as r
from app.retrieval import evidence

# The real text of PDF page 50, parent paragraph p50-2, from segment build 20261112-094445.
PAGE_50 = (
    'The most basic cultural fault line between the west and Islam does not concern '
    'democracy-it involves issues of gender equality and sexual liberalization. The social '
    'values of gender equality and sexual liberalization could plausibly lie at the heart of '
    'any "clash" between Islam and the west. The analysis of these social attitudes reveals '
    'the extent of the gulf between Islam and the west, with a stronger and more significant '
    'gap on these issues than across most of the political values. Ronald Inglehart, Pippa '
    'Norris, Sacred and Secular: Religion and Politics Worldwide , p. 155.')
# The real page-280 span: constitutional equality between the Charter's parties, as OCR
# produced it. The spelling is degraded (آینی, جق), which is why the reviewed lexicon form
# does not match the body text and the clean outline title has to supply it in the live app.
PAGE_280 = 'سیرڈ الرسول ہ کی آیینی ووستوری آہیت ۲۷۹( )(۳( آینی مساوات کا جق الیرالہ ض من اھل ھذہ الصحیفۃ۔)۱('
# The same page's CLEAN outline title, which is what the tree contributes.
PAGE_280_TITLE = 'آئینی مساوات کا حق'


def window_for(text, page=50):
    return {'source_id': 1, 'text': text, 'spans': evidence.spans_for(text), 'page_start': page,
            'book_id': 'b', 'book_title': 'T', 'relation': 'same_concept', 'relevance': .76,
            'printed_label': page - 1, 'chapter': ''}


@pytest.fixture
def guard():
    g = v.concept_guard(['gender_equality'])
    assert g and g['asked'], 'the reviewed lexicon must supply gender-equality surface forms'
    return g


# --------------------------------------------------------------------------- attribution scope

def test_attribution_is_required_only_inside_the_region_the_citation_closes():
    """The brief: attribution must attach to the actual quoted span, not to every sentence in
    a passage that happens to carry a footnote. The old guard asked the whole window."""
    quoted_then_book_voice = (
        'Gender equality is the deepest fault line. Ronald Inglehart, Pippa Norris, Sacred '
        'and Secular: Religion and Politics Worldwide , p. 155. The author of this book then '
        'argues that Islamic social values rest on revelation rather than on opinion polls.')
    window = window_for(quoted_then_book_voice)
    quoted_span = 'Gender equality is the deepest fault line.'
    book_span = ('The author of this book then argues that Islamic social values rest on '
                 'revelation rather than on opinion polls.')
    assert v.needs_attribution(quoted_then_book_voice, quoted_span) is True
    # The book's own sentence, printed AFTER the citation, is not Inglehart and Norris's view.
    assert v.needs_attribution(quoted_then_book_voice, book_span) is False
    unattributed = {'source_id': 1, 'support': book_span,
                    'text': 'The book grounds Islamic social values in revelation, not in polling.'}
    assert v.diagnose(unattributed, window, 'English')[0] == ''


def test_a_quoted_view_still_cannot_be_presented_as_the_books_own(guard):
    """The protection the scoping loosened must still hold where it matters: on page 50 the
    quote runs up to the citation, so every claim drawn from it must name the writers."""
    window = window_for(PAGE_50)
    span = window['spans'][0]['text']
    unattributed = {'source_id': 1, 'support': span,
                    'text': 'The book concludes that gender equality divides Islam and the west most deeply.'}
    code, reason = v.diagnose(unattributed, window, 'English', guard)
    assert code == 'attribution' and 'Inglehart' in reason
    attributed = {'source_id': 1, 'support': span,
                  'text': 'Inglehart and Norris place the deepest divide at gender equality, not democracy.'}
    assert v.diagnose(attributed, window, 'English', guard)[0] == ''


def test_deterministic_attribution_repair_rescues_the_measured_live_failure(guard):
    """The live failure this whole change exists for: pages 50 and 257 were retrieved, the
    claim was on the right page with the right concept, and it was thrown away solely because
    a 1.7B model would not write the two names the book itself prints beside the quote."""
    window = window_for(PAGE_50)
    claim = {'claim_id': 1, 'source_id': 1, 'page': 50, 'support': window['spans'][0]['text'],
             'text': 'Gender equality, not democracy, marks the deepest divide between Islam and the west.'}
    code, reason = v.diagnose(claim, window, 'English', guard)
    assert code == 'attribution'
    repaired = r.deterministic_repair({**claim, 'code': code, 'reason': reason},
                                      window, 'English', guard)
    assert repaired is not None, 'an attribution-only defect must be repairable without a model'
    assert 'Inglehart' in repaired['text'] and 'Norris' in repaired['text']
    assert v.diagnose(repaired, window, 'English', guard)[0] == ''
    assert v.quoted_attributions(PAGE_50) == ['Ronald Inglehart', 'Pippa Norris']


# ------------------------------------------------------------------------------ concept scope

def test_a_paraphrase_without_the_concept_keyword_is_accepted_in_an_on_concept_paragraph(guard):
    """Requiring the concept word inside the span itself was too strong: the next sentence of
    the same quoted paragraph is legitimate support for a faithful paraphrase."""
    window = window_for(PAGE_50)
    third = window['spans'][2]['text']
    assert 'gender equality' not in third.lower()
    claim = {'source_id': 1, 'support': third,
             'text': 'Inglehart and Norris find the social gulf wider than the political one.'}
    assert v.diagnose(claim, window, 'English', guard)[0] == ''


def test_an_adjacent_concepts_span_is_still_refused_as_support(guard):
    """Measured false positive: a gender-equality question drew approved claims from a page
    about CONSTITUTIONAL equality between the Charter's parties."""
    window = window_for(PAGE_280, page=280)
    fabricated = {'source_id': 1, 'support': PAGE_280,
                  'text': 'The Quran and Hadith state that men and women are equal in rights.'}
    assert v.diagnose(fabricated, window, 'English', guard)[0] == 'wrong_concept'
    # With no matched concept the check does not apply, so ordinary questions are unaffected.
    assert v.diagnose(fabricated, window, 'English')[0] == ''


def test_a_rival_concept_is_named_in_the_rejection(guard):
    window = window_for('The charter guarantees constitutional equality to every party to it.',
                        page=281)
    claim = {'source_id': 1, 'support': window['spans'][0]['text'],
             'text': 'The book says men and women are equal.'}
    code, reason = v.diagnose(claim, window, 'English', guard)
    assert code == 'wrong_concept' and 'constitutional equality' in reason


# ---------------------------------------------------------------------- reference-only support

def test_a_bibliographic_line_cannot_support_a_claim(guard):
    """The citation line matches the question's words and states nothing at all."""
    window = window_for(PAGE_50)
    citation = next(s['text'] for s in window['spans'] if 'Sacred and Secular' in s['text'])
    claim = {'source_id': 1, 'support': citation,
             'text': 'Inglehart and Norris wrote about gender equality worldwide.'}
    assert v.diagnose(claim, window, 'English', guard)[0] == 'reference_only'


# ------------------------------------------------------------------------- qualification/hedge

def test_a_hedged_source_statement_may_not_be_restated_as_settled_fact(guard):
    """Measured: the span says gender equality "could plausibly" lie at the heart of a clash;
    the model restated it as "are central to", asserting what the book carefully did not."""
    window = window_for(PAGE_50)
    hedged_span = next(s['text'] for s in window['spans'] if 'could plausibly' in s['text'])
    flattened = {'source_id': 1, 'support': hedged_span,
                 'text': 'Inglehart and Norris state that gender equality is the central issue dividing them.'}
    assert v.diagnose(flattened, window, 'English', guard)[0] == 'hedge_dropped'
    kept = {'source_id': 1, 'support': hedged_span,
            'text': 'Inglehart and Norris suggest gender equality may sit at the centre of any such clash.'}
    assert v.diagnose(kept, window, 'English', guard)[0] == ''


def test_a_hedge_elsewhere_in_a_long_span_does_not_reject_an_unrelated_claim():
    """The check is scoped to the sentence the claim restates, so a hedge in a different
    sentence of a long passage is not a reason to refuse a flatly stated fact."""
    span = ('The Prophet migrated to Madinah in the thirteenth year of the mission. '
            'Some historians suggest the exact month may never be settled.')
    window = window_for(span, page=120)
    claim = {'source_id': 1, 'support': span,
             'text': 'The migration to Madinah took place in the mission\'s thirteenth year.'}
    assert v.diagnose(claim, window, 'English')[0] == ''


# ------------------------------------------------------------------------------- copied spans

def test_a_claim_that_reproduces_its_span_is_refused(guard):
    """The reader asked for an explanation, not pasted quotations. Once the qualification
    guard landed, copying the sentence verbatim was the cheapest way to satisfy it."""
    window = window_for(PAGE_50)
    span = next(s['text'] for s in window['spans'] if 'could plausibly' in s['text'])
    pasted = {'source_id': 1, 'support': span, 'text': 'Inglehart and Norris: ' + span}
    assert v.diagnose(pasted, window, 'English', guard)[0] == 'copied_span'


def test_a_genuine_paraphrase_is_not_mistaken_for_a_copy(guard):
    window = window_for(PAGE_50)
    span = next(s['text'] for s in window['spans'] if 'could plausibly' in s['text'])
    paraphrase = {'source_id': 1, 'support': span,
                  'text': 'Inglehart and Norris argue these social values may be what really divides the two.'}
    assert v.diagnose(paraphrase, window, 'English', guard)[0] == ''


def test_a_short_claim_is_exempt_from_the_copy_check():
    """A seven-word statement cannot be restated without reusing its words."""
    assert v.copies_span('The charter was written in Madinah.',
                         'The charter was written in Madinah.') is False


# -------------------------------------------------------------------------- relevance verdicts

def test_relevance_verdict_gates_only_where_the_question_demands_a_relation():
    """Measured: on "Explain Gender Equality in detail" the local verifier returned
    answers_question=false while its own feedback read "The claim is fully entailed by the
    span." A self-contradicting relevance verdict must not manufacture a false refusal."""
    assert v.demands_relation('Why should we study the biography of the Prophet?') is True
    assert v.demands_relation('When did the migration happen?') is True
    assert v.demands_relation('Explain Gender Equality in detail') is False
    assert v.demands_relation('Gender equality ke bare mein batao') is False
    assert v.demands_relation('صنفی مساوات کی تفصیل بیان کریں') is False
    assert v.demands_relation('نماز کیوں پڑھی جاتی ہے؟') is True


# ------------------------------------------------------------------------------- repair router

def test_repair_refuses_to_touch_a_claim_resting_on_the_wrong_concept():
    """There is nothing in that claim's evidence to rewrite, and finding it a different source
    is exactly the fabrication the guards exist to stop."""
    rejected = [{'claim_id': 1, 'code': 'wrong_concept', 'text': 'x'},
                {'claim_id': 2, 'code': 'span_absent', 'text': 'y'},
                {'claim_id': 3, 'code': 'attribution', 'text': 'z'},
                {'claim_id': 4, 'code': 'hedge_dropped', 'text': 'w'}]
    assert [c['claim_id'] for c in r.repairable(rejected)] == [3, 4]


def test_repair_keeps_the_claims_that_already_passed():
    """"Keep independently supported claims; do not reject an entire answer because one
    claim failed." A repair round must not drop the verified ones on the way through."""
    draft = {'sections': [{'heading': 'A', 'claims': [{'claim_id': 1, 'text': 'kept', 'verified': True}]}],
             'claims': [{'claim_id': 1, 'text': 'kept', 'verified': True}]}
    merged = r.reinstate(draft, [{'claim_id': 2, 'text': 'repaired', 'section_heading': 'A'}])
    assert [c['claim_id'] for c in merged['claims']] == [1, 2]
    assert len(merged['sections']) == 1


def test_verification_does_not_pay_twice_for_an_already_verified_claim():
    """A claim carried through a repair round keeps its verdict instead of costing another
    local model call, which on this hardware is minutes."""
    window = window_for(PAGE_50)
    draft = {'claims': [{'claim_id': 1, 'source_id': 1, 'verified': True,
                         'support': window['spans'][2]['text'],
                         'text': 'Inglehart and Norris find the social gulf wider than the political one.'}],
             'sections': []}
    kept, rejected = v.structural_pass(draft, [window], 'English')
    assert not rejected and kept[0]['verified'] is True


# ------------------------------------------------------------------------- evidence selection

def test_adjacent_concept_passages_do_not_crowd_out_the_on_concept_material():
    """Measured: four of six evidence windows were garbled Charter pages carrying no
    gender-equality wording in any script, and the model drafted six claims from them that
    verification rejected one by one."""
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .52, 'lexical_score': .4,
            'rrf': .05, 'relation': 'same_concept'}
    on_concept = {**base, 'id': 'on', 'parent_id': 'p-on', 'page_start': 50, 'text': 'x',
                  'parent_text': PAGE_50}
    off = [{**base, 'id': f'off{i}', 'parent_id': f'p-off{i}', 'page_start': 280 + i,
            'text': 'y', 'parent_text': f'{PAGE_280_TITLE}. ' + PAGE_280 + f' article {i}. ' * 12}
           for i in range(4)]
    # Enough on-concept material to fill the budget: the adjacent ones are held back.
    on_many = [{**on_concept, 'id': f'on{i}', 'parent_id': f'p-on{i}', 'page_start': 50 + i}
               for i in range(4)]
    windows, _ = evidence.select(on_many + off, max_windows=6, token_budget=4000,
                                 concepts=['gender_equality'])
    relations = [w['relation'] for w in windows]
    assert relations[0] == 'same_concept', 'on-concept material must come first'
    assert relations.count('related_concept') <= 2, 'adjacent-concept windows must be capped'
    assert any(w['relation'] == 'related_concept' for w in windows), 'still offered, not discarded'


def test_the_adjacent_concept_cap_never_shrinks_the_evidence_set():
    """Measured regression: with only one on-concept passage available, a hard cap cut
    west-en-2's evidence from eight windows to three and lost the reviewed pages. The cap
    must stop adjacent material CROWDING OUT better evidence, never leave the model with
    less evidence than it could have had."""
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .52, 'lexical_score': .4,
            'rrf': .05, 'relation': 'same_concept'}
    on_concept = {**base, 'id': 'on', 'parent_id': 'p-on', 'page_start': 50, 'text': 'x',
                  'parent_text': PAGE_50}
    off = [{**base, 'id': f'off{i}', 'parent_id': f'p-off{i}', 'page_start': 280 + i,
            'text': 'y', 'parent_text': f'{PAGE_280_TITLE}. ' + PAGE_280 + f' article {i}. ' * 12}
           for i in range(4)]
    windows, _ = evidence.select([on_concept] + off, max_windows=6, token_budget=4000,
                                 concepts=['gender_equality'])
    assert len(windows) == 5, 'every available passage should still reach the model'
    assert windows[0]['relation'] == 'same_concept'


def test_off_concept_passages_are_demoted_not_dropped():
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .9, 'lexical_score': .9,
            'rrf': .05, 'relation': 'same_concept'}
    rival = {**base, 'id': 'off', 'parent_id': 'p', 'page_start': 280, 'text': 'y',
             'parent_text': f'{PAGE_280_TITLE}. ' + PAGE_280}
    guard = v.concept_guard(['gender_equality'])
    ranked = evidence.rank([rival], guard)
    assert ranked[0]['relation'] == 'related_concept'
    assert ranked[0]['relevance'] < evidence.relevance(rival)


def test_a_passage_the_lexicon_says_nothing_about_is_not_demoted():
    """Measured regression (west-en-2): passages were demoted and capped merely for carrying
    no reviewed concept wording, which cost the case its reviewed pages. Absence from a
    hand-written lexicon is not evidence that a passage is off topic - only a passage
    carrying a RIVAL reviewed concept is treated as a distractor."""
    base = {'book_id': 'b', 'book_title': 'T', 'dense_score': .52, 'lexical_score': .4,
            'rrf': .05, 'relation': 'same_concept'}
    unknown = {**base, 'id': 'u', 'parent_id': 'pu', 'page_start': 61, 'text': 'y',
               'parent_text': 'His bedding was a mat that left marks on his side.'}
    guard = v.concept_guard(['gender_equality'])
    ranked = evidence.rank([unknown], guard)
    assert ranked[0]['relation'] == 'same_concept'
    assert ranked[0]['relevance'] == evidence.relevance(unknown)


# ---------------------------------------------------------------------------- grounding floor

def test_a_respectful_sounding_fabrication_is_refused(guard):
    """Measured, and approved by the 1.7B verifier before this check existed: from a span
    calling gender equality a cultural fault line BETWEEN Islam and the west, the drafter
    produced "Gender equality is a fundamental principle in Islam, emphasizing the equal
    rights and responsibilities of men and women in all aspects of life." The span says
    nothing about rights, responsibilities, or what Islam holds."""
    window = window_for(PAGE_50)
    support = window['spans'][0]['text'] + ' ' + window['spans'][1]['text']
    fabricated = {'source_id': 1, 'support': support,
                  'text': ('As quoted from Ronald Inglehart and Pippa Norris: Gender equality is a '
                           'fundamental principle in Islam, emphasizing the equal rights and '
                           'responsibilities of men and women in all aspects of life.')}
    assert v.diagnose(fabricated, window, 'English', guard)[0] == 'weak_grounding'


def test_the_grounding_floor_passes_a_faithful_same_language_paraphrase(guard):
    window = window_for(PAGE_50)
    good = {'source_id': 1, 'support': window['spans'][2]['text'],
            'text': ('As quoted from Ronald Inglehart and Pippa Norris: the analysis of these '
                     'social attitudes reveals a significant gap between Islamic and Western values.')}
    assert v.diagnose(good, window, 'English', guard)[0] == ''


def test_the_grounding_floor_never_applies_across_scripts():
    """A faithful English explanation of an Urdu passage shares no tokens with it by
    construction. Refusing those would break the multilingual answering this app exists for."""
    urdu = 'نوعی مساوات اورجنسی آزادروی کی ساہتی اقار اسلام اور مفرب میں کسی تصادم کی نیاد بن سکتی ہیں۔'
    english = 'Gender equality may be a basis of conflict between Islam and the west.'
    assert v.weakly_grounded(english, urdu) is False
    assert v.same_script(english, urdu) is False


def test_a_fabrication_cannot_be_rescued_by_gluing_a_correct_sentence_onto_it(guard):
    """Measured escape route: asked to repair a fabricated claim, the local model kept the
    fabrication and appended a correct, properly attributed sentence. Names present, hedge
    present, wording shared with the span — every guard passed individually while the claim
    still asserted what the book never says."""
    window = window_for(PAGE_50)
    glued = {'source_id': 1, 'support': window['spans'][1]['text'],
             'text': ('Gender equality is a fundamental principle in Islam, emphasizing the equal '
                      'rights and responsibilities of men and women in all aspects of life. Ronald '
                      'Inglehart and Pippa Norris write that the social values of gender equality '
                      'and sexual liberalization could plausibly lie at the heart of any clash '
                      'between Islam and the west.')}
    assert v.diagnose(glued, window, 'English', guard)[0] == 'multi_sentence'


def test_the_one_sentence_rule_does_not_refuse_an_ordinary_claim(guard):
    window = window_for(PAGE_50)
    single = {'source_id': 1, 'support': window['spans'][2]['text'],
              'text': 'Inglehart and Norris report a wider social gulf than a political one.'}
    assert v.diagnose(single, window, 'English', guard)[0] == ''
    # The deterministic attribution prefix uses a colon, so a repaired claim stays one sentence.
    assert v.sentence_count('As quoted from Ronald Inglehart and Pippa Norris: the gulf is wide.') == 1
