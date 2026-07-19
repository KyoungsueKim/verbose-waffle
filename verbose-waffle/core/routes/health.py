"""컨테이너 상태 확인 전용 HTTP 라우터."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

router = APIRouter(include_in_schema=False)


@router.get(
    "/healthz",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def healthz() -> Response:
    """애플리케이션 이벤트 루프가 요청을 처리할 수 있음을 본문 없이 알린다."""

    return Response(status_code=status.HTTP_204_NO_CONTENT)
