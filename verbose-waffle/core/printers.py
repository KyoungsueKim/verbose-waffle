from __future__ import annotations

import hashlib
import random
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import PyPDF2
import requests
from fastapi import UploadFile
from fastapi.exceptions import HTTPException
from requests import Response

from core.config import PrintConfig

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(frozen=True)
class PrintJobResult:
    """프린트 처리 결과를 담는 값 객체다."""

    phone_number: str
    file_name: str
    page_count: int
    is_a3: bool


class PrintJobService:
    """업로드된 PDF를 프린트 서버로 전송하는 기능을 담당한다."""

    def __init__(self, config: PrintConfig | None = None) -> None:
        self._config = config or PrintConfig()

    def process_upload(self, upload_file: UploadFile, phone_number: str, is_a3: bool) -> PrintJobResult:
        """업로드된 PDF 파일을 처리하고 프린트 등록까지 완료한다."""

        job_id = self._create_job_id()
        self._ensure_temp_dir()

        pdf_path = self._save_upload(job_id, upload_file)
        page_count = self._get_page_count(pdf_path)

        data_result = self._send_print_data(job_id)
        register_result = self._send_register_doc(job_id, upload_file.filename, phone_number, page_count, is_a3)
        self._cleanup_job_files(job_id)

        print(
            "[Print Job]",
            {
                "file_name": upload_file.filename,
                "page_count": page_count,
                "is_a3": is_a3,
                "phone_number": phone_number,
                "data_result": self._safe_response_json(data_result),
                "register_result": self._safe_response_json(register_result),
            },
        )

        return PrintJobResult(
            phone_number=phone_number,
            file_name=upload_file.filename,
            page_count=page_count,
            is_a3=is_a3,
        )

    def _create_job_id(self) -> str:
        """프린트 작업 식별자를 생성한다."""

        uuid_base = f"{time.time():.6f}".encode("utf-8")
        digest = hashlib.sha1(uuid_base).hexdigest()
        return f"{digest[0:8]}-{digest[9:13]}-{digest[14:18]}-{digest[19:23]}-{digest[24:36]}".upper()

    def _ensure_temp_dir(self) -> None:
        """임시 파일 저장용 디렉터리를 준비한다."""

        self._config.temp_dir.mkdir(parents=True, exist_ok=True)

    def _save_upload(self, job_id: str, upload_file: UploadFile) -> Path:
        """업로드된 파일을 임시 디렉터리에 저장한다."""

        pdf_path = self._config.temp_dir / f"{job_id}.pdf"
        with pdf_path.open("wb") as file_obj:
            file_obj.write(upload_file.file.read())
        return pdf_path

    def _get_page_count(self, pdf_path: Path) -> int:
        """PDF 페이지 수를 계산한다."""

        with pdf_path.open("rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return len(pdf_reader.pages)

    def _print_to_file(self, job_id: str) -> Optional[Path]:
        """CUPS 가상 프린터를 이용해 PRN 파일을 생성한다."""

        processing_time = 0
        output_path = self._config.output_dir / f"{job_id}.prn"
        try:
            subprocess.check_call(
                [
                    "lpadmin",
                    "-p",
                    job_id,
                    "-v",
                    f"file://{output_path}",
                    "-E",
                    "-m",
                    str(self._config.ppd_path),
                ]
            )
            subprocess.check_call(["lpr", "-P", job_id, "-o", "ColorModel=KGray", str(self._config.temp_dir / f"{job_id}.pdf")])

            while True:
                if b"idle" in subprocess.check_output(["lpstat", "-p", job_id], timeout=180):
                    break
                time.sleep(1)
                processing_time += 1

            subprocess.check_call(["lpadmin", "-x", job_id])
            print(f"[DEBUG] PDF file {job_id}.pdf is processed with {processing_time} seconds.")
            return output_path if output_path.is_file() else None
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Failed converting pdf files to PRN binary files. Detail: {exc}",
            )

    def _send_print_data(self, job_id: str) -> Response:
        """PRN 파일을 업로드 서버로 전송한다."""

        try:
            prn_path = self._print_to_file(job_id)
            if prn_path is None:
                raise HTTPException(status_code=500, detail="Failed converting pdf files to PRN binary files.")

            file_name = prn_path.name
            headers = {
                "Content-Type": "application/X-binary; charset=utf-8",
                "User-Agent": None,
                "Content-Disposition": f"attachment; filename={file_name}",
                "Expect": "100-continue",
            }
            with prn_path.open("rb") as data:
                response = requests.post(
                    url=self._config.upload_bin_url,
                    headers=headers,
                    data=data,
                    verify=False,
                )
            return response
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Failed posting PRN binary data into the origin server. Exception: {exc}",
            )

    def _send_register_doc(self, job_id: str, doc_name: str, phone_number: str, cnt: int, is_a3: bool) -> Response:
        """등록 서버에 프린트 문서 정보를 등록한다."""

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
                    "doc_name": doc_name,
                    "queue_id": job_id,
                    "pc_ip": f"192.168.{random.randrange(0, 25)}.{random.randrange(0, 255)}",
                    "pages": [
                        {
                            "size": "A3" if is_a3 else "A4",
                            "color": 0,
                            "cnt": cnt,
                        }
                    ],
                }
            ],
        }
        return requests.post(
            url=self._config.register_doc_url,
            headers=headers,
            json=payload,
            verify=False,
        )

    def _cleanup_job_files(self, job_id: str) -> None:
        """임시 PDF/PRN 파일을 정리한다."""

        prn_path = self._config.output_dir / f"{job_id}.prn"
        pdf_path = self._config.temp_dir / f"{job_id}.pdf"
        if prn_path.exists():
            prn_path.unlink()
        if pdf_path.exists():
            pdf_path.unlink()

    @staticmethod
    def _safe_response_json(response: Response | None) -> dict | None:
        """응답이 JSON일 때만 안전하게 파싱한다."""

        if response is None:
            return None
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code}
