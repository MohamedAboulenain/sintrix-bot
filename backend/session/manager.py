from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from backend.config import settings

_TTL_SECONDS = 86_400  # 24 hours


def _session_path(session_id: str) -> Path:
    return Path(settings.sessions_dir) / f"{session_id}.json"


def create_session(filename: str, text: str, meta: dict) -> str:
    session_id = str(uuid.uuid4())
    data = {
        "session_id": session_id,
        "filename": filename,
        "text": text,
        "meta": meta,
        "created_at": time.time(),
    }
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return session_id


def load_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if time.time() - data["created_at"] > _TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    return data


def cleanup_expired_sessions() -> int:
    removed = 0
    sessions_dir = Path(settings.sessions_dir)
    if not sessions_dir.exists():
        return 0
    for f in sessions_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if time.time() - data.get("created_at", 0) > _TTL_SECONDS:
                f.unlink(missing_ok=True)
                removed += 1
        except Exception:
            f.unlink(missing_ok=True)
            removed += 1
    return removed
