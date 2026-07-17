from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from core.dependencies import get_print_service
from core.printers import PrintJobService
from core.printing.errors import InvalidPrintDocumentError, PrintApplicationError
from core.printing.models import DuplexMode

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload_file/")
async def receive_file(
    phone_number: str = Form(...),
    is_a3: Optional[str] = Form(None),
    duplex_mode: Optional[str] = Form(None),
    file: UploadFile = File(...),
    print_service: PrintJobService = Depends(get_print_service),
):
    """업로드된 PDF 파일을 처리하고 결과를 반환한다."""

    try:
        parsed_is_a3 = _parse_optional_boolean(is_a3, "is_a3")
        parsed_duplex_mode = DuplexMode.from_api_value(duplex_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        result = await run_in_threadpool(
            print_service.process_upload,
            file,
            phone_number,
            parsed_is_a3,
            parsed_duplex_mode,
        )
    except InvalidPrintDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrintApplicationError as exc:
        logger.exception("Print job application failure")
        raise HTTPException(
            status_code=500,
            detail="Print job failed. Check the server log for the failing stage.",
        ) from exc
    return {"phone_number": result.phone_number, "file_name": result.file_name}


def _parse_optional_boolean(value: str | None, field_name: str) -> bool:
    """선택 불리언 폼 값을 조용한 fallback 없이 명시적으로 검증한다."""

    normalized_value = (value or "false").strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field_name} must be true or false; received '{value}'.")
