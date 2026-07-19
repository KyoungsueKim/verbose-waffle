from __future__ import annotations

import unittest
from pathlib import Path

from core.config import PrintConfig
from core.printing.models import PrintScaling


class PrintConfigTest(unittest.TestCase):
    """환경변수 기반 프린트 설정의 기본값과 실패 메시지를 검증한다."""

    def test_defaults_enable_auto_fit_and_preserve_current_debug_files(self) -> None:
        config = PrintConfig.from_env({})

        self.assertIs(config.cups_scaling, PrintScaling.AUTO_FIT)
        self.assertEqual(config.cups_media_a4, "A4")
        self.assertEqual(config.cups_media_a3, "A3")
        self.assertTrue(config.retain_job_files)
        self.assertTrue(config.log_phone_number)
        self.assertTrue(config.log_file_name)

    def test_all_operational_values_can_be_overridden(self) -> None:
        config = PrintConfig.from_env(
            {
                "PRINT_TEMP_DIR": "/work/input",
                "PRINT_OUTPUT_DIR": "/work/output",
                "PRINT_CUPS_MODEL": "custom.ppd",
                "PRINT_CUPS_MEDIA_A4": "iso_a4_210x297mm",
                "PRINT_CUPS_MEDIA_A3": "iso_a3_297x420mm",
                "PRINT_CUPS_SCALING": "fit",
                "PRINT_CUPS_JOB_TIMEOUT_SECONDS": "45.5",
                "PRINT_CUPS_POLL_INTERVAL_SECONDS": "0.25",
                "PRINT_CUPS_CLEANUP_TIMEOUT_SECONDS": "7",
                "PRINT_RETAIN_JOB_FILES": "false",
                "PRINT_LOG_PHONE_NUMBER": "false",
                "PRINT_LOG_FILE_NAME": "false",
                "PRINT_HTTP_CONNECT_TIMEOUT_SECONDS": "3",
                "PRINT_HTTP_READ_TIMEOUT_SECONDS": "12",
                "PRINT_UPLOAD_BIN_URL": "http://upload.test/binary",
                "PRINT_REGISTER_DOC_URL": "http://register.test/document",
                "PRINT_FRANCHISE_ID": "99",
            }
        )

        self.assertEqual(config.temp_dir, Path("/work/input"))
        self.assertEqual(config.output_dir, Path("/work/output"))
        self.assertEqual(config.cups_model, "custom.ppd")
        self.assertEqual(config.cups_media_a4, "iso_a4_210x297mm")
        self.assertEqual(config.cups_media_a3, "iso_a3_297x420mm")
        self.assertIs(config.cups_scaling, PrintScaling.FIT)
        self.assertEqual(config.cups_job_timeout_seconds, 45.5)
        self.assertEqual(config.cups_poll_interval_seconds, 0.25)
        self.assertEqual(config.cups_cleanup_timeout_seconds, 7)
        self.assertFalse(config.retain_job_files)
        self.assertFalse(config.log_phone_number)
        self.assertFalse(config.log_file_name)
        self.assertEqual(config.http_timeout, (3, 12))
        self.assertEqual(config.franchise_id, 99)

    def test_invalid_scaling_fails_at_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "PRINT_CUPS_SCALING"):
            PrintConfig.from_env({"PRINT_CUPS_SCALING": "fill"})

    def test_empty_job_directory_fails_at_startup(self) -> None:
        """빈 경로가 작업 디렉터리 대신 현재 디렉터리로 해석되면 안 된다."""

        for variable_name in ("PRINT_TEMP_DIR", "PRINT_OUTPUT_DIR"):
            with self.subTest(variable_name=variable_name):
                with self.assertRaisesRegex(ValueError, variable_name):
                    PrintConfig.from_env({variable_name: "   "})

    def test_non_positive_timeout_fails_at_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "PRINT_CUPS_JOB_TIMEOUT_SECONDS"):
            PrintConfig.from_env({"PRINT_CUPS_JOB_TIMEOUT_SECONDS": "0"})

    def test_non_finite_timeout_fails_at_startup(self) -> None:
        for raw_value in ("nan", "inf", "-inf"):
            with self.subTest(raw_value=raw_value):
                with self.assertRaisesRegex(ValueError, "PRINT_CUPS_JOB_TIMEOUT_SECONDS"):
                    PrintConfig.from_env(
                        {"PRINT_CUPS_JOB_TIMEOUT_SECONDS": raw_value}
                    )

    def test_invalid_retention_flag_fails_at_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "PRINT_RETAIN_JOB_FILES"):
            PrintConfig.from_env({"PRINT_RETAIN_JOB_FILES": "sometimes"})

    def test_invalid_log_flags_fail_at_startup(self) -> None:
        """민감정보 로그 옵션의 오타를 조용히 기본값으로 처리하지 않는다."""

        for variable_name in ("PRINT_LOG_PHONE_NUMBER", "PRINT_LOG_FILE_NAME"):
            with self.subTest(variable_name=variable_name):
                with self.assertRaisesRegex(ValueError, variable_name):
                    PrintConfig.from_env({variable_name: "sometimes"})

    def test_non_positive_franchise_id_fails_at_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "PRINT_FRANCHISE_ID"):
            PrintConfig.from_env({"PRINT_FRANCHISE_ID": "0"})


if __name__ == "__main__":
    unittest.main()
