from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

A3_PORTRAIT = (841.9, 1190.5)
A4_PORTRAIT = (595.3, 841.9)
A5_PORTRAIT = (419.5, 595.3)


def write_marked_pdf(output_path: Path, page_sizes: Iterable[tuple[float, float]]) -> Path:
    """실제 사용자 문서 없이 모서리 잘림을 판별할 합성 PDF를 만든다."""

    writer = PdfWriter()
    for width, height in page_sizes:
        page = PageObject.create_blank_page(width=width, height=height)
        page[NameObject("/Contents")] = _marker_stream(width, height)
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)
    return output_path


def write_duplex_test_pdf(output_path: Path) -> Path:
    """물리 양면 넘김 방향을 판별할 안전 여백의 2쪽 A4 PDF를 만든다."""

    writer = PdfWriter()
    width, height = A4_PORTRAIT
    for page_number in (1, 2):
        page = PageObject.create_blank_page(width=width, height=height)
        page[NameObject("/Contents")] = _duplex_marker_stream(
            width,
            height,
            page_number,
        )
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)
    return output_path


def _marker_stream(width: float, height: float) -> DecodedStreamObject:
    """페이지 테두리, 네 색 모서리, 중심 십자 표시를 PDF 명령으로 만든다."""

    inset = 2.0
    marker = 36.0
    center_x = width / 2
    center_y = height / 2
    commands = f"""
q
2 w 0 0 0 RG {inset} {inset} {width - 2 * inset} {height - 2 * inset} re S
1 0 0 rg {inset} {height - inset - marker} {marker} {marker} re f
0 1 0 rg {width - inset - marker} {height - inset - marker} {marker} {marker} re f
0 0 1 rg {inset} {inset} {marker} {marker} re f
1 0 1 rg {width - inset - marker} {inset} {marker} {marker} re f
0 0 0 RG 3 w {center_x - 30} {center_y} m {center_x + 30} {center_y} l S
{center_x} {center_y - 30} m {center_x} {center_y + 30} l S
Q
""".strip()
    stream = DecodedStreamObject()
    stream.set_data(commands.encode("ascii"))
    return stream


def _duplex_marker_stream(
    width: float,
    height: float,
    page_number: int,
) -> DecodedStreamObject:
    """Canon A4 비인쇄 여백 안쪽에 방향 화살표와 면 식별 표식을 그린다."""

    inset = 24.0
    marker = 48.0
    center_x = width / 2
    top = height - inset
    marker_x = inset if page_number == 1 else width - inset - marker
    marker_color = "1 0 0" if page_number == 1 else "0 0 1"
    page_bars = "\n".join(
        f"0 0 0 rg {center_x - 24} {inset + 12 + index * 14} 48 7 re f"
        for index in range(page_number)
    )
    commands = f"""
q
3 w 0 0 0 RG {inset} {inset} {width - 2 * inset} {height - 2 * inset} re S
{marker_color} rg {marker_x} {top - marker} {marker} {marker} re f
0 0 0 rg {center_x} {top - 4} m {center_x - 32} {top - 52} l {center_x + 32} {top - 52} l h f
{page_bars}
Q
""".strip()
    stream = DecodedStreamObject()
    stream.set_data(commands.encode("ascii"))
    return stream
