from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from core import html_content

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """개인정보 처리방침 HTML을 반환한다."""

    return HTMLResponse(content=html_content.html_content, status_code=200)
