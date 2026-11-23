from typing import Literal
from pydantic import BaseModel, Field


AnswerStyle = Literal['detailed', 'short', 'simple', 'points']


class Scope(BaseModel):
    """Search only inside one book, optionally only inside a page range (a chapter/section).

    Set by the UI's chapter explorer ("Explain this chapter", "Focus on this chapter"). The
    retriever falls back to the whole library, and says so, when the scope has no match.
    """
    book_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    label: str = Field(default='', max_length=200)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default='default', pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    language_hint: Literal['auto', 'Hindi', 'Urdu', 'English', 'Hinglish'] = 'auto'
    stream: bool = False
    # How the explanation is written (app/agents/explain_agent.STYLE_NOTES). Never changes
    # grounding: every style still cites every factual sentence and is audited the same way.
    answer_style: AnswerStyle = 'detailed'
    scope: Scope | None = None


class Citation(BaseModel):
    id: int
    book_id: str
    book_title: str
    page: int
    printed_label: int | None = None
    chapter: str = ''
    excerpt: str
    full_support: str = ''
    ocr: bool = False
    corrected: bool = False
    correction_source: str = ''
    relation: str = 'same_concept'
    transcription_reviewed: bool = False


class RelatedPassage(BaseModel):
    id: int
    book_id: str
    book_title: str
    page: int
    printed_label: int | None = None
    chapter: str = ''
    excerpt: str
    ocr: bool = False
    relation: str = 'related_concept'


class ChatResponse(BaseModel):
    answer: str
    language: str
    citations: list[Citation] = []
    related: list[RelatedPassage] = []
    provider_used: str
    model_used: str = ''
    fallback_used: bool = False
    execution: list[dict] = Field(default_factory=list)
    reason_code: str = ''
    retrieved_count: int = 0
    evidence_pages: list[int] = Field(default_factory=list)
    grounded: bool
    coverage: str = 'none'
    missing_aspects: list[str] = Field(default_factory=list)
    selected_provider: str = ''
    selected_model: str = ''
    answering_provider: str = ''
    answering_model: str = ''
    fallback_reason: str = ''
    latency_ms: int
    status: str = 'complete'
    # 'markdown' for the explanation path; the UI renders headings, lists and [n] citations.
    answer_format: str = 'text'
    # 'audited' (every sentence fact-checked against the sources), 'citations_checked' (local
    # model, citations validated in code only), 'claims_verified' (strict pipeline), or ''.
    verification: str = ''
    # Suggested next questions (clickable in the UI). They are questions, never facts, and are
    # either written by the answering model from the same sources or built from the book's
    # own chapter/section titles. See explain_agent.followups_for.
    followups: list[str] = Field(default_factory=list)
    answer_style: str = 'detailed'
    # The search scope actually used: {'book_id','page_start','page_end','label','applied'}.
    # applied=False means nothing matched inside the scope and the whole library was searched.
    scope: dict | None = None
