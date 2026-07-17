from __future__ import annotations

import unittest

from core.routes.print_jobs import _parse_optional_boolean


class PrintJobRouteParsingTest(unittest.TestCase):
    """출력 폼 값이 조용한 fallback 없이 검증되는지 확인한다."""

    def test_missing_is_a3_keeps_legacy_a4_default(self) -> None:
        self.assertFalse(_parse_optional_boolean(None, "is_a3"))

    def test_supported_boolean_spellings_are_normalized(self) -> None:
        self.assertTrue(_parse_optional_boolean(" YES ", "is_a3"))
        self.assertFalse(_parse_optional_boolean("0", "is_a3"))

    def test_unknown_boolean_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "is_a3 must be true or false"):
            _parse_optional_boolean("a3", "is_a3")


if __name__ == "__main__":
    unittest.main()
