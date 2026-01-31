from __future__ import annotations

from fastapi import Request

from core.app_ads import AppAdsContentService
from core.printers import PrintJobService
from core.ssv import AdmobSsvVerifier


def get_print_service(request: Request) -> PrintJobService:
    """애플리케이션 상태에 등록된 PrintJobService를 반환한다."""

    return request.app.state.print_service


def get_ssv_verifier(request: Request) -> AdmobSsvVerifier:
    """애플리케이션 상태에 등록된 AdmobSsvVerifier를 반환한다."""

    return request.app.state.ssv_verifier


def get_app_ads_service(request: Request) -> AppAdsContentService:
    """애플리케이션 상태에 등록된 AppAdsContentService를 반환한다."""

    return request.app.state.app_ads_service
