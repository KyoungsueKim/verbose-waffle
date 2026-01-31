from __future__ import annotations

from dataclasses import dataclass

from core.config import AppAdsConfig


@dataclass(frozen=True)
class AppAdsContentService:
    """app-ads.txt 응답 본문을 생성하는 서비스."""

    config: AppAdsConfig

    def render(self) -> str:
        """app-ads.txt 표준 형식에 맞춰 텍스트를 생성한다."""

        if not self.config.lines:
            return ""
        return "\n".join(self.config.lines) + "\n"
