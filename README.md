# verbose-waffle (서버 컨테이너)

(26. 02. 07. 업데이트) 
<img width="1125" height="1082" alt="image" src="https://github.com/user-attachments/assets/c6c3c502-f649-4f0c-bcac-9e888b344b74" />

감사하게도 많은 분들께서 관심을 가져주시고 사용해주신 덕분에,  
2022년 09월 14일 앱을 처음 선보인 이래로 총 **4,823건의 누적 다운로드**, **99,524건의 App Store 노출**, **6,122건의 앱 페이지 조회**, 그리고 **활성 기기당 세션 비율 3.69**라는 의미 있는 지표를 기록하고 있습니다.

부족한 점이 많음에도 꾸준히 사용해주신 사용자 여러분 덕분에 개발자로서 한 단계 더 성장할 수 있었습니다.  
앞으로도 초심을 잃지 않고, 지속적인 개선과 안정적인 운영을 통해 더 나은 앱을 만들어 나가겠습니다. 감사합니다.

김경수 드림. 

--------------------

캠퍼스 프린터기를 사용할 때 드라이버가 윈도우밖에 없어서 아이패드를 주로 쓰는 사람들은 꼭 윈도우 노트북을 켜야 하더라구요. 그게 너무 불편해서 하나 만들었습니다. 짜잔.

![image](https://user-images.githubusercontent.com/61102713/198853397-d98c747d-2dae-4756-8cc5-3d0015dc8b41.png)
![image](https://user-images.githubusercontent.com/61102713/198852430-17e54f35-a841-4abb-b39f-97ae98f1d873.png)

* 이 저장소는 클라이언트 앱이 정상적으로 작동하기 위해 필요한 Docker 컨테이너형 서버입니다.
* 클라이언트 앱에서 PDF와 출력 옵션을 받아 CUPS/Canon UFR II 필터 체인으로 PRN을 만들고, 캠퍼스 프린트 서버에 전송·등록합니다.
* A4 출력에는 `media=A4`와 `print-scaling=auto-fit`을 명시합니다. A4 용지보다 큰 페이지는 인쇄 가능 영역 안으로 비율을 유지한 채 축소하고, A4 이하 페이지는 불필요하게 확대하지 않습니다. A3 선택 요청은 동일한 정책으로 A3 용지를 사용합니다.
* 이 기능의 해결 범위는 **A4를 초과하는 페이지의 잘림**입니다. 정확히 A4인 full-bleed 문서는 `auto-fit`이 축소하지 않을 수 있으므로 Canon PPD의 약 5 mm 비인쇄 여백에 있던 내용은 기존처럼 잘릴 수 있습니다.
* 클라이언트 소스코드는 [super-parakeet](https://github.com/KyoungsueKim/super-parakeet)에 있습니다.
* Dockerfile을 이용해 컨테이너를 빌드해야 하므로 Docker와 CUPS에 대한 기본 지식이 필요합니다.
* 현재 저장소에는 `.github/workflows` 등 자동 CI/CD 정의가 없습니다. Git push만으로 빌드·배포되지 않으며, 아래 검증과 [운영 SOP](docs/sop/a4-auto-fit.md)를 운영자가 수동으로 수행해야 합니다.

![image](https://user-images.githubusercontent.com/61102713/198852909-05a20ce6-ae55-4b5b-8b91-0d46f9917fb4.png)
<img width="976" alt="image" src="https://user-images.githubusercontent.com/61102713/198852863-2352fd2f-10ba-431f-a570-adbff70aa2da.png">
* 캠퍼스 친구들이 이 서비스를 쓰긴 쓰는데 앱 광고를 잘 안눌러줘서 적자입니다 ㅜㅜ 광고가 많이 눌러지길 간절히 바래봅니다 .. 

## 빠른 시작

Windows PowerShell과 Docker Desktop을 기준으로 합니다.

```powershell
git clone https://github.com/KyoungsueKim/verbose-waffle
Set-Location verbose-waffle
Copy-Item .env.example .env
```

`.env`를 텍스트 편집기로 열어 캠퍼스 연동 주소와 출력 정책을 운영 환경에 맞게 확인합니다. `.env`에는 운영 정보가 포함될 수 있으므로 커밋하거나 메신저·이슈에 첨부하지 않습니다. 기본 자동 맞춤 설정은 다음과 같습니다.

```dotenv
PRINT_CUPS_MEDIA_A4=A4
PRINT_CUPS_MEDIA_A3=A3
PRINT_CUPS_SCALING=auto-fit
PRINT_LOG_PHONE_NUMBER=true
PRINT_LOG_FILE_NAME=true
PRINT_HEALTHCHECK_DISABLED=true
```

기본 `PRINT_TEMP_HOST_DIR=./temp`는 프로젝트 로컬 디렉터리를 `/temp`에 바인드하므로 CIFS나 특정 호스트 경로를 요구하지 않습니다. 이미 마운트되어 있어야 하는 외부 저장소를 사용할 때만 로컬 `.env`에서 절대 경로를 지정하고 `PRINT_TEMP_BIND_CREATE_HOST_PATH=false`로 두어, mount가 빠졌을 때 빈 로컬 디렉터리를 대신 생성하지 않도록 합니다. `PRINT_OUTPUT_DIR=/temp`로 설정하면 보존된 PDF와 PRN이 같은 호스트 작업 디렉터리에 남습니다. 이 호스트 측 변수들은 애플리케이션 설정이 아니라 Compose bind 설정입니다.

이미지를 빌드하고 서버를 시작합니다. 파일 수신 포트는 `64550`입니다.

```powershell
docker compose build
docker compose up -d --force-recreate --no-build
docker compose ps
docker compose logs --tail 200 verbose-waffle
```

기본 Compose는 검증된 이미지 안의 애플리케이션 코드를 실행하며 호스트 소스를 컨테이너에 덮어쓰지 않습니다. 호스트에서는 `PRINT_TEMP_HOST_DIR`로 선택한 작업 파일 디렉터리만 `/temp`에 바인드합니다. 소스를 수정했으면 반드시 이미지를 다시 빌드해야 하며, 이 경계 덕분에 이전 이미지 태그로 되돌리는 롤백이 실제 코드 롤백이 됩니다.

운영 서버는 API 구조 노출을 줄이기 위해 `/openapi.json`, `/docs`, `/redoc`을 라우팅하지 않습니다. `GET /healthz`는 응답 본문 없이 HTTP 204를 반환하지만, 반복 access log를 피하기 위해 기본 Compose의 주기적 healthcheck는 `PRINT_HEALTHCHECK_DISABLED=true`로 꺼져 있습니다. 필요할 때 이 값을 `false`로 바꾸면 Docker가 `/healthz`와 CUPS scheduler를 함께 검사합니다.

완료 로그는 장애 추적을 위해 기본적으로 전화번호와 원본 PDF 파일명을 포함합니다. 각각 `PRINT_LOG_PHONE_NUMBER=false`, `PRINT_LOG_FILE_NAME=false`로 즉시 제외할 수 있습니다. 이 로그는 개인정보이므로 접근을 통제하고 외부 공유 전에 전화번호·파일명·작업 ID를 제거합니다.

전체 환경변수와 허용값은 [.env.example](.env.example), 배포·실물 인쇄·장애 대응 절차는 [A4 자동 맞춤 운영 SOP](docs/sop/a4-auto-fit.md)를 따릅니다.

## 검증

이미지 안의 Python 의존성을 그대로 사용하되, 테스트 디렉터리는 읽기 전용으로 마운트합니다. 기본 테스트에서는 실제 캠퍼스 서버로 요청하지 않으며 CUPS 통합 테스트는 건너뜁니다.

```powershell
docker compose run --rm --no-deps `
  --volume "${PWD}\tests:/opt/project/tests:ro" `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle:/opt/project" `
  verbose-waffle `
  python -m unittest discover -s /opt/project/tests -v
```

실제 Canon PPD와 CUPS 필터를 쓰는 통합 테스트는 별도로 실행합니다. A3 세로·가로, 정확한 A4, A5, 혼합 크기 PDF를 `pdftopdf`로 변환해 모든 출력 페이지가 A4인지와 네 모서리 표식이 남는지를 렌더링으로 검사하고, Canon UFR II PRN 생성도 확인합니다. 이 테스트 역시 캠퍼스 업로드/등록 서버를 호출하지 않습니다.

```powershell
docker compose run --rm --no-deps `
  --volume "${PWD}\tests:/opt/project/tests:ro" `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle:/opt/project" `
  --env "RUN_CUPS_INTEGRATION=1" `
  verbose-waffle `
  python -m unittest tests.test_cups_integration -v
```

통합 테스트는 PDF geometry와 렌더 표식까지 확인하지만 실제 프린터의 급지·드라이버·기계 여백을 모두 대신하지는 않습니다. ‘내용이 잘리지 않는다’는 최종 판정은 [SOP의 합성 PDF 실물 검수 절차](docs/sop/a4-auto-fit.md#physical-acceptance)를 반드시 통과해야 합니다.

## 사용 흐름과 문서

iOS 클라이언트 앱이 PDF를 `/upload_file/`로 전송하면 서버가 PDF 페이지 수를 검사하고, 요청별 CUPS 파일 큐에서 PRN으로 변환한 뒤 캠퍼스 서버에 전송·등록합니다. 클라이언트의 서버 주소는 `super-parakeet/Service/Requests.swift`에서 운영 서버 주소로 설정합니다.

* [출력 변환 아키텍처](docs/architecture/printing.md): 계층별 책임, CUPS 필터 체인, 용지/배율 정책, 파일·큐 수명주기
* [A4 자동 맞춤 운영 SOP](docs/sop/a4-auto-fit.md): 환경변수, 배포, 검증, 실물 인수, 장애 대응, 개인정보 및 롤백

<img width="929" alt="image" src="https://user-images.githubusercontent.com/61102713/198853336-f24d6409-1c9d-408d-8f6f-bdc56cfa9032.png">


