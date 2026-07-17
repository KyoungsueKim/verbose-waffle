from __future__ import annotations

import logging
from uuid import uuid4

from core.config import PrintConfig
from core.printing.errors import (
    InvalidPrintDocumentError,
    PrintConversionFailedError,
    PrintFileStorageError,
)
from core.printing.models import DuplexMode, PaperSize, PrintJobResult
from core.printing.ports import (
    JobFileStore,
    PdfDocumentInspector,
    PrintFileConverter,
    PrintServerGateway,
    UploadedDocument,
)

logger = logging.getLogger(__name__)


class PrintJobService:
    """PDF 저장, 검사, 변환, 전송, 등록의 유즈케이스 순서만 조정한다."""

    def __init__(
        self,
        config: PrintConfig,
        pdf_inspector: PdfDocumentInspector,
        print_converter: PrintFileConverter,
        file_store: JobFileStore,
        server_gateway: PrintServerGateway,
    ) -> None:
        self._config = config
        self._pdf_inspector = pdf_inspector
        self._print_converter = print_converter
        self._file_store = file_store
        self._server_gateway = server_gateway

    def process_upload(
        self,
        upload_file: UploadedDocument,
        phone_number: str,
        is_a3: bool,
        duplex_mode: DuplexMode | None = None,
    ) -> PrintJobResult:
        """업로드 PDF를 선택 용지에 맞춘 PRN으로 변환하고 등록한다."""

        effective_duplex_mode = duplex_mode or DuplexMode.SIMPLEX
        paper_size = PaperSize.from_is_a3(is_a3)
        job_id = str(uuid4()).upper()
        document_name = upload_file.filename or f"{job_id}.pdf"
        data_result: dict | None = None
        register_result: dict | None = None

        try:
            try:
                pdf_path = self._file_store.save_upload(job_id, upload_file.file)
            except Exception as exc:  # noqa: BLE001 - 저장 구현의 오류를 유즈케이스 오류로 변환한다.
                raise PrintFileStorageError(
                    f"Failed to save uploaded PDF for job '{job_id}': {exc}"
                ) from exc

            try:
                document_info = self._pdf_inspector.inspect(pdf_path)
            except Exception as exc:  # noqa: BLE001 - PDF 라이브러리 오류를 API 오류로 변환한다.
                raise InvalidPrintDocumentError(
                    f"Uploaded file is not a readable PDF for job '{job_id}': {exc}"
                ) from exc

            try:
                prn_path = self._print_converter.convert(
                    job_id,
                    pdf_path,
                    paper_size,
                    effective_duplex_mode,
                )
            except Exception as exc:  # noqa: BLE001 - 변환 어댑터 오류를 유즈케이스 오류로 통일한다.
                raise PrintConversionFailedError(
                    f"Print conversion failed for job '{job_id}': {exc}"
                ) from exc

            data_result = self._server_gateway.upload_print_file(prn_path)
            register_result = self._server_gateway.register_document(
                job_id,
                document_name,
                phone_number,
                document_info.page_count,
                paper_size,
            )
        finally:
            if not self._config.retain_job_files:
                try:
                    self._file_store.cleanup(job_id)
                except Exception:  # noqa: BLE001 - 원래 작업 결과를 보존하고 로그로 경고한다.
                    logger.exception("Failed to clean local files for print job %s", job_id)

        logger.info(
            "Print job completed: %s",
            {
                "job_id": job_id,
                "page_count": document_info.page_count,
                "paper_size": paper_size.value,
                "print_scaling": self._config.cups_scaling.value,
                "duplex_mode": effective_duplex_mode.value,
                "data_result": data_result,
                "register_result": register_result,
            },
        )

        return PrintJobResult(
            phone_number=phone_number,
            file_name=document_name,
            page_count=document_info.page_count,
            is_a3=is_a3,
            duplex_mode=effective_duplex_mode,
            paper_size=paper_size,
            print_scaling=self._config.cups_scaling,
        )
