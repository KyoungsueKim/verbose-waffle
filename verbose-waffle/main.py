import os

import uvicorn
from fastapi import FastAPI

from core.app_ads import AppAdsContentService
from core.config import AdmobSsvConfig, AppAdsConfig, PrintConfig
from core.printers import PrintJobService
from core.routes import admob, app_ads, privacy, print_jobs
from core.ssv import AdmobSsvVerifier


def create_app() -> FastAPI:
    """FastAPI 애플리케이션과 의존성을 구성한다."""

    app = FastAPI()
    app.state.print_service = PrintJobService(PrintConfig())
    app.state.ssv_verifier = AdmobSsvVerifier(AdmobSsvConfig())
    app.state.app_ads_service = AppAdsContentService(AppAdsConfig())

    app.include_router(privacy.router)
    app.include_router(print_jobs.router)
    app.include_router(admob.router)
    app.include_router(app_ads.router)

    return app


app = create_app()


if __name__ == '__main__':
    server_fullchain: str = "/etc/letsencrypt/live/kksoft.kr/fullchain1.pem"
    server_private_key: str = "/etc/letsencrypt/live/kksoft.kr/privkey1.pem"
    # server_fullchain: str = "C:\\Certbot\\archive\\kksoft.kr\\fullchain1.pem"
    # server_private_key: str = "C:\\Certbot\\archive\\kksoft.kr\\privkey1.pem"
    if not os.path.isfile(server_fullchain) or not os.path.isfile(server_private_key):
        print("SSL Certificate file does not exist. Exit the fastapi instance.")
        exit(1)

    os.system('service cups start')
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=64550,
        reload=False,
        ssl_certfile=server_fullchain,
        ssl_keyfile=server_private_key,
    )
