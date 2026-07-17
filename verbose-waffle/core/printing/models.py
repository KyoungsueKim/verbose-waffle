from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DuplexMode(str, Enum):
    """API 요청에서 선택할 수 있는 단면/양면 인쇄 모드다."""

    SIMPLEX = "simplex"
    LONG_EDGE = "long_edge"
    SHORT_EDGE = "short_edge"

    @classmethod
    def from_api_value(cls, value: str | None) -> "DuplexMode":
        """요청 문자열을 도메인 값으로 변환하며 누락 값은 단면으로 처리한다."""

        normalized_value = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized_value:
            return cls.SIMPLEX

        aliases = {
            "simplex": cls.SIMPLEX,
            "one_sided": cls.SIMPLEX,
            "none": cls.SIMPLEX,
            "off": cls.SIMPLEX,
            "false": cls.SIMPLEX,
            "long_edge": cls.LONG_EDGE,
            "two_sided_long_edge": cls.LONG_EDGE,
            "duplex": cls.LONG_EDGE,
            "duplexnotumble": cls.LONG_EDGE,
            "duplex_no_tumble": cls.LONG_EDGE,
            "true": cls.LONG_EDGE,
            "short_edge": cls.SHORT_EDGE,
            "two_sided_short_edge": cls.SHORT_EDGE,
            "duplextumble": cls.SHORT_EDGE,
            "duplex_tumble": cls.SHORT_EDGE,
        }
        try:
            return aliases[normalized_value]
        except KeyError as exc:
            supported_values = "simplex, long_edge, short_edge"
            raise ValueError(
                f"Unsupported duplex_mode '{value}'. Supported values: {supported_values}."
            ) from exc


class PaperSize(str, Enum):
    """등록 서버와 CUPS 작업에서 함께 사용하는 출력 용지 크기다."""

    A4 = "A4"
    A3 = "A3"

    @classmethod
    def from_is_a3(cls, is_a3: bool) -> "PaperSize":
        """기존 API의 A3 선택 값을 명시적인 용지 크기로 변환한다."""

        return cls.A3 if is_a3 else cls.A4


class PrintScaling(str, Enum):
    """잘림을 만들 수 있는 값을 제외한 CUPS 확대/축소 정책이다."""

    AUTO_FIT = "auto-fit"
    FIT = "fit"
    NONE = "none"

    @classmethod
    def from_config_value(cls, value: str) -> "PrintScaling":
        """환경변수 값을 검증된 확대/축소 정책으로 변환한다."""

        normalized_value = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized_value)
        except ValueError as exc:
            supported_values = ", ".join(item.value for item in cls)
            raise ValueError(
                "PRINT_CUPS_SCALING must be one of "
                f"{supported_values}; received '{value}'."
            ) from exc


@dataclass(frozen=True)
class PdfDocumentInfo:
    """업로드 PDF에서 출력 흐름에 필요한 최소 메타데이터다."""

    page_count: int


@dataclass(frozen=True)
class PrintJobResult:
    """프린트 처리 결과를 담는 값 객체다."""

    phone_number: str
    file_name: str
    page_count: int
    is_a3: bool
    duplex_mode: DuplexMode
    paper_size: PaperSize
    print_scaling: PrintScaling
