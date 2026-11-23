"""Saved answers: POST /saved, GET /saved, GET /saved/{id}, DELETE /saved/{id}. See app/core/saved.py."""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core import saved

router = APIRouter()
ID = r'^[a-f0-9]{12}$'


class SavedCitation(BaseModel):
    id: int
    book_id: str = Field(max_length=64)
    book_title: str = Field(default='', max_length=300)
    page: int
    printed_label: int | None = None
    excerpt: str = Field(default='', max_length=2000)


class SavedIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=40000)
    answer_format: str = Field(default='markdown', max_length=20)
    citations: list[SavedCitation] = Field(default_factory=list, max_length=60)
    language: str = Field(default='', max_length=20)
    verification: str = Field(default='', max_length=40)
    answering_model: str = Field(default='', max_length=120)
    answer_style: str = Field(default='', max_length=20)
    session_id: str = Field(default='', pattern=r'^[a-zA-Z0-9_-]{0,80}$')


@router.post('/saved')
async def save(body: SavedIn):
    item, created = saved.add(body.model_dump())
    return {'id': item['id'], 'created': created}


@router.get('/saved')
async def list_saved():
    return saved.listing()


@router.get('/saved/{item_id}')
async def get_saved(item_id: str):
    item = saved.get(item_id) if re.fullmatch(ID, item_id) else None
    if not item:
        raise HTTPException(404, 'Saved answer not found')
    return item


@router.delete('/saved/{item_id}')
async def delete_saved(item_id: str):
    if not re.fullmatch(ID, item_id) or not saved.remove(item_id):
        raise HTTPException(404, 'Saved answer not found')
    return {'deleted': True}
