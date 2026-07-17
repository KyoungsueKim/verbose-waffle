from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
import urllib3

from core.config import PrintConfig
from core.printing.errors import PrintDataUploadError, PrintDocumentRegistrationError
from core.printing.models import PaperSize

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestsPrintServerGateway:
    """아주대 Canon 출력 서버의 바이너리 업로드와 문서 등록을 담당한다."""

    def __init__(
        self,
        config: PrintConfig,
        post: Callable[..., requests.Response] = requests.post,
        random_octet: Callable[[int, int], int] = random.randrange,
    ) -> None:
        self._config = config
        self._post = post
        self._random_octet = random_octet

    def upload_print_file(self, prn_path: Path) -> dict[str, Any] | None:
        """PRN 파일을 바이너리 서버에 업로드하고 HTTP 실패를 명시적으로 거부한다."""

        headers = {
            "Content-Type": "application/X-binary; charset=utf-8",
            "User-Agent": None,
            "Content-Disposition": f"attachment; filename={prn_path.name}",
            "Expect": "100-continue",
        }
        try:
            with prn_path.open("rb") as data:
                response = self._post(
                    url=self._config.upload_bin_url,
                    headers=headers,
                    data=data,
                    verify=False,
                    timeout=self._config.http_timeout,
                )
            response.raise_for_status()
            return _response_summary(response)
        except Exception as exc:  # noqa: BLE001 - 라이브러리 오류를 포트 오류로 통일한다.
            raise PrintDataUploadError(
                f"PRN upload failed for '{prn_path.name}': {exc}"
            ) from exc

    def register_document(
        self,
        job_id: str,
        document_name: str,
        phone_number: str,
        page_count: int,
        paper_size: PaperSize,
    ) -> dict[str, Any] | None:
        """CUPS에서 사용한 용지와 동일한 크기로 문서 메타데이터를 등록한다."""

        file_name = f"{job_id}.prn"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": None,
            "Content-Disposition": f"attachment; filename={file_name}",
            "Expect": "100-continue",
        }
        payload = {
            "nonmember_id": phone_number,
            "franchise": self._config.franchise_id,
            "pc_mac": job_id[-12:],
            "docs": [
                {
                    "doc_name": document_name,
                    "queue_id": job_id,
                    "pc_ip": (
                        f"192.168.{self._random_octet(0, 25)}."
                        f"{self._random_octet(0, 255)}"
                    ),
                    "pages": [
                        {
                            "size": paper_size.value,
                            "color": 0,
                            "cnt": page_count,
                        }
                    ],
                }
            ],
        }
        try:
            response = self._post(
                url=self._config.register_doc_url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=self._config.http_timeout,
            )
            response.raise_for_status()
            return _response_summary(response)
        except Exception as exc:  # noqa: BLE001 - 라이브러리 오류를 포트 오류로 통일한다.
            raise PrintDocumentRegistrationError(
                f"Document registration failed for job '{job_id}': {exc}"
            ) from exc


def _response_summary(response: requests.Response) -> dict[str, Any] | None:
    """응답 본문 대신 민감정보가 없는 HTTP 상태만 반환한다."""

    return {"status_code": response.status_code}
