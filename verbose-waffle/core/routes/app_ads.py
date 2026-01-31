from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from core.app_ads import AppAdsContentService
from core.dependencies import get_app_ads_service

router = APIRouter()


@router.get("/app-ads.txt", response_class=PlainTextResponse, include_in_schema=False)
async def app_ads_txt(
    service: AppAdsContentService = Depends(get_app_ads_service),
) -> PlainTextResponse:
    """AdMob app-ads.txt를 제공하기 위한 엔드포인트."""

    return PlainTextResponse(content=service.render(), status_code=200)
