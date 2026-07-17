from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from core.printing.models import PdfDocumentInfo


class PyPdfDocumentInspector:
    """pypdf를 사용해 업로드 PDF의 구조를 읽는 어댑터다."""

    def inspect(self, pdf_path: Path) -> PdfDocumentInfo:
        """PDF 페이지 수를 확인하고 빈 문서는 명시적으로 거부한다."""

        with pdf_path.open("rb") as pdf_file:
            page_count = len(PdfReader(pdf_file).pages)

        if page_count < 1:
            raise ValueError("The uploaded PDF must contain at least one page.")
        return PdfDocumentInfo(page_count=page_count)
