from __future__ import annotations

from fastapi import Request

from core.printers import PrintJobService
from core.ssv import AdmobSsvVerifier


def get_print_service(request: Request) -> PrintJobService:
    """앱 상태에 등록된 PrintJobService를 반환한다."""

    return request.app.state.print_service


def get_ssv_verifier(request: Request) -> AdmobSsvVerifier:
    """앱 상태에 등록된 AdmobSsvVerifier를 반환한다."""

    return request.app.state.ssv_verifier
