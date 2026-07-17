from __future__ import annotations


class PrintApplicationError(RuntimeError):
    """라우터가 HTTP 응답으로 변환할 수 있는 출력 유즈케이스 오류다."""


class InvalidPrintDocumentError(PrintApplicationError):
    """업로드 파일을 유효한 PDF 문서로 읽을 수 없음을 나타낸다."""


class PrintFileStorageError(PrintApplicationError):
    """업로드 PDF를 작업 디렉터리에 안전하게 저장하지 못했음을 나타낸다."""


class PrintConversionFailedError(PrintApplicationError):
    """PDF를 프린터용 PRN 파일로 변환하지 못했음을 나타낸다."""


class PrintDataUploadError(PrintApplicationError):
    """생성된 PRN 파일을 원격 출력 서버에 업로드하지 못했음을 나타낸다."""


class PrintDocumentRegistrationError(PrintApplicationError):
    """원격 출력 서버에 문서 메타데이터를 등록하지 못했음을 나타낸다."""
