"""Validated, non-secret model preferences for the UI and request router."""
import os
import re
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.config import ROOT, config, settings

CLOUDS = ('anthropic', 'openai', 'gemini')
PROVIDERS = (*CLOUDS, 'ollama')
SETTINGS_PATH = ROOT / 'model-settings.json'

def default_models():
    return {p: settings.ollama_chat_model if p == 'ollama' else config['models'][p] for p in PROVIDERS}

class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['auto', 'anthropic', 'openai', 'gemini', 'ollama'] = 'auto'
    cloud_order: list[str] = Field(default_factory=lambda: list(CLOUDS))
    models: dict[str, str] = Field(default_factory=default_models)

    @field_validator('cloud_order')
    @classmethod
    def validate_order(cls, value):
        if len(value) != 3 or set(value) != set(CLOUDS):
            raise ValueError('Choose each cloud provider exactly once')
        return value

    @field_validator('models')
    @classmethod
    def validate_models(cls, value):
        if set(value) != set(PROVIDERS):
            raise ValueError('A model is required for every provider')
        if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}', model) for model in value.values()):
            raise ValueError('Use model IDs only (letters, numbers, dots, hyphens, colons or slashes)')
        return value

def get_preferences() -> Preferences:
    if SETTINGS_PATH.exists():
        return Preferences.model_validate_json(SETTINGS_PATH.read_text(encoding='utf-8'))
    configured = [p.strip() for p in settings.llm_provider_order.split(',') if p.strip() in CLOUDS]
    return Preferences(cloud_order=list(dict.fromkeys([*configured, *CLOUDS])))

def save_preferences(preferences: Preferences) -> Preferences:
    preferences = Preferences.model_validate(preferences)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='.model-settings-', suffix='.json', dir=SETTINGS_PATH.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
            file.write(preferences.model_dump_json(indent=2))
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, SETTINGS_PATH)
    finally:
        Path(name).unlink(missing_ok=True)
    return preferences

def build_provider_order(preferences: Preferences) -> list[str]:
    if preferences.mode == 'ollama':
        return ['ollama']
    clouds = list(preferences.cloud_order)
    if preferences.mode in CLOUDS:
        clouds.remove(preferences.mode)
        clouds.insert(0, preferences.mode)
    return [*clouds, 'ollama']

request_preferences: ContextVar[Preferences | None] = ContextVar('model_preferences', default=None)
request_trace: ContextVar[list | None] = ContextVar('model_trace', default=None)
request_api_keys: ContextVar[dict[str, str]] = ContextVar('request_api_keys', default={})

@contextmanager
def model_request():
    """Freeze settings for one whole answer, including all agents and retries."""
    preference_token = request_preferences.set(get_preferences().model_copy(deep=True))
    trace = []
    trace_token = request_trace.set(trace)
    try:
        yield trace
    finally:
        request_trace.reset(trace_token)
        request_preferences.reset(preference_token)
