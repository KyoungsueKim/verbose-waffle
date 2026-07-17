from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from core.config import PrintConfig
from core.printing.cups import CupsPrintFileConverter
from core.printing.models import DuplexMode, PaperSize
from tests.support.pdf_factory import (
    A3_PORTRAIT,
    A4_PORTRAIT,
    A5_PORTRAIT,
    write_marked_pdf,
)

CANON_PPD = Path("/usr/share/cups/model/CNRCUPSIRADV45453ZK.ppd")
PDFTOPDF_FILTER = Path("/usr/lib/cups/filter/pdftopdf")
PDFTOPPM = Path("/usr/bin/pdftoppm")
MEDIA_BOX_TOLERANCE_POINTS = 0.2
MINIMUM_RENDERED_MARGIN_PIXELS = 1
MINIMUM_OVERSIZED_MARGIN_PIXELS = 12

ColorMatcher = Callable[[int, int, int], bool]
COLOR_MATCHERS: dict[str, ColorMatcher] = {
    "red": lambda red, green, blue: red >= 200 and green <= 80 and blue <= 80,
    "green": lambda red, green, blue: red <= 80 and green >= 200 and blue <= 80,
    "blue": lambda red, green, blue: red <= 80 and green <= 80 and blue >= 200,
    "magenta": lambda red, green, blue: red >= 200 and green <= 80 and blue >= 200,
}


class PpmImage:
    """Pillow 없이 PPM P6 렌더의 크기와 RGB 픽셀을 보관한다."""

    def __init__(self, width: int, height: int, pixels: bytes) -> None:
        self.width = width
        self.height = height
        self.pixels = pixels


def _read_ppm_p6(ppm_path: Path) -> PpmImage:
    """Poppler가 만든 PPM P6 헤더와 8비트 RGB 픽셀을 파싱한다."""

    data = ppm_path.read_bytes()
    tokens: list[bytes] = []
    offset = 0
    while len(tokens) < 4:
        while offset < len(data) and data[offset] in b" \t\r\n":
            offset += 1
        if offset < len(data) and data[offset] == ord("#"):
            newline = data.find(b"\n", offset)
            if newline < 0:
                raise AssertionError(f"PPM comment is not terminated: {ppm_path}")
            offset = newline + 1
            continue

        token_start = offset
        while offset < len(data) and data[offset] not in b" \t\r\n#":
            offset += 1
        if token_start == offset:
            raise AssertionError(f"PPM header is incomplete: {ppm_path}")
        tokens.append(data[token_start:offset])

    magic, raw_width, raw_height, raw_max_value = tokens
    if magic != b"P6":
        raise AssertionError(f"Expected PPM P6, received {magic!r}: {ppm_path}")
    if raw_max_value != b"255":
        raise AssertionError(f"Expected 8-bit PPM, received max value {raw_max_value!r}: {ppm_path}")

    if data[offset:offset + 2] == b"\r\n":
        offset += 2
    elif offset < len(data) and data[offset] in b" \t\r\n":
        offset += 1
    else:
        raise AssertionError(f"PPM pixel separator is missing: {ppm_path}")

    width = int(raw_width)
    height = int(raw_height)
    pixels = data[offset:]
    expected_length = width * height * 3
    if len(pixels) != expected_length:
        raise AssertionError(
            f"PPM pixel length mismatch: expected {expected_length}, "
            f"received {len(pixels)}: {ppm_path}"
        )
    return PpmImage(width=width, height=height, pixels=pixels)


def _find_color_bounds(
    image: PpmImage,
    matcher: ColorMatcher,
) -> tuple[int, int, int, int] | None:
    """조건에 맞는 색 픽셀의 left, top, right, bottom 경계를 찾는다."""

    left = image.width
    top = image.height
    right = -1
    bottom = -1
    for pixel_index in range(0, len(image.pixels), 3):
        red, green, blue = image.pixels[pixel_index:pixel_index + 3]
        if not matcher(red, green, blue):
            continue
        position = pixel_index // 3
        x = position % image.width
        y = position // image.width
        left = min(left, x)
        top = min(top, y)
        right = max(right, x)
        bottom = max(bottom, y)

    if right < 0:
        return None
    return left, top, right, bottom


@unittest.skipUnless(
    os.environ.get("RUN_CUPS_INTEGRATION") == "1",
    "RUN_CUPS_INTEGRATION=1인 Linux CUPS 컨테이너에서만 실행한다.",
)
class CupsIntegrationTest(unittest.TestCase):
    """실제 Canon PPD와 CUPS 필터 체인이 PRN을 만드는지 검증한다."""

    @classmethod
    def setUpClass(cls) -> None:
        """통합 테스트가 운영 이미지의 실제 필터와 PPD를 사용하는지 확인한다."""

        super().setUpClass()
        required_paths = (CANON_PPD, PDFTOPDF_FILTER, PDFTOPPM)
        missing_paths = [str(path) for path in required_paths if not path.is_file()]
        if missing_paths:
            raise AssertionError(
                "CUPS integration image is missing required files: " + ", ".join(missing_paths)
            )

    def test_pdftopdf_auto_fit_preserves_a4_pages_and_corner_markers(self) -> None:
        """A4 자동 맞춤이 여러 원본 크기의 페이지와 네 색 모서리를 보존하는지 검증한다."""

        fixture_cases = (
            ("a3-portrait", (A3_PORTRAIT,)),
            ("a3-landscape", ((A3_PORTRAIT[1], A3_PORTRAIT[0]),)),
            ("exact-a4", (A4_PORTRAIT,)),
            ("a5-portrait", (A5_PORTRAIT,)),
            ("mixed-a3-a4-a5", (A3_PORTRAIT, A4_PORTRAIT, A5_PORTRAIT)),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for fixture_name, page_sizes in fixture_cases:
                with self.subTest(fixture=fixture_name):
                    input_path = write_marked_pdf(
                        root / f"{fixture_name}-input.pdf",
                        page_sizes,
                    )
                    output_path = root / f"{fixture_name}-a4-auto-fit.pdf"
                    self._run_pdftopdf(input_path, output_path)

                    self._assert_all_pages_are_a4(output_path, expected_pages=len(page_sizes))
                    rendered_pages = self._render_to_ppm(
                        output_path,
                        root / f"{fixture_name}-page",
                    )
                    self.assertEqual(len(rendered_pages), len(page_sizes))
                    for page_number, (ppm_path, source_size) in enumerate(
                        zip(rendered_pages, page_sizes, strict=True),
                        start=1,
                    ):
                        with self.subTest(fixture=fixture_name, page=page_number):
                            source_is_oversized = (
                                max(source_size) > max(A4_PORTRAIT) + MEDIA_BOX_TOLERANCE_POINTS
                                or min(source_size)
                                > min(A4_PORTRAIT) + MEDIA_BOX_TOLERANCE_POINTS
                            )
                            minimum_margin = (
                                MINIMUM_OVERSIZED_MARGIN_PIXELS
                                if source_is_oversized
                                else MINIMUM_RENDERED_MARGIN_PIXELS
                            )
                            self._assert_corner_markers_have_internal_margins(
                                ppm_path,
                                minimum_margin,
                            )

    def test_a3_pdf_can_be_converted_with_a4_auto_fit_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = write_marked_pdf(root / "a3-portrait.pdf", [A3_PORTRAIT])
            config = PrintConfig(
                temp_dir=root,
                output_dir=root,
                retain_job_files=True,
            )
            job_id = f"FIT-{uuid4().hex[:12]}"

            prn_path = CupsPrintFileConverter(config).convert(
                job_id,
                pdf_path,
                PaperSize.A4,
                DuplexMode.SIMPLEX,
            )

            self.assertTrue(prn_path.is_file())
            self.assertGreater(prn_path.stat().st_size, 100)

    def _run_pdftopdf(self, input_path: Path, output_path: Path) -> None:
        """실제 Canon PPD를 지정해 pdftopdf 필터를 A4 auto-fit 옵션으로 실행한다."""

        filter_environment = os.environ.copy()
        filter_environment.update(
            {
                "CONTENT_TYPE": "application/pdf",
                "FINAL_CONTENT_TYPE": "application/vnd.cups-pdf",
                "PPD": str(CANON_PPD),
                "PRINTER": "canon-a4-auto-fit-test",
            }
        )
        command = [
            str(PDFTOPDF_FILTER),
            "1",
            "integration-test",
            input_path.name,
            "1",
            "media=A4 print-scaling=auto-fit",
            str(input_path),
        ]
        with output_path.open("wb") as output_file:
            completed = subprocess.run(
                command,
                check=False,
                stdout=output_file,
                stderr=subprocess.PIPE,
                env=filter_environment,
            )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        self.assertTrue(output_path.is_file())
        self.assertGreater(output_path.stat().st_size, 0)

    def _assert_all_pages_are_a4(self, pdf_path: Path, expected_pages: int) -> None:
        """변환 PDF가 페이지 수를 보존하고 모든 MediaBox를 A4로 만드는지 확인한다."""

        reader = PdfReader(pdf_path)
        self.assertEqual(len(reader.pages), expected_pages)
        expected_dimensions = sorted(A4_PORTRAIT)
        for page_number, page in enumerate(reader.pages, start=1):
            actual_dimensions = sorted(
                (
                    float(page.mediabox.width),
                    float(page.mediabox.height),
                )
            )
            for actual, expected in zip(actual_dimensions, expected_dimensions, strict=True):
                self.assertAlmostEqual(
                    actual,
                    expected,
                    delta=MEDIA_BOX_TOLERANCE_POINTS,
                    msg=(
                        f"Page {page_number} MediaBox is not A4: "
                        f"{tuple(actual_dimensions)}"
                    ),
                )

    def _render_to_ppm(self, pdf_path: Path, output_prefix: Path) -> list[Path]:
        """Poppler로 각 PDF 페이지를 PPM P6 이미지로 렌더링한다."""

        completed = subprocess.run(
            [
                str(PDFTOPPM),
                "-r",
                "72",
                str(pdf_path),
                str(output_prefix),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        return sorted(
            output_prefix.parent.glob(f"{output_prefix.name}-*.ppm"),
            key=lambda path: int(path.stem.rsplit("-", maxsplit=1)[1]),
        )

    def _assert_corner_markers_have_internal_margins(
        self,
        ppm_path: Path,
        minimum_margin: int,
    ) -> None:
        """네 색 마커가 렌더에 남고 어느 픽셀도 이미지 경계에 닿지 않는지 검증한다."""

        image = _read_ppm_p6(ppm_path)
        for color_name, matcher in COLOR_MATCHERS.items():
            bounds = _find_color_bounds(image, matcher)
            self.assertIsNotNone(bounds, f"{color_name} marker is missing: {ppm_path}")
            if bounds is None:
                continue

            left, top, right, bottom = bounds
            margins = (
                left,
                top,
                image.width - 1 - right,
                image.height - 1 - bottom,
            )
            self.assertGreaterEqual(
                min(margins),
                minimum_margin,
                f"{color_name} marker touches the image boundary: {bounds}, {ppm_path}",
            )
            self.assertGreaterEqual(right - left + 1, 5)
            self.assertGreaterEqual(bottom - top + 1, 5)

            center_x = (left + right) / 2
            center_y = (top + bottom) / 2
            self.assertLess(
                min(center_x, image.width - 1 - center_x),
                image.width * 0.3,
                f"{color_name} marker is no longer near a horizontal corner: {bounds}",
            )
            self.assertLess(
                min(center_y, image.height - 1 - center_y),
                image.height * 0.3,
                f"{color_name} marker is no longer near a vertical corner: {bounds}",
            )


if __name__ == "__main__":
    unittest.main()
