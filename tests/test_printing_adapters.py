from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.config import PrintConfig
from core.printing.errors import PrintDataUploadError, PrintDocumentRegistrationError
from core.printing.files import LocalJobFileStore
from core.printing.gateway import RequestsPrintServerGateway
from core.printing.models import PaperSize


class FailingReadStream:
    """일부 바이트를 반환한 뒤 읽기 오류를 일으키는 업로드 테스트 대역이다."""

    def __init__(self) -> None:
        self._reads = 0

    def read(self, size: int = -1) -> bytes:
        self._reads += 1
        if self._reads == 1:
            return b"partial"
        raise OSError("synthetic read failure")


class LocalJobFileStoreTest(unittest.TestCase):
    """부분 업로드가 작업 디렉터리에 남지 않는지 검증한다."""

    def test_partial_save_failure_removes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PrintConfig(temp_dir=Path(temp_dir), output_dir=Path(temp_dir))
            store = LocalJobFileStore(config)

            with self.assertRaisesRegex(OSError, "synthetic read failure"):
                store.save_upload("JOB", FailingReadStream())

            self.assertFalse((Path(temp_dir) / "JOB.pdf").exists())


class RequestsPrintServerGatewayTest(unittest.TestCase):
    """원격 연동 timeout, HTTP 상태 검증, 용지 payload를 검증한다."""

    def test_upload_uses_configured_timeout_and_rejects_http_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prn_path = Path(temp_dir) / "JOB.prn"
            prn_path.write_bytes(b"prn")
            response = Mock(status_code=500)
            response.raise_for_status.side_effect = RuntimeError("HTTP 500")
            post = Mock(return_value=response)
            config = PrintConfig(
                http_connect_timeout_seconds=2,
                http_read_timeout_seconds=9,
            )
            gateway = RequestsPrintServerGateway(config, post=post)

            with self.assertRaisesRegex(PrintDataUploadError, "HTTP 500"):
                gateway.upload_print_file(prn_path)

            self.assertEqual(post.call_args.kwargs["timeout"], (2, 9))
            response.raise_for_status.assert_called_once_with()

    def test_registration_uses_same_a3_media_and_checks_status(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        post = Mock(return_value=response)
        gateway = RequestsPrintServerGateway(
            PrintConfig(),
            post=post,
            random_octet=lambda start, stop: start,
        )

        result = gateway.register_document(
            "JOB-ID",
            "synthetic.pdf",
            "01000000000",
            4,
            PaperSize.A3,
        )

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["docs"][0]["pages"][0]["size"], "A3")
        self.assertEqual(payload["docs"][0]["pages"][0]["cnt"], 4)
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result, {"status_code": 200})

    def test_registration_network_failure_has_distinct_error_type(self) -> None:
        gateway = RequestsPrintServerGateway(
            PrintConfig(),
            post=Mock(side_effect=TimeoutError("network timeout")),
        )

        with self.assertRaisesRegex(
            PrintDocumentRegistrationError, "network timeout"
        ):
            gateway.register_document(
                "JOB-ID",
                "synthetic.pdf",
                "01000000000",
                1,
                PaperSize.A4,
            )


if __name__ == "__main__":
    unittest.main()
