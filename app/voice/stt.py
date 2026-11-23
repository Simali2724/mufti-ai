from app.core.config import settings
_model=None
# Reply-language hint -> Whisper language code. Hinglish is spoken Hindi/Urdu but written in Latin
# letters, so Whisper is left to detect it (forcing 'hi' would produce Devanagari).
WHISPER_LANGUAGE={'Urdu':'ur','Hindi':'hi','English':'en'}
def transcribe(path,language_hint=None):
    global _model
    try: from faster_whisper import WhisperModel
    except ImportError: raise RuntimeError('Install requirements-optional.txt for local voice transcription')
    from app.core.config import ROOT
    if _model is None: _model=WhisperModel(settings.whisper_model_size,device='cpu',compute_type='int8',download_root=str(ROOT/'data/whisper'))
    segments,info=_model.transcribe(path,beam_size=3,language=WHISPER_LANGUAGE.get(language_hint or ''))
    return ' '.join(s.text for s in segments).strip(),info.language
