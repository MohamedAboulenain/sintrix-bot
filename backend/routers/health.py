from fastapi import APIRouter
from backend.services import notebooklm_service

router = APIRouter()


@router.get("/health")
async def health():
    nlm = notebooklm_service.get_status()
    return {
        "status": "ok",
        "notebooklm": nlm["available"],
        "quota_remaining": nlm["quota_remaining"],
        "quota_limit": nlm["quota_limit"],
    }
