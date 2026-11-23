"""POST /quiz — a short multiple-choice quiz built from an answer in this conversation.

The answer is looked up in the server-side conversation history by session and question, so the
quiz can only ever be built from an answer the app itself produced and grounded. See
app/agents/quiz_agent.py.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.agents import quiz_agent
from app.llm.router import ProviderUnavailable

router = APIRouter()


class QuizIn(BaseModel):
    session_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    question: str = Field(min_length=1, max_length=4000)
    count: int = Field(default=4, ge=2, le=6)


def find_turn(history, question):
    """The latest turn with exactly this question (follow-ups can repeat a question)."""
    return next((t for t in reversed(history or []) if t.get('question') == question), None)


@router.post('/quiz')
async def quiz(body: QuizIn, request: Request):
    state = await request.app.state.graph.aget_state({'configurable': {'thread_id': body.session_id}})
    turn = find_turn(state.values.get('history', []), body.question)
    if turn is None:
        raise HTTPException(404, 'That answer is not in this conversation any more.')
    if not turn.get('grounded') or not turn.get('citations'):
        raise HTTPException(409, 'A quiz can only be made from an answer that came from the book.')
    try:
        result = await quiz_agent.make_quiz(turn, body.count)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except ProviderUnavailable:
        raise HTTPException(503, 'No AI model is reachable right now (quota or connection). Please try again later.')
    if not result['questions']:
        raise HTTPException(422, 'No quiz question passed the check against the answer. Please try again.')
    return result
