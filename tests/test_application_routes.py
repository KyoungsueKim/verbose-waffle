from __future__ import annotations

import asyncio
import unittest

import httpx

from main import create_app


class ApplicationRouteExposureTest(unittest.TestCase):
    """운영 API가 문서 메타데이터를 노출하지 않는지 검증한다."""

    @classmethod
    def setUpClass(cls) -> None:
        """실제 애플리케이션 조립 결과를 준비한다."""

        cls.app = create_app()

    async def _get(self, *paths: str) -> list[httpx.Response]:
        """ASGI 경계에서 각 경로의 실제 HTTP 응답을 반환한다."""

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return [await client.get(path) for path in paths]

    def test_openapi_and_interactive_docs_are_not_routed(self) -> None:
        """OpenAPI 스키마와 대화형 문서 경로는 모두 404여야 한다."""

        paths = ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect")
        responses = asyncio.run(self._get(*paths))

        for path, response in zip(paths, responses, strict=True):
            with self.subTest(path=path):
                self.assertEqual(response.status_code, 404)

    def test_health_endpoint_returns_no_content(self) -> None:
        """Docker healthcheck용 경로는 민감한 본문 없이 204를 반환해야 한다."""

        response = asyncio.run(self._get("/healthz"))[0]

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")


if __name__ == "__main__":
    unittest.main()
