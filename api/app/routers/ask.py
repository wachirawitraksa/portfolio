from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..netutil import client_ip
from ..rag.ask import ask
from ..rag.llm import LLM, get_llm

router = APIRouter()


class AskBody(BaseModel):
    question: str = Field(max_length=1000)


@router.post("/ask")
async def ask_question(
    body: AskBody, request: Request, db: AsyncSession = Depends(get_db), llm: LLM | None = Depends(get_llm)
):
    """Public question box. Always answers with JSON: `mode` says what kind of reply it is, `sources` lists the
    projects, jobs and articles it came from, `contact_email` is where to go when the site has no answer."""
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "question is empty")
    result = await ask(db, question, client_ip(request), llm)
    return JSONResponse(result.payload(), status_code=429 if result.mode == "rate_limited" else 200)
