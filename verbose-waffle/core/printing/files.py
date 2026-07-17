from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from core.config import PrintConfig


class LocalJobFileStore:
    """업로드 PDF와 생성 PRN의 로컬 파일 수명주기를 관리한다."""

    def __init__(self, config: PrintConfig) -> None:
        self._config = config

    def save_upload(self, job_id: str, source: BinaryIO) -> Path:
        """업로드 스트림을 작업별 PDF로 저장하고 부분 저장 실패를 정리한다."""

        self._config.temp_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = self._config.temp_dir / f"{job_id}.pdf"
        try:
            with pdf_path.open("wb") as output_file:
                shutil.copyfileobj(source, output_file)
        except Exception:
            pdf_path.unlink(missing_ok=True)
            raise
        return pdf_path

    def cleanup(self, job_id: str) -> None:
        """설정된 입출력 디렉터리에서 해당 작업 파일만 삭제한다."""

        (self._config.output_dir / f"{job_id}.prn").unlink(missing_ok=True)
        (self._config.temp_dir / f"{job_id}.pdf").unlink(missing_ok=True)
