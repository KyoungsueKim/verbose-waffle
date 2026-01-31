from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from core.dependencies import get_print_service
from core.printers import PrintJobService

router = APIRouter()


@router.post("/upload_file/")
async def receive_file(
    phone_number: str = Form(...),
    is_a3: Optional[str] = Form(None),
    file: UploadFile = File(...),
    print_service: PrintJobService = Depends(get_print_service),
):
    """업로드된 PDF 파일을 처리하고 결과를 반환한다."""

    parsed_is_a3 = (is_a3 or "").lower() == "true"
    result = await run_in_threadpool(print_service.process_upload, file, phone_number, parsed_is_a3)
    return {"phone_number": result.phone_number, "file_name": result.file_name}
