from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from core.printing.pdf import PyPdfDocumentInspector
from tests.support.pdf_factory import A4_PORTRAIT, write_duplex_test_pdf


class PyPdfDocumentInspectorTest(unittest.TestCase):
    """실사용 문서를 열지 않고 합성 PDF 메타데이터 판독을 검증한다."""

    def test_counts_synthetic_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "two-pages.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=595.3, height=841.9)
            writer.add_blank_page(width=841.9, height=1190.5)
            with pdf_path.open("wb") as pdf_file:
                writer.write(pdf_file)

            info = PyPdfDocumentInspector().inspect(pdf_path)

            self.assertEqual(info.page_count, 2)

    def test_rejects_pdf_without_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "empty.pdf"
            with pdf_path.open("wb") as pdf_file:
                PdfWriter().write(pdf_file)

            with self.assertRaisesRegex(ValueError, "at least one page"):
                PyPdfDocumentInspector().inspect(pdf_path)


class SyntheticPrintFixtureTest(unittest.TestCase):
    """실물 양면 인수용 합성 문서의 페이지 계약을 검증한다."""

    def test_duplex_fixture_has_two_a4_pages(self) -> None:
        """양면 시험 문서는 안전 여백 표식이 있는 A4 두 쪽이어야 한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_duplex_test_pdf(Path(temp_dir) / "duplex-a4-safe.pdf")

            reader = PdfReader(pdf_path)

            self.assertEqual(len(reader.pages), 2)
            for page in reader.pages:
                self.assertAlmostEqual(float(page.mediabox.width), A4_PORTRAIT[0])
                self.assertAlmostEqual(float(page.mediabox.height), A4_PORTRAIT[1])


if __name__ == "__main__":
    unittest.main()
