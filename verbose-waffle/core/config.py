from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from core.printing.models import PrintScaling


@dataclass(frozen=True)
class PrintConfig:
    """프린트 처리에 필요한 설정을 모아둔 구성 값이다."""

    temp_dir: Path = Path("temp")
    output_dir: Path = Path("/root")
    cups_model: str = "CNRCUPSIRADV45453ZK.ppd"
    cups_media_a4: str = "A4"
    cups_media_a3: str = "A3"
    cups_scaling: PrintScaling = PrintScaling.AUTO_FIT
    cups_job_timeout_seconds: float = 180.0
    cups_poll_interval_seconds: float = 1.0
    cups_cleanup_timeout_seconds: float = 10.0
    retain_job_files: bool = True
    http_connect_timeout_seconds: float = 10.0
    http_read_timeout_seconds: float = 60.0
    upload_bin_url: str = "http://218.145.52.6:8080/spbs/upload_bin"
    register_doc_url: str = "http://u-printon.canon-bs.co.kr:62301/nologin/regist_doc/"
    franchise_id: int = 28

    @property
    def http_timeout(self) -> tuple[float, float]:
        """requests가 사용하는 연결/응답 대기 제한 시간을 반환한다."""

        return self.http_connect_timeout_seconds, self.http_read_timeout_seconds

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "PrintConfig":
        """환경변수를 읽어 운영자가 코드 수정 없이 출력 정책을 바꾸게 한다."""

        source = os.environ if environ is None else environ
        config = cls(
            temp_dir=Path(
                _required_text(
                    source.get("PRINT_TEMP_DIR", "temp"),
                    "PRINT_TEMP_DIR",
                )
            ),
            output_dir=Path(
                _required_text(
                    source.get("PRINT_OUTPUT_DIR", "/root"),
                    "PRINT_OUTPUT_DIR",
                )
            ),
            cups_model=_required_text(
                source.get("PRINT_CUPS_MODEL", "CNRCUPSIRADV45453ZK.ppd"),
                "PRINT_CUPS_MODEL",
            ),
            cups_media_a4=_required_text(
                source.get("PRINT_CUPS_MEDIA_A4", "A4"),
                "PRINT_CUPS_MEDIA_A4",
            ),
            cups_media_a3=_required_text(
                source.get("PRINT_CUPS_MEDIA_A3", "A3"),
                "PRINT_CUPS_MEDIA_A3",
            ),
            cups_scaling=PrintScaling.from_config_value(
                source.get("PRINT_CUPS_SCALING", PrintScaling.AUTO_FIT.value)
            ),
            cups_job_timeout_seconds=_positive_float(
                source.get("PRINT_CUPS_JOB_TIMEOUT_SECONDS", "180"),
                "PRINT_CUPS_JOB_TIMEOUT_SECONDS",
            ),
            cups_poll_interval_seconds=_positive_float(
                source.get("PRINT_CUPS_POLL_INTERVAL_SECONDS", "1"),
                "PRINT_CUPS_POLL_INTERVAL_SECONDS",
            ),
            cups_cleanup_timeout_seconds=_positive_float(
                source.get("PRINT_CUPS_CLEANUP_TIMEOUT_SECONDS", "10"),
                "PRINT_CUPS_CLEANUP_TIMEOUT_SECONDS",
            ),
            retain_job_files=_boolean(
                source.get("PRINT_RETAIN_JOB_FILES", "true"),
                "PRINT_RETAIN_JOB_FILES",
            ),
            http_connect_timeout_seconds=_positive_float(
                source.get("PRINT_HTTP_CONNECT_TIMEOUT_SECONDS", "10"),
                "PRINT_HTTP_CONNECT_TIMEOUT_SECONDS",
            ),
            http_read_timeout_seconds=_positive_float(
                source.get("PRINT_HTTP_READ_TIMEOUT_SECONDS", "60"),
                "PRINT_HTTP_READ_TIMEOUT_SECONDS",
            ),
            upload_bin_url=_required_text(
                source.get("PRINT_UPLOAD_BIN_URL", "http://218.145.52.6:8080/spbs/upload_bin"),
                "PRINT_UPLOAD_BIN_URL",
            ),
            register_doc_url=_required_text(
                source.get(
                    "PRINT_REGISTER_DOC_URL",
                    "http://u-printon.canon-bs.co.kr:62301/nologin/regist_doc/",
                ),
                "PRINT_REGISTER_DOC_URL",
            ),
            franchise_id=_positive_integer(
                source.get("PRINT_FRANCHISE_ID", "28"),
                "PRINT_FRANCHISE_ID",
            ),
        )
        return config


def _required_text(value: str, variable_name: str) -> str:
    """빈 문자열을 허용하지 않는 환경변수를 검증한다."""

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{variable_name} must not be empty.")
    return normalized_value


def _positive_float(value: str, variable_name: str) -> float:
    """0보다 큰 실수 환경변수를 읽는다."""

    try:
        parsed_value = float(value)
    except ValueError as exc:
        raise ValueError(f"{variable_name} must be a number; received '{value}'.") from exc
    if not math.isfinite(parsed_value) or parsed_value <= 0:
        raise ValueError(f"{variable_name} must be greater than zero; received '{value}'.")
    return parsed_value


def _positive_integer(value: str, variable_name: str) -> int:
    """0보다 큰 정수 환경변수를 읽고 설정 오류를 즉시 알린다."""

    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise ValueError(f"{variable_name} must be an integer; received '{value}'.") from exc
    if parsed_value <= 0:
        raise ValueError(f"{variable_name} must be greater than zero; received '{value}'.")
    return parsed_value


def _boolean(value: str, variable_name: str) -> bool:
    """사람이 읽기 쉬운 true/false 환경변수를 불리언으로 변환한다."""

    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{variable_name} must be true or false; received '{value}'.")


@dataclass(frozen=True)
class AdmobSsvConfig:
    """AdMob SSV 검증에 필요한 설정을 모아둔 구성 값이다."""

    key_server_url: str = "https://www.gstatic.com/admob/reward/verifier-keys.json"
    cache_ttl_seconds: int = 24 * 60 * 60


@dataclass(frozen=True)
class AppAdsConfig:
    """app-ads.txt 제공을 위한 설정."""

    lines: tuple[str, ...] = (
        "google.com, pub-8286712861565957, DIRECT, f08c47fec0942fa0",
        "facebook.com, 1207724671011144, DIRECT, c3e20eee3f780d68",
    )
