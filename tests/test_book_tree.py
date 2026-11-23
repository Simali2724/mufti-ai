"""The Book / Chapter / Section / page-range tree, and the navigation route built on it.

These run against the tree persisted for the real book when it is present, and against a
synthetic outline otherwise, so the suite stays meaningful on a machine without the PDF.
"""
import json
import pytest
from app.ingestion import book_tree
from app.retrieval import tree_nav

BOOK_ID = '46a52585612a906c'
SYNTHETIC = {
    'book_id': 'synthetic', 'page_count': 100, 'source': 'pdf_outline', 'outline_entries': 5,
    'source_hash': 'x', 'problems': [],
    'chapters': [
        {'id': 'synthetic-c1', 'kind': 'chapter', 'title': '🔰 باب 1: پہلا باب',
         'parent_id': 'synthetic', 'page_start': 1, 'page_end': 49, 'sections': [
             {'id': 'synthetic-s1', 'kind': 'section', 'title': 'صنفی مساوات کا بیان',
              'parent_id': 'synthetic-c1', 'page_start': 10, 'page_end': 19},
             {'id': 'synthetic-s2', 'kind': 'section', 'title': 'آئینی مساوات کا حق',
              'parent_id': 'synthetic-c1', 'page_start': 20, 'page_end': 49}]},
        {'id': 'synthetic-c2', 'kind': 'chapter', 'title': '🔰 باب 2: دوسرا باب',
         'parent_id': 'synthetic', 'page_start': 50, 'page_end': 100, 'sections': []}]}


@pytest.fixture
def synthetic(monkeypatch):
    monkeypatch.setitem(book_tree._cache, 'synthetic', SYNTHETIC)
    return SYNTHETIC


def test_a_page_resolves_to_its_chapter_and_section(synthetic):
    located = book_tree.locate('synthetic', 15)
    assert located['section_id'] == 'synthetic-s1'
    assert located['chapter_id'] == 'synthetic-c1'
    assert (located['page_start'], located['page_end']) == (10, 19)
    # A page inside the chapter but before its first section still resolves to the chapter.
    assert book_tree.locate('synthetic', 5)['chapter_id'] == 'synthetic-c1'
    assert book_tree.locate('synthetic', 5)['section_id'] == ''
    # A page outside every chapter is reported as such, not guessed at.
    assert book_tree.locate('synthetic', 999) == {}


def test_validation_reports_every_broken_range_not_just_the_first():
    broken = [{'id': 'c1', 'page_start': 10, 'page_end': 5, 'sections': [
        {'id': 's1', 'parent_id': 'c1', 'page_start': 1, 'page_end': 2},
        {'id': 's2', 'parent_id': 'other', 'page_start': 10, 'page_end': 11}]}]
    problems = book_tree.validate(broken, 100)
    assert len(problems) >= 3, problems
    assert any('broken parent link' in p for p in problems)


def test_a_chapter_is_recognised_by_its_marker_or_its_word():
    assert book_tree.is_chapter('🔰 باب 1: قرآن کا اُسلوب') is True
    assert book_tree.is_chapter('اِبتدائیہ: مطالعۂ سیرت کا منہاج') is True
    assert book_tree.is_chapter('صنفی مساوات کا بیان') is False
    assert book_tree.clean_title('🔰 باب 1: \nقرآن') == 'باب 1: قرآن'


def test_the_navigation_route_matches_clean_titles_and_bounds_what_it_returns(synthetic):
    """The whole point of the route: the question's correctly spelled Urdu matches the
    outline title even though the OCR'd body text spells it differently."""
    nodes = tree_nav.match_nodes('synthetic', 'آئینی مساوات کا حق کیا ہے؟')
    assert nodes and nodes[0]['id'] == 'synthetic-s2'
    # A section's pages are capped, so a 30-page chapter cannot swamp the candidate pool.
    pages = tree_nav.pages_for(nodes, limit=4)
    assert len(pages) == 4


def test_a_single_shared_word_is_not_enough_to_match_a_section(synthetic):
    """A section title is short; one common word would match far too much."""
    assert tree_nav.match_nodes('synthetic', 'مساوات') == []
    assert tree_nav.match_nodes('synthetic', '') == []


@pytest.mark.skipif(not book_tree.load(BOOK_ID), reason='real book tree not built here')
def test_the_real_books_tree_is_valid_and_locates_the_reviewed_pages():
    tree = book_tree.load(BOOK_ID)
    assert tree['problems'] == [], tree['problems']
    assert tree['source'] == 'pdf_outline' and tree['outline_entries'] > 100
    # The two pages the brief names, and the rival concept the guards must keep apart.
    assert 'مغرب' in book_tree.locate(BOOK_ID, 50)['section']
    assert book_tree.locate(BOOK_ID, 257)['chapter'].startswith('باب 4')
    assert 'آئینی مساوات' in book_tree.locate(BOOK_ID, 280)['section']


@pytest.mark.skipif(not book_tree.load(BOOK_ID), reason='real book tree not built here')
def test_every_section_range_lies_inside_its_chapter():
    tree = book_tree.load(BOOK_ID)
    for chapter in tree['chapters']:
        assert chapter['page_start'] <= chapter['page_end'] <= tree['page_count']
        for section in chapter['sections']:
            assert chapter['page_start'] <= section['page_start'] <= section['page_end'] <= chapter['page_end']
            assert section['parent_id'] == chapter['id']


@pytest.mark.skipif(not book_tree.load(BOOK_ID), reason='real book tree not built here')
def test_the_outline_title_is_cleaner_than_the_ocr_body_text():
    """The measured asymmetry the tree exists to exploit: the body text of page 280 spells
    the concept 'آینی مساوات' and the outline spells it 'آئینی مساوات'. Only the second
    matches the reviewed lexicon, which is how the rival concept is recognised at all."""
    from app.agents.verifier_agent import concept_guard, mentions_concept
    guard = concept_guard(['gender_equality'])
    rivals = [forms for cid, forms in guard['competing'] if cid == 'constitutional_equality']
    assert rivals, 'the lexicon must still separate constitutional from gender equality'
    title = book_tree.locate(BOOK_ID, 280)['section']
    assert mentions_concept(title, rivals[0]), title


def test_a_tree_built_from_a_different_pdf_is_not_used(monkeypatch):
    """A stale tree is worse than none: it would caption a citation with a heading from a
    different edition. Detected by comparing two recorded hashes, not by re-reading 16 MB."""
    monkeypatch.setattr(book_tree, 'catalog',
                        lambda: [{'id': 'synthetic', 'hash': 'NEW-BOOK-HASH'}])
    assert book_tree.is_stale({**SYNTHETIC, 'source_hash': 'OLD-BOOK-HASH'}) is True
    assert book_tree.is_stale({**SYNTHETIC, 'source_hash': 'NEW-BOOK-HASH'}) is False
    # An uncatalogued book or a tree without a hash is left alone rather than discarded.
    monkeypatch.setattr(book_tree, 'catalog', lambda: [])
    assert book_tree.is_stale({**SYNTHETIC, 'source_hash': 'OLD-BOOK-HASH'}) is False
