from __future__ import annotations

import pprint
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.dependencies import get_ssv_verifier
from core.ssv import AdmobSsvVerifier

router = APIRouter()


@router.get("/admob/ssv")
async def admob_ssv_callback(
    request: Request,
    verifier: AdmobSsvVerifier = Depends(get_ssv_verifier),
):
    """AdMob SSV 콜백을 검증하고 결과를 출력한다.

    모바일 SSV 설정에 아래 파라미터가 포함되도록 구성한다.
    - ad_network
    - ad_unit
    - custom_data
    - key_id
    - reward_amount
    - reward_item
    - signature
    - timestamp
    - transaction_id
    - user_id
    """

    raw_query = request.url.query
    params = parse_qs(raw_query, keep_blank_values=True)
    verification = verifier.verify(raw_query)

    log_payload = {
        "verified": verification.is_verified,
        "key_id": verification.key_id,
        "reason": verification.reason,
        "raw_query": raw_query,
        "params": {key: value if len(value) > 1 else value[0] for key, value in params.items()},
    }
    print("[AdMob SSV]", pprint.pformat(log_payload, width=120))

    if not verification.is_verified:
        return JSONResponse(status_code=400, content={"status": "invalid", "reason": verification.reason})

    return JSONResponse(status_code=200, content={"status": "ok"})
