from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from core.config import PrintConfig
from core.printers import PrintJobService
from core.printing.errors import (
    InvalidPrintDocumentError,
    PrintConversionFailedError,
    PrintDataUploadError,
)
from core.printing.files import LocalJobFileStore
from core.printing.models import DuplexMode, PaperSize, PdfDocumentInfo


class FakePdfInspector:
    """PDF 라이브러리 없이 서비스 흐름만 검증하는 테스트 대역이다."""

    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    def inspect(self, pdf_path: Path) -> PdfDocumentInfo:
        if self.failure is not None:
            raise self.failure
        return PdfDocumentInfo(page_count=3)


class FakePrintConverter:
    """CUPS 없이 선택 용지와 양면 모드를 기록하고 PRN을 만든다."""

    def __init__(self, output_dir: Path, failure: Exception | None = None) -> None:
        self.output_dir = output_dir
        self.failure = failure
        self.calls: list[tuple[str, Path, PaperSize, DuplexMode]] = []

    def convert(
        self,
        job_id: str,
        pdf_path: Path,
        paper_size: PaperSize,
        duplex_mode: DuplexMode,
    ) -> Path:
        self.calls.append((job_id, pdf_path, paper_size, duplex_mode))
        if self.failure is not None:
            raise self.failure
        output_path = self.output_dir / f"{job_id}.prn"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"synthetic-prn")
        return output_path


class FakePrintServerGateway:
    """외부 네트워크 없이 업로드와 등록 인수를 기록한다."""

    def __init__(self, upload_failure: Exception | None = None) -> None:
        self.upload_failure = upload_failure
        self.uploads: list[Path] = []
        self.registrations: list[tuple[str, str, str, int, PaperSize]] = []

    def upload_print_file(self, prn_path: Path) -> dict:
        self.uploads.append(prn_path)
        if self.upload_failure is not None:
            raise self.upload_failure
        return {"uploaded": True}

    def register_document(
        self,
        job_id: str,
        document_name: str,
        phone_number: str,
        page_count: int,
        paper_size: PaperSize,
    ) -> dict:
        self.registrations.append(
            (job_id, document_name, phone_number, page_count, paper_size)
        )
        return {"registered": True}


class PrintJobServiceTest(unittest.TestCase):
    """매체 정책, 외부 포트 인수, 성공/실패 파일 수명주기를 검증한다."""

    def test_a3_request_uses_a3_for_cups_and_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = PrintConfig(
                temp_dir=root / "input",
                output_dir=root / "output",
                retain_job_files=False,
            )
            converter = FakePrintConverter(config.output_dir)
            gateway = FakePrintServerGateway()
            service = PrintJobService(
                config=config,
                pdf_inspector=FakePdfInspector(),
                print_converter=converter,
                file_store=LocalJobFileStore(config),
                server_gateway=gateway,
            )
            upload = SimpleNamespace(
                filename="synthetic-a3.pdf", file=BytesIO(b"%PDF-synthetic")
            )

            result = service.process_upload(
                upload,
                "01000000000",
                is_a3=True,
                duplex_mode=DuplexMode.LONG_EDGE,
            )

            self.assertIs(converter.calls[0][2], PaperSize.A3)
            self.assertIs(result.paper_size, PaperSize.A3)
            self.assertIs(gateway.registrations[0][4], PaperSize.A3)
            self.assertEqual(gateway.registrations[0][3], 3)
            self.assertFalse(any(config.temp_dir.glob("*.pdf")))
            self.assertFalse(any(config.output_dir.glob("*.prn")))

    def test_gateway_failure_still_removes_job_files_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = PrintConfig(
                temp_dir=root / "input",
                output_dir=root / "output",
                retain_job_files=False,
            )
            converter = FakePrintConverter(config.output_dir)
            gateway = FakePrintServerGateway(
                PrintDataUploadError("synthetic network failure")
            )
            service = PrintJobService(
                config=config,
                pdf_inspector=FakePdfInspector(),
                print_converter=converter,
                file_store=LocalJobFileStore(config),
                server_gateway=gateway,
            )
            upload = SimpleNamespace(
                filename="synthetic.pdf", file=BytesIO(b"%PDF-synthetic")
            )

            with self.assertRaises(PrintDataUploadError):
                service.process_upload(upload, "01000000000", is_a3=False)

            self.assertFalse(any(config.temp_dir.glob("*.pdf")))
            self.assertFalse(any(config.output_dir.glob("*.prn")))

    def test_converter_failure_is_mapped_and_job_files_are_removed(self) -> None:
        """인프라 변환 오류는 애플리케이션 오류가 되고 작업 파일을 남기지 않는다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = PrintConfig(
                temp_dir=root / "input",
                output_dir=root / "output",
                retain_job_files=False,
            )
            gateway = FakePrintServerGateway()
            service = PrintJobService(
                config=config,
                pdf_inspector=FakePdfInspector(),
                print_converter=FakePrintConverter(
                    config.output_dir,
                    RuntimeError("synthetic CUPS failure"),
                ),
                file_store=LocalJobFileStore(config),
                server_gateway=gateway,
            )
            upload = SimpleNamespace(
                filename="synthetic.pdf", file=BytesIO(b"%PDF-synthetic")
            )

            with self.assertRaisesRegex(
                PrintConversionFailedError,
                "synthetic CUPS failure",
            ):
                service.process_upload(upload, "01000000000", is_a3=False)

            self.assertFalse(gateway.uploads)
            self.assertFalse(any(config.temp_dir.glob("*.pdf")))
            self.assertFalse(any(config.output_dir.glob("*.prn")))

    def test_unreadable_pdf_is_a_client_error_and_partial_files_are_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = PrintConfig(
                temp_dir=root / "input",
                output_dir=root / "output",
                retain_job_files=False,
            )
            service = PrintJobService(
                config=config,
                pdf_inspector=FakePdfInspector(ValueError("broken PDF")),
                print_converter=FakePrintConverter(config.output_dir),
                file_store=LocalJobFileStore(config),
                server_gateway=FakePrintServerGateway(),
            )
            upload = SimpleNamespace(filename=None, file=BytesIO(b"not-a-pdf"))

            with self.assertRaisesRegex(InvalidPrintDocumentError, "readable PDF"):
                service.process_upload(upload, "01000000000", is_a3=False)

            self.assertFalse(any(config.temp_dir.glob("*.pdf")))


if __name__ == "__main__":
    unittest.main()
