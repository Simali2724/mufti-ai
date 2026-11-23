"""POST /feedback (👍/👎 on an answer) and GET /feedback/summary. See app/core/feedback.py."""
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core import feedback

router = APIRouter()
Reason = Literal['wrong', 'incomplete', 'not_found_but_in_book', 'wrong_language', 'too_long', 'too_short',
                 'bad_reference', 'other']


class FeedbackIn(BaseModel):
    session_id: str = Field(default='default', pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    rating: Literal['up', 'down']
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(default='', max_length=20000)
    reasons: list[Reason] = Field(default_factory=list, max_length=8)
    note: str = Field(default='', max_length=1000)
    pages: list[int] = Field(default_factory=list, max_length=40)
    book_ids: list[str] = Field(default_factory=list, max_length=10)
    language: str = Field(default='', max_length=20)
    answer_style: str = Field(default='', max_length=20)
    reason_code: str = Field(default='', max_length=60)
    answering_model: str = Field(default='', max_length=120)
    verification: str = Field(default='', max_length=40)


@router.post('/feedback')
async def give_feedback(body: FeedbackIn):
    entry = body.model_dump()
    # Keep the start of the answer only: enough to recognise it, not a second copy of history.
    entry['answer'] = entry['answer'][:1500]
    row = feedback.record(entry)
    return {'saved': True, 'id': row['id']}


@router.get('/feedback/summary')
async def feedback_summary(limit: int = 20):
    return feedback.summary(max(1, min(limit, 100)))
