from typing import TypedDict


class AgentState(TypedDict, total=False):
    bibliography_answered: bool
    user_input: str
    input_modality: str
    detected_language: str
    normalized_query_en_ur_ar: list[str]
    search_queries: list[dict]
    matched_concepts: list[str]
    intent: str
    topics: list[str]
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    evidence_windows: list[dict]
    previous_windows: list[dict]
    retrieval_failed: bool
    search_rounds: int
    expanded: bool
    draft_answer: dict
    verification_report: dict
    final_answer: str
    citations: list[dict]
    related: list[dict]
    coverage: str
    missing_aspects: list[str]
    provider_used: str
    retries: int
    repair_rounds: int
    repaired: bool
    errors: list[str]
    language_hint: str
    grounded: bool
    history: list[dict]
    evidence_batch: int
    reason_code: str
    retrieval_query: str
    explanation: dict
    explain_rounds: int
    answer_format: str
    verification: str
    answer_style: str
    scope: dict
    scope_applied: bool
    followups: list[str]
