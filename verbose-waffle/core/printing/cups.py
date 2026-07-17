from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from core.config import PrintConfig
from core.printing.models import DuplexMode, PaperSize


class CupsCommandError(RuntimeError):
    """실패한 CUPS 실행 파일과 종료 상태를 보존하는 인프라 오류다."""

    def __init__(self, command: Sequence[str], return_code: int, stderr: bytes) -> None:
        self.executable = command[0]
        self.return_code = return_code
        self.stderr = stderr.decode("utf-8", errors="replace").strip()
        detail = self.stderr or "no stderr output"
        super().__init__(
            f"{self.executable} exited with code {self.return_code}: {detail}"
        )


class CupsConversionError(RuntimeError):
    """CUPS 변환 실패 단계와 원인을 애플리케이션 경계에 전달한다."""

    def __init__(self, job_id: str, stage: str, cause: Exception) -> None:
        self.job_id = job_id
        self.stage = stage
        super().__init__(f"CUPS stage '{stage}' failed for job '{job_id}': {cause}")


class CommandRunner(Protocol):
    """CUPS 명령 실행을 테스트 대역으로 교체하기 위한 포트다."""

    def run(self, command: Sequence[str], timeout: float) -> bytes:
        """명령을 제한 시간 안에 실행하고 표준 출력을 반환한다."""


class SubprocessCommandRunner:
    """subprocess를 이용하는 운영 환경용 CUPS 명령 실행기다."""

    def run(self, command: Sequence[str], timeout: float) -> bytes:
        """셸 없이 명령을 실행하며 locale과 오류 출력을 예측 가능하게 고정한다."""

        environment = os.environ.copy()
        environment.update({"LC_ALL": "C", "LANG": "C"})
        try:
            result = subprocess.run(
                list(command),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"{command[0]} exceeded its {timeout:g}-second command timeout."
            ) from exc
        if result.returncode != 0:
            raise CupsCommandError(command, result.returncode, result.stderr)
        return result.stdout


class CupsPrintOptionsBuilder:
    """도메인 출력 정책을 CUPS lpr 작업 옵션으로 직렬화한다."""

    def __init__(self, config: PrintConfig) -> None:
        self._config = config

    def build(self, paper_size: PaperSize, duplex_mode: DuplexMode) -> list[str]:
        """용지, 자동 맞춤, 흑백 및 양면 옵션을 예측 가능한 순서로 만든다."""

        media = (
            self._config.cups_media_a3
            if paper_size is PaperSize.A3
            else self._config.cups_media_a4
        )
        return [
            "-o",
            "ColorModel=KGray",
            "-o",
            f"media={media}",
            "-o",
            f"print-scaling={self._config.cups_scaling.value}",
            *self._duplex_options(duplex_mode),
        ]

    @staticmethod
    def _duplex_options(duplex_mode: DuplexMode) -> list[str]:
        """Canon UFR II PPD가 이해하는 양면 옵션을 반환한다."""

        if duplex_mode is DuplexMode.LONG_EDGE:
            return ["-o", "Duplex=DuplexNoTumble", "-o", "BindEdge=Left"]
        if duplex_mode is DuplexMode.SHORT_EDGE:
            return ["-o", "Duplex=DuplexTumble", "-o", "BindEdge=Top"]
        return ["-o", "Duplex=None"]


class CupsPrintFileConverter:
    """작업별 CUPS 파일 큐를 만들고 하나의 deadline 안에서 PRN으로 변환한다."""

    def __init__(
        self,
        config: PrintConfig,
        command_runner: CommandRunner | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._command_runner = command_runner or SubprocessCommandRunner()
        self._monotonic = monotonic
        self._sleep = sleep
        self._options_builder = CupsPrintOptionsBuilder(config)

    def convert(
        self,
        job_id: str,
        pdf_path: Path,
        paper_size: PaperSize,
        duplex_mode: DuplexMode,
    ) -> Path:
        """용지와 자동맞춤 정책을 전달하고 유효한 비어 있지 않은 PRN을 반환한다."""

        deadline = self._monotonic() + self._config.cups_job_timeout_seconds
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._config.output_dir / f"{job_id}.prn"
        queue_creation_attempted = False
        stage = "prepare_output"
        failure: tuple[str, Exception] | None = None

        try:
            if output_path.exists():
                raise FileExistsError(f"Refusing to reuse existing PRN path: {output_path}")

            stage = "create_queue"
            queue_creation_attempted = True
            self._run_before_deadline(
                self._build_create_queue_command(job_id, output_path), deadline
            )

            stage = "submit_job"
            self._run_before_deadline(
                self._build_lpr_command(job_id, pdf_path, paper_size, duplex_mode),
                deadline,
            )

            stage = "wait_for_job"
            self._wait_for_completion(job_id, output_path, deadline)
        except Exception as exc:  # noqa: BLE001 - CUPS 오류를 단일 경계에서 변환한다.
            failure = (stage, exc)
        finally:
            if queue_creation_attempted:
                try:
                    self._command_runner.run(
                        ["lpadmin", "-x", job_id],
                        timeout=self._config.cups_cleanup_timeout_seconds,
                    )
                except Exception as cleanup_exc:  # noqa: BLE001 - 원래 오류를 보존한다.
                    if failure is None:
                        failure = ("cleanup_queue", cleanup_exc)
                    else:
                        failure[1].add_note(
                            f"CUPS queue cleanup also failed: {cleanup_exc}"
                        )

        if failure is not None:
            failure_stage, cause = failure
            raise CupsConversionError(job_id, failure_stage, cause) from cause
        return output_path

    def _run_before_deadline(self, command: Sequence[str], deadline: float) -> bytes:
        """전체 작업 deadline의 남은 시간만 해당 명령에 허용한다."""

        remaining_seconds = deadline - self._monotonic()
        if remaining_seconds <= 0:
            raise TimeoutError(
                f"CUPS job exceeded {self._config.cups_job_timeout_seconds:g} seconds."
            )
        return self._command_runner.run(command, timeout=remaining_seconds)

    def _build_create_queue_command(self, job_id: str, output_path: Path) -> list[str]:
        """고유 PRN 경로를 사용하는 임시 CUPS 큐 생성 명령을 만든다."""

        return [
            "lpadmin",
            "-p",
            job_id,
            "-v",
            output_path.resolve().as_uri(),
            "-E",
            "-m",
            self._config.cups_model,
        ]

    def _build_lpr_command(
        self,
        job_id: str,
        pdf_path: Path,
        paper_size: PaperSize,
        duplex_mode: DuplexMode,
    ) -> list[str]:
        """PDF 제출에 필요한 모든 작업 옵션을 한곳에서 구성한다."""

        return [
            "lpr",
            "-P",
            job_id,
            *self._options_builder.build(paper_size, duplex_mode),
            str(pdf_path),
        ]

    def _wait_for_completion(
        self,
        job_id: str,
        output_path: Path,
        deadline: float,
    ) -> None:
        """미완료 작업이 사라지고 비어 있지 않은 PRN이 생길 때까지 기다린다."""

        while True:
            pending_jobs = self._run_before_deadline(
                ["lpstat", "-W", "not-completed", "-o", job_id],
                deadline,
            )
            output_is_ready = output_path.is_file() and output_path.stat().st_size > 0
            if not pending_jobs.strip() and output_is_ready:
                return

            remaining_seconds = deadline - self._monotonic()
            if remaining_seconds <= 0:
                output_state = (
                    "missing"
                    if not output_path.exists()
                    else f"{output_path.stat().st_size}-byte"
                )
                raise TimeoutError(
                    f"CUPS job '{job_id}' did not produce a completed non-empty PRN "
                    f"within {self._config.cups_job_timeout_seconds:g} seconds "
                    f"(output: {output_state})."
                )
            self._sleep(
                min(self._config.cups_poll_interval_seconds, remaining_seconds)
            )
