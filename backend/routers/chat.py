"""
Chat router — POST /api/v1/chat

Streams an SSE response.  Each event is a JSON string:
  data: {"token": "some text"}     ← during streaming
  data: {"done": true, "citations": [...]}  ← final frame

Modes:
  knx       — query NotebookLM directly
  user      — query user-uploaded document via OpenAI
  combined  — NotebookLM answer + user doc context merged by OpenAI
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services import notebooklm_service, openai_service
from backend.session.manager import load_session

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    mode: str = "knx"           # "knx" | "user" | "combined"
    session_id: str | None = None
    history: list[dict] | None = None  # [{role, content}, ...]


@router.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    mode = req.mode.lower()
    if mode not in ("knx", "user", "combined"):
        raise HTTPException(status_code=400, detail="Mode must be 'knx', 'user', or 'combined'.")

    # Load user-doc session if needed
    session = None
    if mode in ("user", "combined") and req.session_id:
        session = load_session(req.session_id)

    return StreamingResponse(
        _stream(req.message, mode, session, req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream(message: str, mode: str, session: dict | None, history: list[dict] | None = None):
    """Yield SSE events."""

    def event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        if mode == "knx":
            # Query NotebookLM — not a true streaming API, yield answer in chunks
            result = await notebooklm_service.query(message, history=history)
            answer = result["answer"]
            citations = result["citations"]
            # Simulate streaming by chunking the answer
            words = answer.split(" ")
            for i in range(0, len(words), 8):
                chunk = " ".join(words[i:i + 8])
                if i + 8 < len(words):
                    chunk += " "
                yield event({"token": chunk})
            yield event({"done": True, "citations": citations,
                         "quota_warning": result.get("quota_warning", False),
                         "quota_remaining": result.get("quota_remaining", 0)})

        elif mode == "user":
            if not session:
                yield event({"token": "⚠️ No document uploaded. Please upload a PDF or Excel file first."})
                yield event({"done": True, "citations": []})
                return
            async for token in openai_service.stream_query_document(
                message, session["text"], session["filename"], history=history
            ):
                yield event({"token": token})
            yield event({"done": True, "citations": []})

        elif mode == "combined":
            # Step 1: get NotebookLM answer (no streaming)
            nlm_result = await notebooklm_service.query(message, history=history)
            nlm_answer = nlm_result["answer"]
            nlm_citations = nlm_result["citations"]

            if session:
                # Step 2: stream OpenAI combined answer
                async for token in openai_service.stream_combined(
                    message, nlm_answer, session["text"], session["filename"], history=history
                ):
                    yield event({"token": token})
                yield event({"done": True, "citations": nlm_citations,
                             "quota_warning": nlm_result.get("quota_warning", False),
                             "quota_remaining": nlm_result.get("quota_remaining", 0)})
            else:
                # No user doc — fall back to plain KNX answer
                words = nlm_answer.split(" ")
                for i in range(0, len(words), 8):
                    chunk = " ".join(words[i:i + 8])
                    if i + 8 < len(words):
                        chunk += " "
                    yield event({"token": chunk})
                yield event({"done": True, "citations": nlm_citations,
                             "quota_warning": nlm_result.get("quota_warning", False),
                             "quota_remaining": nlm_result.get("quota_remaining", 0)})

    except Exception as exc:
        logger.error(f"Chat stream error: {exc}")
        yield event({"token": "⚠️ An unexpected error occurred. Please try again."})
        yield event({"done": True, "citations": []})
