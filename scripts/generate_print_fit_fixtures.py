from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.support.pdf_factory import (  # noqa: E402
    A3_PORTRAIT,
    A4_PORTRAIT,
    A5_PORTRAIT,
    write_duplex_test_pdf,
    write_marked_pdf,
)


def main() -> None:
    """운영 문서를 사용하지 않고 자동 맞춤 검증용 PDF 세트를 생성한다."""

    output_dir = PROJECT_ROOT / "tmp" / "pdfs"
    fixtures = {
        "a3-portrait.pdf": [A3_PORTRAIT],
        "a3-landscape.pdf": [(A3_PORTRAIT[1], A3_PORTRAIT[0])],
        "exact-a4.pdf": [A4_PORTRAIT],
        "a5-portrait.pdf": [A5_PORTRAIT],
        "mixed-a3-a4-a5.pdf": [A3_PORTRAIT, A4_PORTRAIT, A5_PORTRAIT],
    }
    for file_name, page_sizes in fixtures.items():
        output_path = write_marked_pdf(output_dir / file_name, page_sizes)
        print(output_path)

    duplex_path = write_duplex_test_pdf(output_dir / "duplex-a4-safe.pdf")
    print(duplex_path)


if __name__ == "__main__":
    main()
