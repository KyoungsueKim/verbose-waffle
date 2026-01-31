from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Iterable

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.config import AdmobSsvConfig


@dataclass(frozen=True)
class SsvVerificationResult:
    """SSV 검증 결과를 담는 값 객체다."""

    is_verified: bool
    key_id: int | None
    reason: str | None


class AdmobSsvVerifier:
    """AdMob 보상형 SSV 요청의 서명을 검증한다."""

    def __init__(self, config: AdmobSsvConfig | None = None, session: requests.Session | None = None) -> None:
        self._config = config or AdmobSsvConfig()
        self._session = session or requests.Session()
        self._cached_keys: dict[int, bytes] = {}
        self._cache_expires_at: float = 0.0

    def verify(self, raw_query: str) -> SsvVerificationResult:
        """쿼리 문자열을 기반으로 SSV 서명을 검증한다."""

        try:
            data_to_verify, signature_bytes, key_id = self._parse_query(raw_query)
        except ValueError as exc:
            return SsvVerificationResult(is_verified=False, key_id=None, reason=str(exc))

        public_key_bytes = self._get_public_key(key_id)
        if public_key_bytes is None:
            return SsvVerificationResult(is_verified=False, key_id=key_id, reason="key not found")

        try:
            public_key = self._load_public_key(public_key_bytes)
            public_key.verify(signature_bytes, data_to_verify, ec.ECDSA(hashes.SHA256()))
            return SsvVerificationResult(is_verified=True, key_id=key_id, reason=None)
        except InvalidSignature:
            return SsvVerificationResult(is_verified=False, key_id=key_id, reason="invalid signature")
        except Exception as exc:  # noqa: BLE001
            return SsvVerificationResult(is_verified=False, key_id=key_id, reason=f"verify error: {exc}")

    def _parse_query(self, raw_query: str) -> tuple[bytes, bytes, int]:
        """쿼리 문자열에서 검증용 데이터와 서명, 키 ID를 추출한다."""

        signature_marker = "&signature="
        key_id_marker = "&key_id="
        signature_index = raw_query.find(signature_marker)
        key_id_index = raw_query.find(key_id_marker)

        if signature_index < 0 or key_id_index < 0:
            raise ValueError("signature or key_id is missing")
        if signature_index > key_id_index:
            raise ValueError("signature and key_id order is invalid")

        data_to_verify = raw_query[:signature_index]
        signature_value = raw_query[signature_index + len(signature_marker) : key_id_index]
        key_id_value = raw_query[key_id_index + len(key_id_marker) :]

        if not signature_value:
            raise ValueError("signature is empty")
        if not key_id_value:
            raise ValueError("key_id is empty")

        signature_bytes = self._urlsafe_b64decode(signature_value)
        key_id = int(key_id_value)
        return data_to_verify.encode("utf-8"), signature_bytes, key_id

    def _get_public_key(self, key_id: int) -> bytes | None:
        """캐시된 공개키가 없으면 키 서버에서 갱신한다."""

        now = time.time()
        if not self._cached_keys or now >= self._cache_expires_at:
            self._refresh_keys(now)
        return self._cached_keys.get(key_id)

    def _refresh_keys(self, now: float) -> None:
        """키 서버에서 최신 공개키 목록을 받아 캐시에 저장한다."""

        response = self._session.get(self._config.key_server_url, timeout=10)
        response.raise_for_status()
        payload = response.json()

        keys: dict[int, bytes] = {}
        for key_id, key_bytes in self._extract_keys(payload.get("keys", [])):
            keys[key_id] = key_bytes

        self._cached_keys = keys
        self._cache_expires_at = now + self._config.cache_ttl_seconds

    def _extract_keys(self, items: Iterable[dict]) -> Iterable[tuple[int, bytes]]:
        """키 서버 응답에서 keyId와 공개키를 추출한다."""

        for item in items:
            raw_key_id = item.get("keyId") or item.get("key_id")
            if raw_key_id is None:
                continue

            public_key = item.get("publicKey") or item.get("public_key") or item.get("pem")
            if public_key:
                yield int(raw_key_id), public_key.encode("utf-8")
                continue

            public_key_b64 = item.get("base64") or item.get("publicKeyBase64")
            if public_key_b64:
                yield int(raw_key_id), base64.b64decode(public_key_b64)

    @staticmethod
    def _load_public_key(key_bytes: bytes):
        """PEM 또는 DER 형태의 공개키를 로드한다."""

        if key_bytes.strip().startswith(b"-----BEGIN"):
            return serialization.load_pem_public_key(key_bytes)
        return serialization.load_der_public_key(key_bytes)

    @staticmethod
    def _urlsafe_b64decode(value: str) -> bytes:
        """URL-safe Base64 문자열을 바이트로 변환한다."""

        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded)
