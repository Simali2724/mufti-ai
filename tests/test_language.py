import pytest
from app.core.language import detect
@pytest.mark.parametrize('q,expected',[('नमाज़ क्या है?','Hindi'),('سیرت کی اہمیت کیا ہے؟','Urdu'),('What is the subject of this book?','English'),('Seerat kya hai aur kitab mein kya hai?','Hinglish')])
def test_detect(q,expected): assert detect(q)==expected
def test_hint(): assert detect('Roman text','Urdu')=='Urdu'


def test_rewrite_is_skipped_on_a_local_model_but_kept_for_conversation_context(monkeypatch):
    """The rewrite call costs 90-144s locally and changed no measured retrieval outcome.

    It must still run when there is history to resolve ("what about her rights?"), and when a
    cloud model is available, where it is cheap and its translations are usable.
    """
    from app.agents import language_agent as la
    monkeypatch.setattr(la.settings, 'model_rewrite_without_history', False)

    monkeypatch.setattr(la, 'cloud_available', lambda: False)
    rewrite, why = la.needs_rewrite({'user_input': 'What does the book say about sanitation?'}, [])
    assert rewrite is False and 'local model' in why
    # Conversation context still forces a rewrite, whatever the provider.
    rewrite, _ = la.needs_rewrite({'user_input': 'And her rights?', 'history': [{'question': 'q'}]}, [])
    assert rewrite is True

    monkeypatch.setattr(la, 'cloud_available', lambda: True)
    rewrite, why = la.needs_rewrite({'user_input': 'What does the book say about sanitation?'}, [])
    assert rewrite is True and 'cloud model is available' in why
    # A matched lexicon concept already supplies reviewed cross-script variants.
    rewrite, _ = la.needs_rewrite({'user_input': 'gender equality'}, ['gender_equality'])
    assert rewrite is False
