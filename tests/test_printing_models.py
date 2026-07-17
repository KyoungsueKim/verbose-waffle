from __future__ import annotations

import unittest

from core.printing.models import DuplexMode, PaperSize, PrintScaling


class DuplexModeTest(unittest.TestCase):
    """API 별칭과 내부 양면 모드의 계약을 검증한다."""

    def test_missing_value_defaults_to_simplex(self) -> None:
        self.assertIs(DuplexMode.from_api_value(None), DuplexMode.SIMPLEX)

    def test_supported_aliases_are_normalized(self) -> None:
        cases = {
            "true": DuplexMode.LONG_EDGE,
            "two-sided-long-edge": DuplexMode.LONG_EDGE,
            "DuplexTumble": DuplexMode.SHORT_EDGE,
            "one sided": DuplexMode.SIMPLEX,
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertIs(DuplexMode.from_api_value(raw_value), expected)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported duplex_mode"):
            DuplexMode.from_api_value("booklet")


class PaperAndScalingTest(unittest.TestCase):
    """용지와 스케일링 설정이 제한된 값만 허용하는지 검증한다."""

    def test_is_a3_maps_to_same_media_used_for_registration(self) -> None:
        self.assertIs(PaperSize.from_is_a3(False), PaperSize.A4)
        self.assertIs(PaperSize.from_is_a3(True), PaperSize.A3)

    def test_scaling_normalizes_environment_spelling(self) -> None:
        self.assertIs(PrintScaling.from_config_value(" AUTO_FIT "), PrintScaling.AUTO_FIT)

    def test_clipping_prone_fill_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "PRINT_CUPS_SCALING"):
            PrintScaling.from_config_value("fill")


if __name__ == "__main__":
    unittest.main()
