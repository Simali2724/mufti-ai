"""Keep the offline suite out of the real data directory.

Traces written by tests used to land in data/diagnostics/ next to real request traces, which
made mocked runs look like evidence about live behaviour.
"""
import pytest
from app.core import diagnostics


@pytest.fixture(autouse=True)
def _isolate_diagnostics(tmp_path_factory):
    diagnostics.override['dir'] = tmp_path_factory.mktemp('diagnostics')
    try:
        yield
    finally:
        diagnostics.override['dir'] = None


@pytest.fixture(autouse=True)
def _strict_mode_unless_marked(request, monkeypatch):
    """Existing graph tests mock the claim pipeline (answer/verify/repair), so they run in
    strict mode. Tests of the explanation path opt in with @pytest.mark.explain."""
    from app.core.config import settings
    if 'explain' not in request.keywords:
        monkeypatch.setattr(settings, 'answer_mode', 'strict')


@pytest.fixture(autouse=True)
def _clear_model_cooldowns():
    from app.llm import router
    router._model_cooldown.clear()
    yield
    router._model_cooldown.clear()


@pytest.fixture(autouse=True)
def _no_startup_warmup(monkeypatch):
    """The server warms the real search stack at start-up; offline tests must never touch Ollama."""
    from app.core.config import settings
    monkeypatch.setattr(settings, 'warmup_on_start', False)
