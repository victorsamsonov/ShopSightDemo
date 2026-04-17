from __future__ import annotations

from fastapi import APIRouter

from domain.models import ChatRequest, Config
from application.query_orchestrator import answer_question


router = APIRouter()


@router.post("/chat")
async def chat_endpoint(payload: ChatRequest) -> dict:
    return await answer_question(
        payload.message,
        config=Config(),
        is_followup=payload.is_followup,
        followup_context=payload.followup_context,
    )

