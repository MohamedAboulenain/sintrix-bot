"""
OpenAI service — GPT-4o for:
  - User-document Q&A (query a user-uploaded PDF/Excel by embedding text as context)
  - Combined mode (merge NotebookLM answer with user-doc context)
  - PDF/Excel content generation
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI

from backend.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


_SYSTEM_KNX = (
    "You are Sintrix KNX Bot, an expert in KNX building automation. "
    "Answer concisely and accurately using the provided document context. "
    "If the document doesn't contain the answer, say so clearly. "
    "Format responses with markdown where helpful (headings, lists, code blocks)."
)

_SYSTEM_GENERATE = (
    "You are Sintrix KNX Bot, an expert in KNX building automation. "
    "Generate structured, professional content based on the user's request. "
    "Use clear sections, tables, and bullet points where appropriate."
)

_SYSTEM_GENERATE_EXCEL = (
    "You are Sintrix KNX Bot, an expert in KNX building automation. "
    "Your task is to produce data for an Excel spreadsheet. "
    "Respond with ONLY a valid JSON array of objects — no explanation, no markdown, no code fences, no extra text. "
    "Each object is one row. Keys become column headers. "
    "Example: [{\"Type\": \"Main Group\", \"Range\": \"0–31\", \"Description\": \"Top-level grouping\"}]"
)


async def generate_content(prompt: str, doc_text: str | None = None) -> str:
    """Generate structured text content for PDF creation."""
    client = _get_client()
    context = f"\nUser document context:\n{doc_text[:6_000]}" if doc_text else ""
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_GENERATE},
            {"role": "user", "content": f"{prompt}{context}"},
        ],
        stream=False,
        max_tokens=3000,
    )
    return response.choices[0].message.content or ""


async def generate_excel_content(prompt: str, doc_text: str | None = None) -> str:
    """Generate JSON-structured data for Excel creation. Returns a raw JSON array string."""
    client = _get_client()
    context = f"\n\nUser document context (use it if relevant):\n{doc_text[:6_000]}" if doc_text else ""
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_GENERATE_EXCEL},
            {"role": "user", "content": f"{prompt}{context}"},
        ],
        stream=False,
        max_tokens=3000,
    )
    return response.choices[0].message.content or ""


async def stream_query_document(message: str, doc_text: str, filename: str, history: list[dict] | None = None):
    """Async generator yielding text tokens for streaming."""
    client = _get_client()
    context = f"Document: {filename}\n\n{doc_text[:12_000]}"
    history_msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-10:]]
    async with await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_KNX},
            *history_msgs,
            {"role": "user", "content": f"Document context:\n{context}\n\nQuestion: {message}"},
        ],
        stream=True,
        max_tokens=1500,
    ) as stream:
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


async def stream_combined(message: str, nlm_answer: str, doc_text: str, filename: str, history: list[dict] | None = None):
    """Async generator for combined-mode streaming."""
    client = _get_client()
    doc_snippet = doc_text[:6_000]
    prompt = (
        f"KNX specification answer:\n{nlm_answer}\n\n"
        f"User document ({filename}):\n{doc_snippet}\n\n"
        f"Question: {message}\n\n"
        "Combine the above sources into a single comprehensive answer."
    )
    history_msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-10:]]
    async with await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_KNX},
            *history_msgs,
            {"role": "user", "content": prompt},
        ],
        stream=True,
        max_tokens=2000,
    ) as stream:
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
