"""
Upload router — POST /api/v1/upload

Accepts a PDF or Excel file (max 20 MB).
Extracts text, creates a session, returns session metadata.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.config import settings
from backend.services import pdf_service, excel_service
from backend.session.manager import create_session

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    "application/vnd.ms-excel": "excel",
}
_ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls"}
_MAX_BYTES = settings.max_upload_mb * 1024 * 1024


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Use PDF or Excel.")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {settings.max_upload_mb} MB).")

    try:
        if ext == ".pdf":
            text, count = pdf_service.extract_text(data)
            meta = {"type": "pdf", "page_count": count}
        else:
            text, count = excel_service.extract_text(data)
            meta = {"type": "excel", "sheet_count": count}
    except Exception as exc:
        logger.error(f"File extraction error: {exc}")
        raise HTTPException(status_code=422, detail="Could not read the file. Ensure it is not corrupted.")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in the file.")

    session_id = create_session(file.filename or "document", text, meta)

    return {
        "session_id": session_id,
        "filename": file.filename,
        **meta,
        "char_count": len(text),
    }
