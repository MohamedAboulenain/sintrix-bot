"""
Generate router

  POST /api/v1/generate/pdf    → returns PDF file download
  POST /api/v1/generate/excel  → returns Excel file download
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.services import openai_service, pdf_service, excel_service
from backend.services.openai_service import generate_excel_content
from backend.session.manager import load_session

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    session_id: str | None = None


def _safe_filename(text: str, ext: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text[:40]).strip().lower()
    slug = re.sub(r"[\s-]+", "_", slug) or "sintrix_knx"
    return f"{slug}.{ext}"


@router.post("/generate/pdf")
async def generate_pdf(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    doc_text = None
    if req.session_id:
        session = load_session(req.session_id)
        if session:
            doc_text = session["text"]

    try:
        content = await openai_service.generate_content(req.prompt, doc_text)
        title = _extract_title(req.prompt)
        pdf_bytes = pdf_service.generate_pdf(title, content)
    except Exception as exc:
        logger.error(f"PDF generation error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")

    filename = _safe_filename(req.prompt, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate/excel")
async def generate_excel(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    doc_text = None
    if req.session_id:
        session = load_session(req.session_id)
        if session:
            doc_text = session["text"]

    try:
        content = await generate_excel_content(req.prompt, doc_text)
        title = _extract_title(req.prompt)
        excel_bytes = excel_service.generate_excel(title, content)
    except Exception as exc:
        logger.error(f"Excel generation error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate Excel file.")

    filename = _safe_filename(req.prompt, "xlsx")
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _extract_title(prompt: str) -> str:
    words = prompt.strip().split()[:8]
    return " ".join(words).title()
