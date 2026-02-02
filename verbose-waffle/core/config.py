from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PrintConfig:
    """프린트 처리에 필요한 설정을 모아둔 구성 값이다."""

    temp_dir: Path = Path("temp")
    output_dir: Path = Path("/root")
    ppd_path: Path = Path("CNRCUPSIRADV45453ZK.ppd")
    upload_bin_url: str = "http://218.145.52.6:8080/spbs/upload_bin"
    register_doc_url: str = "http://u-printon.canon-bs.co.kr:62301/nologin/regist_doc/"
    franchise_id: int = 28


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
