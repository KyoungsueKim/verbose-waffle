from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, Protocol

from core.printing.models import DuplexMode, PaperSize, PdfDocumentInfo


class PdfDocumentInspector(Protocol):
    """애플리케이션 계층이 PDF 라이브러리에 의존하지 않게 하는 포트다."""

    def inspect(self, pdf_path: Path) -> PdfDocumentInfo:
        """PDF를 읽어 출력에 필요한 메타데이터를 반환한다."""


class UploadedDocument(Protocol):
    """FastAPI 타입 없이 업로드 파일의 최소 계약만 표현한다."""

    filename: str | None
    file: BinaryIO


class PrintFileConverter(Protocol):
    """애플리케이션 계층과 CUPS 변환 구현을 분리하는 포트다."""

    def convert(
        self,
        job_id: str,
        pdf_path: Path,
        paper_size: PaperSize,
        duplex_mode: DuplexMode,
    ) -> Path:
        """PDF를 프린터가 이해하는 PRN 파일로 변환한다."""


class JobFileStore(Protocol):
    """출력 유즈케이스가 로컬 경로 구현에 의존하지 않게 하는 포트다."""

    def save_upload(self, job_id: str, source: BinaryIO) -> Path:
        """업로드 스트림을 작업별 PDF로 저장한다."""

    def cleanup(self, job_id: str) -> None:
        """해당 작업이 만든 로컬 파일만 정리한다."""


class PrintServerGateway(Protocol):
    """애플리케이션 계층과 원격 Canon 서버 연동을 분리하는 포트다."""

    def upload_print_file(self, prn_path: Path) -> dict[str, Any] | None:
        """생성된 PRN 파일을 원격 바이너리 서버에 업로드한다."""

    def register_document(
        self,
        job_id: str,
        document_name: str,
        phone_number: str,
        page_count: int,
        paper_size: PaperSize,
    ) -> dict[str, Any] | None:
        """원격 서버에 출력 문서 메타데이터를 등록한다."""
