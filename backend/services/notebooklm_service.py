"""
NotebookLM service — wraps notebooklm-py for async queries.

Manages:
- One-time auth loading at startup (from ~/.notebooklm/storage_state.json)
- Daily quota tracking (resets midnight UTC)
- Graceful degradation when unavailable
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.config import settings

logger = logging.getLogger(__name__)

_auth = None
_available: bool = False
_query_count: int = 0
_quota_date: str = ""  # "YYYY-MM-DD"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _reset_quota_if_new_day() -> None:
    global _query_count, _quota_date
    today = _today()
    if _quota_date != today:
        _query_count = 0
        _quota_date = today


async def initialize() -> None:
    global _auth, _available
    notebook_id = settings.notebooklm_notebook_id
    if not notebook_id:
        logger.warning("NOTEBOOKLM_NOTEBOOK_ID not set — NotebookLM disabled.")
        return
    try:
        from notebooklm.auth import AuthTokens
        _auth = await AuthTokens.from_storage()
        _available = True
        logger.info("NotebookLM auth loaded successfully.")
    except FileNotFoundError:
        logger.warning(
            "No saved NotebookLM session found. "
            "Run `notebooklm login` once to authenticate."
        )
    except ImportError:
        logger.warning("notebooklm-py not installed — NotebookLM disabled.")
    except Exception as exc:
        logger.error(f"NotebookLM init failed: {exc}")


def get_status() -> dict:
    _reset_quota_if_new_day()
    remaining = max(0, settings.nlm_daily_quota - _query_count)
    return {
        "available": _available,
        "quota_used": _query_count,
        "quota_limit": settings.nlm_daily_quota,
        "quota_remaining": remaining,
        "quota_warning": _query_count >= settings.nlm_quota_warning_threshold,
        "quota_exhausted": remaining == 0,
    }


async def query(message: str, history: list[dict] | None = None) -> dict:
    """Query the NotebookLM notebook and return answer + citations."""
    global _query_count, _available

    _reset_quota_if_new_day()
    status = get_status()

    if status["quota_exhausted"]:
        return _unavailable_response("Daily query limit reached. Please try again tomorrow.")

    if not _available or _auth is None:
        return _unavailable_response(
            "The KNX knowledge base is currently unavailable. "
            "Please ensure `notebooklm login` has been run."
        )

    # Prepend the last 3 exchanges as plain-text context so NotebookLM
    # can resolve follow-up references even without native multi-turn support.
    if history:
        ctx = "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content'][:300]}"
            for h in history[-6:]
        )
        message = f"[Conversation so far:\n{ctx}\n]\n\n{message}"

    try:
        from notebooklm import NotebookLMClient
        logger.info(f"Querying notebook ID: {settings.notebooklm_notebook_id!r}")
        async with NotebookLMClient(_auth) as client:
            result = await client.chat.ask(settings.notebooklm_notebook_id, message)

        _query_count += 1
        answer_preview = (result.answer or "")[:120].replace("\n", " ")
        logger.info(f"NotebookLM response ({len(result.answer or '')} chars): {answer_preview!r}…")
        citations = _extract_citations(result)

        return {
            "answer": result.answer or "",
            "citations": citations,
            "quota_warning": get_status()["quota_warning"],
            "quota_remaining": get_status()["quota_remaining"],
        }

    except Exception as exc:
        err = str(exc).lower()
        if any(kw in err for kw in ("401", "auth", "cookie", "session", "login")):
            _available = False
            logger.error(f"NotebookLM auth expired: {exc}")
            return _unavailable_response(
                "KNX knowledge base session expired. "
                "Please re-run `notebooklm login` on the server."
            )
        logger.error(f"NotebookLM query error: {exc}")
        return _unavailable_response("An error occurred querying the KNX knowledge base.")


def _extract_citations(result) -> list[dict]:
    if not result or not result.references:
        return []
    seen: set[int] = set()
    citations: list[dict] = []
    for ref in result.references:
        num = getattr(ref, "citation_number", None)
        if num in seen:
            continue
        seen.add(num)
        citations.append({
            "number": num,
            "source": getattr(ref, "source_title", "") or "",
            "excerpt": (getattr(ref, "cited_text", "") or "")[:300],
        })
        if len(citations) >= 10:
            break
    return citations


def _unavailable_response(reason: str) -> dict:
    return {
        "answer": f"⚠️ {reason}",
        "citations": [],
        "quota_warning": False,
        "quota_remaining": get_status()["quota_remaining"],
    }
