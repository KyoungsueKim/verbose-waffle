from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Sequence

from core.config import PrintConfig
from core.printing.cups import (
    CupsConversionError,
    CupsPrintFileConverter,
    CupsPrintOptionsBuilder,
)
from core.printing.models import DuplexMode, PaperSize, PrintScaling


class FakeCommandRunner:
    """CUPS 호출 순서, 제한 시간, 실패 정리를 기록하는 테스트 실행기다."""

    def __init__(
        self,
        output_path: Path,
        statuses: list[bytes] | None = None,
        fail_command: str | None = None,
        output_bytes: bytes | None = b"synthetic-prn",
    ) -> None:
        self.output_path = output_path
        self.statuses = statuses or [b""]
        self.fail_command = fail_command
        self._failure_emitted = False
        self.output_bytes = output_bytes
        self.calls: list[tuple[list[str], float]] = []

    def run(self, command: Sequence[str], timeout: float) -> bytes:
        normalized_command = list(command)
        self.calls.append((normalized_command, timeout))
        if (
            self.fail_command == normalized_command[0]
            and not self._failure_emitted
        ):
            self._failure_emitted = True
            raise RuntimeError(f"forced {normalized_command[0]} failure")
        if normalized_command[0] == "lpr" and self.output_bytes is not None:
            self.output_path.write_bytes(self.output_bytes)
        if normalized_command[0] == "lpstat":
            if len(self.statuses) > 1:
                return self.statuses.pop(0)
            return self.statuses[0]
        return b""


class FakeClock:
    """실제 대기 없이 CUPS 전체 deadline을 검증한다."""

    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


class CupsPrintOptionsBuilderTest(unittest.TestCase):
    """API 용지와 등록 용지가 동일한 CUPS 옵션이 되는지 검증한다."""

    def test_a4_auto_fit_simplex_options(self) -> None:
        options = CupsPrintOptionsBuilder(PrintConfig()).build(
            PaperSize.A4,
            DuplexMode.SIMPLEX,
        )

        self.assertEqual(
            options,
            [
                "-o",
                "ColorModel=KGray",
                "-o",
                "media=A4",
                "-o",
                "print-scaling=auto-fit",
                "-o",
                "Duplex=None",
            ],
        )

    def test_a3_auto_fit_short_edge_options(self) -> None:
        options = CupsPrintOptionsBuilder(PrintConfig()).build(
            PaperSize.A3,
            DuplexMode.SHORT_EDGE,
        )

        self.assertIn("media=A3", options)
        self.assertIn("print-scaling=auto-fit", options)
        self.assertIn("Duplex=DuplexTumble", options)
        self.assertIn("BindEdge=Top", options)

    def test_none_is_an_explicit_rollback_mode(self) -> None:
        options = CupsPrintOptionsBuilder(
            PrintConfig(cups_scaling=PrintScaling.NONE)
        ).build(PaperSize.A4, DuplexMode.LONG_EDGE)

        self.assertIn("print-scaling=none", options)


class CupsPrintFileConverterTest(unittest.TestCase):
    """PRN 유효성과 모든 실패 경로의 임시 큐 정리를 검증한다."""

    def test_success_waits_for_job_and_deletes_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = PrintConfig(output_dir=root)
            output_path = root / "JOB.prn"
            runner = FakeCommandRunner(output_path)
            converter = CupsPrintFileConverter(config, command_runner=runner)
            pdf_path = root / "oversized-a3.pdf"
            pdf_path.write_bytes(b"synthetic-pdf")

            result = converter.convert(
                "JOB",
                pdf_path,
                PaperSize.A4,
                DuplexMode.SIMPLEX,
            )

            self.assertEqual(result, output_path)
            lpr_command = runner.calls[1][0]
            self.assertEqual(lpr_command[:3], ["lpr", "-P", "JOB"])
            self.assertIn("media=A4", lpr_command)
            self.assertIn("print-scaling=auto-fit", lpr_command)
            self.assertEqual(lpr_command[-1], str(pdf_path))
            self.assertEqual(
                runner.calls[2][0],
                ["lpstat", "-W", "not-completed", "-o", "JOB"],
            )
            self.assertEqual(runner.calls[-1][0], ["lpadmin", "-x", "JOB"])
            self.assertTrue(all(timeout > 0 for _, timeout in runner.calls))

    def test_lpr_failure_reports_stage_and_deletes_created_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = FakeCommandRunner(root / "JOB.prn", fail_command="lpr")
            converter = CupsPrintFileConverter(
                PrintConfig(output_dir=root),
                command_runner=runner,
            )

            with self.assertRaises(CupsConversionError) as raised:
                converter.convert(
                    "JOB",
                    root / "input.pdf",
                    PaperSize.A4,
                    DuplexMode.SIMPLEX,
                )

            self.assertEqual(raised.exception.stage, "submit_job")
            self.assertIn("forced lpr failure", str(raised.exception))
            self.assertEqual(runner.calls[-1][0], ["lpadmin", "-x", "JOB"])

    def test_ambiguous_queue_creation_failure_still_attempts_exact_cleanup(self) -> None:
        """lpadmin 실패가 큐 생성 뒤 발생했을 가능성까지 안전하게 정리한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = FakeCommandRunner(root / "JOB.prn", fail_command="lpadmin")
            converter = CupsPrintFileConverter(
                PrintConfig(output_dir=root),
                command_runner=runner,
            )

            with self.assertRaises(CupsConversionError) as raised:
                converter.convert(
                    "JOB",
                    root / "input.pdf",
                    PaperSize.A4,
                    DuplexMode.SIMPLEX,
                )

            self.assertEqual(raised.exception.stage, "create_queue")
            self.assertEqual(runner.calls[0][0][0:3], ["lpadmin", "-p", "JOB"])
            self.assertEqual(runner.calls[-1][0], ["lpadmin", "-x", "JOB"])

    def test_timeout_still_deletes_created_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clock = FakeClock()
            runner = FakeCommandRunner(
                root / "JOB.prn",
                statuses=[b"JOB-1 user 1024"],
            )
            converter = CupsPrintFileConverter(
                PrintConfig(
                    output_dir=root,
                    cups_job_timeout_seconds=2,
                    cups_poll_interval_seconds=1,
                ),
                command_runner=runner,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

            with self.assertRaises(CupsConversionError) as raised:
                converter.convert(
                    "JOB",
                    root / "input.pdf",
                    PaperSize.A4,
                    DuplexMode.SIMPLEX,
                )

            self.assertIsInstance(raised.exception.__cause__, TimeoutError)
            self.assertEqual(raised.exception.stage, "wait_for_job")
            self.assertEqual(runner.calls[-1][0], ["lpadmin", "-x", "JOB"])

    def test_missing_or_empty_prn_never_succeeds(self) -> None:
        for output_bytes in (None, b""):
            with self.subTest(output_bytes=output_bytes):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    clock = FakeClock()
                    runner = FakeCommandRunner(
                        root / "JOB.prn",
                        output_bytes=output_bytes,
                    )
                    converter = CupsPrintFileConverter(
                        PrintConfig(
                            output_dir=root,
                            cups_job_timeout_seconds=1,
                            cups_poll_interval_seconds=1,
                        ),
                        command_runner=runner,
                        monotonic=clock.monotonic,
                        sleep=clock.sleep,
                    )

                    with self.assertRaises(CupsConversionError) as raised:
                        converter.convert(
                            "JOB",
                            root / "input.pdf",
                            PaperSize.A4,
                            DuplexMode.SIMPLEX,
                        )

                    self.assertEqual(raised.exception.stage, "wait_for_job")
                    self.assertEqual(
                        runner.calls[-1][0], ["lpadmin", "-x", "JOB"]
                    )

    def test_existing_prn_path_is_rejected_before_queue_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_path = root / "JOB.prn"
            output_path.write_bytes(b"stale")
            runner = FakeCommandRunner(output_path)
            converter = CupsPrintFileConverter(
                PrintConfig(output_dir=root), command_runner=runner
            )

            with self.assertRaises(CupsConversionError) as raised:
                converter.convert(
                    "JOB",
                    root / "input.pdf",
                    PaperSize.A4,
                    DuplexMode.SIMPLEX,
                )

            self.assertEqual(raised.exception.stage, "prepare_output")
            self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()
