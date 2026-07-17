from __future__ import annotations

import logging
import unittest

from main import configure_application_logging


class ApplicationLoggingTest(unittest.TestCase):
    """운영에서 출력 작업의 INFO 증거가 사라지지 않는지 검증한다."""

    def test_core_info_logger_has_an_explicit_handler(self) -> None:
        """Uvicorn root logger에 기대지 않고 core 로그를 직접 출력해야 한다."""

        configure_application_logging()

        application_logger = logging.getLogger("core")
        job_logger = logging.getLogger("core.printers")
        self.assertEqual(job_logger.getEffectiveLevel(), logging.INFO)
        self.assertTrue(application_logger.handlers)
        self.assertFalse(application_logger.propagate)


if __name__ == "__main__":
    unittest.main()
