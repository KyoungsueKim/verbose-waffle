# A4 자동 맞춤 배포·검증·장애 대응 SOP

| 항목 | 내용 |
| --- | --- |
| 목적 | A4보다 큰 PDF를 A4 인쇄 가능 영역 안으로 자동 축소해 내용 잘림을 방지하고, 동일한 절차로 안전하게 배포·검증·롤백한다. |
| 적용 범위 | `verbose-waffle`의 `/upload_file/` PDF → CUPS/Canon UFR II PRN → 캠퍼스 업로드·등록 흐름 |
| 기본 정책 | `PRINT_CUPS_MEDIA_A4=A4`, `PRINT_CUPS_SCALING=auto-fit` |
| 최종 품질 게이트 | 단위 테스트, 실제 CUPS 통합 테스트, 합성 PDF 실물 인수 테스트 모두 통과 |
| 관련 설계 | [출력 변환 아키텍처](../architecture/printing.md) |

이 문서는 누가 수행하더라도 같은 결과를 얻기 위한 표준 실행 절차이다. 명령은 저장소 루트에서 Windows PowerShell로 실행한다. Linux 운영자는 경로 표기만 환경에 맞게 바꾸고 단계와 판정 기준은 그대로 유지한다.

## 1. 역할과 승인 책임

| 역할 | 필수 업무 | 완료 증거 |
| --- | --- | --- |
| 변경 개발자 | 변경 범위 검토, 자동 테스트 실행, 알려진 위험 전달 | 테스트 원문 결과, 대상 commit ID |
| 배포 운영자 | `.env` 백업·검증, 이전 이미지 태그, 빌드·재기동, CUPS 상태 확인 | 백업 경로, 이전/신규 이미지 ID, 배포 시각 |
| 실물 인수 담당자 | 합성 PDF를 승인된 시험 계정으로 출력하고 잘림·방향·양면·등록 정보를 판정 | 개인정보가 없는 체크리스트와 실물 사진 |
| 서비스 승인자 | 테스트 증거와 사용자 영향 검토 후 운영 전환 또는 롤백 결정 | 승인/기각 기록 |
| 장애·개인정보 담당자 | 실패 작업의 PDF/PRN/로그 접근 통제, 보존 기간 종료 후 정확한 파일 정리 | 접근·삭제 기록, 민감정보가 제거된 장애 기록 |

한 사람이 여러 역할을 맡을 수 있지만, 배포자가 자신의 추정만으로 실물 인수를 생략하면 안 된다. 실제 프린터에 접근할 수 없는 환경에서는 “배포 완료”가 아니라 “자동 검증 완료, 실물 인수 대기” 상태로 둔다.

## 2. 사전 조건과 중단 기준

### 사전 조건

* 저장소 루트, 대상 commit, 작업 티켓 또는 변경 기록을 확인했다.
* Docker Desktop과 `docker compose`가 실행 가능하다.
* `linux-UFRII-drv-v620-m17n-20.tar.gz`가 Docker 빌드 컨텍스트에 있다.
* 호스트 포트 `64550`을 사용할 수 있고, 컨테이너에서 승인된 캠퍼스 연동 주소로 통신할 수 있다.
* 운영 `.env`를 읽을 권한과 컨테이너 재기동 권한이 있다.
* 현재 구조는 요청마다 `lpadmin`으로 큐를 만들기 때문에 Compose의 기본 root 실행을 유지한다. non-root 전환은 CUPS 관리 권한을 별도로 설계한 뒤 진행한다.
* 이전 `.env`와 `verbose-waffle:local` 이미지를 복구할 안전한 위치가 있다.
* 합성 시험 문서, 승인된 시험용 클라이언트/계정, A4와 필요 시 A3가 준비된 실제 프린터가 있다.
* `/temp`, `/root`, Docker 저장소에 테스트와 장애 분석에 필요한 여유 공간이 있다.

### 즉시 중단하고 승인자에게 알릴 조건

* 운영 `.env` 또는 이전 이미지를 백업할 수 없다.
* 실제 사용자 PDF나 전화번호를 테스트 자료로 사용해야만 검증할 수 있다.
* 단위 테스트 또는 CUPS 통합 테스트가 한 건이라도 실패한다.
* Canon PPD, `pdftopdf`, `rastertoufr2`, CUPS scheduler 중 하나가 없다.
* 캠퍼스 서버 시험 요청이 과금·실사용 데이터에 영향을 주는데 별도 승인을 받지 못했다.
* 배포 후 기존 A4/A3, 단면/양면 계약이 달라지거나 등록 용지와 CUPS 용지가 불일치한다.

현재 저장소에는 자동 CI/CD가 없다. Git push 성공은 검증이나 배포 성공의 증거가 아니며 이 SOP의 수동 게이트를 모두 수행해야 한다.

## 3. 환경변수 기준표

Compose 배포의 기준값은 `.env.example`과 `docker-compose.yml`이다. `main.py`는 시작 시 `PrintConfig.from_env()`로 값을 읽으며, 형식이 잘못되면 서비스가 정상 기동하지 않는다.

| 변수 | Compose 기본값 | 허용값·운영 규칙 | 효과 | 롤백 기준 |
| --- | --- | --- | --- | --- |
| `PRINT_TEMP_DIR` | `/temp` | 비어 있지 않고 컨테이너가 쓰기 가능한 경로. 운영은 절대 경로 권장 | 업로드 PDF 저장 위치 | 이전 `.env` 값. Compose 표준은 `/temp` |
| `PRINT_OUTPUT_DIR` | `/root` | 비어 있지 않고 컨테이너가 쓰기 가능한 경로 | PRN 출력 위치와 `file:` URI 기준 | 이전 `.env` 값 또는 `/root` |
| `PRINT_CUPS_MODEL` | `CNRCUPSIRADV45453ZK.ppd` | 설치된 PPD 모델 이름. 빈 문자열 금지 | 작업별 CUPS 큐의 Canon 모델 | 직전 검증된 PPD 이름 |
| `PRINT_CUPS_MEDIA_A4` | `A4` | PPD가 지원하는 A4 media 키워드. 빈 문자열 금지 | `is_a3=false` 작업의 `media` | 직전 검증값 또는 `A4` |
| `PRINT_CUPS_MEDIA_A3` | `A3` | PPD가 지원하는 A3 media 키워드. 빈 문자열 금지 | `is_a3=true` 작업의 `media` | 직전 검증값 또는 `A3` |
| `PRINT_CUPS_SCALING` | `auto-fit` | `auto-fit`, `fit`, `none`; `auto_fit`도 파싱되지만 표준 표기 사용 | 페이지 확대·축소 정책 | 우선 직전 검증값. 긴급 기능 중지는 `none`이지만 잘림이 다시 생김 |
| `PRINT_CUPS_JOB_TIMEOUT_SECONDS` | `180` | 유한하고 0보다 큰 초 단위 실수 | 큐 생성, 제출, 완료 확인을 합친 CUPS 작업 전체 deadline | 직전 검증값 또는 `180` |
| `PRINT_CUPS_POLL_INTERVAL_SECONDS` | `1` | 유한하고 0보다 큰 초 단위 실수 | `lpstat -W not-completed` 상태 확인 간격 | 직전 검증값 또는 `1` |
| `PRINT_CUPS_CLEANUP_TIMEOUT_SECONDS` | `10` | 유한하고 0보다 큰 초 단위 실수 | 성공·실패 뒤 `lpadmin -x` 큐 정리에 허용하는 별도 제한 시간 | 직전 검증값 또는 `10` |
| `PRINT_RETAIN_JOB_FILES` | `true` | 참: `1,true,yes,on`; 거짓: `0,false,no,off` | PDF/PRN의 작업 후 보존 여부 | 장애 분석은 승인된 기간만 `true`; 일반 운영 권장값은 `false` |
| `PRINT_HTTP_CONNECT_TIMEOUT_SECONDS` | `10` | 유한하고 0보다 큰 초 단위 실수 | 캠퍼스 서버 연결 대기 제한 | 직전 검증값 또는 `10` |
| `PRINT_HTTP_READ_TIMEOUT_SECONDS` | `60` | 유한하고 0보다 큰 초 단위 실수 | 캠퍼스 서버 응답 읽기 제한 | 직전 검증값 또는 `60` |
| `PRINT_UPLOAD_BIN_URL` | `.env.example`의 현행값 | 코드는 비어 있지 않은지만 검사한다. 운영자는 승인된 HTTP(S) 주소인지 별도 확인 | PRN 바이너리 전송 대상 | 보안 백업에 기록된 직전 주소 |
| `PRINT_REGISTER_DOC_URL` | `.env.example`의 현행값 | 코드는 비어 있지 않은지만 검사한다. 운영자는 승인된 HTTP(S) 주소인지 별도 확인 | 문서·용지·페이지 등록 대상 | 보안 백업에 기록된 직전 주소 |
| `PRINT_FRANCHISE_ID` | `28` | 0보다 큰 정수 | 등록 payload의 프랜차이즈 식별값 | 직전 승인값 |

`PrintConfig()`를 직접 만드는 로컬 단위 테스트는 `PRINT_TEMP_DIR`에 해당하는 기본 경로가 `temp`이다. 실제 서버는 Compose가 `/temp`를 명시하므로 운영 조사에서는 컨테이너의 유효 환경변수와 마운트를 기준으로 판단한다.

배율 모드 선택 기준은 다음과 같다.

* `auto-fit`: 기본값. 선택한 용지보다 큰 페이지만 인쇄 가능 영역 안으로 축소하고, 용지보다 작거나 같은 페이지는 확대하지 않는다.
* `fit`: 모든 페이지를 인쇄 가능 영역에 맞추므로 A5도 확대될 수 있다.
* `none`: 원본 배율을 유지해 대형 페이지가 다시 잘릴 수 있다. 긴급 롤백 외에는 사용하지 않는다.
* `fill`, `auto`: 잘림 없는 계약을 보장하지 않으므로 애플리케이션 허용값이 아니다.

## 4. 1단계: 변경 대상과 복구 지점 확보

1. 현재 상태를 기록한다.

   ```powershell
   git status --short
   git rev-parse HEAD
   docker compose ps
   ```

2. `.env`의 최초 존재 여부를 기록하고, 존재할 때만 저장소 밖의 접근 통제된 임시 위치에 백업한다. 출력된 상태와 경로만 변경 기록에 남기고 파일 내용은 붙여넣지 않는다.

   ```powershell
   $deployStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
   $envOriginallyExisted = Test-Path -LiteralPath .env -PathType Leaf
   $envBackupPath = $null
   if ($envOriginallyExisted) {
     $envBackupPath = Join-Path $env:TEMP "verbose-waffle-env-$deployStamp.backup"
     Copy-Item -LiteralPath .env -Destination $envBackupPath
     if (-not (Test-Path -LiteralPath $envBackupPath -PathType Leaf)) {
       throw "The .env backup was not created. Stop the deployment."
     }
   }
   "EnvOriginallyExisted=$envOriginallyExisted"
   if ($envBackupPath) { "EnvBackupPath=$envBackupPath" } else { "EnvBackupPath=<none>" }
   ```

3. 기존 로컬 이미지가 있으면 새 빌드 전에 태그를 붙인다. 이미지가 없으면 전체 이미지 롤백이 불가능하므로 그 사실을 기록하고, 장애 시 서비스를 중지한 뒤 별도로 승인된 이미지를 배포하는 복구안을 승인자와 확정한다.

   ```powershell
   $rollbackImage = "verbose-waffle:rollback-$deployStamp"
   docker image inspect verbose-waffle:local *> $null
   $previousImageExists = $LASTEXITCODE -eq 0
   if ($previousImageExists) {
     docker tag verbose-waffle:local $rollbackImage
     if ($LASTEXITCODE -ne 0) { throw "Failed to create the rollback image tag." }
     $rollbackImageId = docker image inspect $rollbackImage --format '{{.Id}}'
     "RollbackImage=$rollbackImage"
     "RollbackImageId=$rollbackImageId"
   } else {
     $rollbackImage = $null
     $rollbackImageId = $null
     "RollbackImage=<none>"
     "RollbackImageId=<none>"
   }
   ```

4. 롤백 승인자, 허용 중단 시간, 실물 인수 담당자를 배포 전에 확정한다.

## 5. 2단계: 설정 작성과 정적 검증

1. `.env`가 없을 때만 예시 파일을 복사한다.

   ```powershell
   if (-not (Test-Path -LiteralPath .env)) {
     Copy-Item -LiteralPath .env.example -Destination .env
   }
   ```

2. 텍스트 편집기로 `.env`를 열어 3절 표와 승인된 운영값을 대조한다. 자동 맞춤 기본값은 다음 세 줄이다.

   ```dotenv
   PRINT_CUPS_MEDIA_A4=A4
   PRINT_CUPS_MEDIA_A3=A3
   PRINT_CUPS_SCALING=auto-fit
   ```

3. Compose 문법을 값 출력 없이 검사한다.

   ```powershell
   docker compose config --quiet
   ```

   구버전 Compose가 `--quiet`을 지원하지 않으면 `docker compose config`를 로컬 터미널에서만 실행한다. 그 출력에는 연동 주소 등 운영 설정이 포함될 수 있으므로 공유하지 않는다.

4. `PrintConfig`의 실행 검증은 최신 의존성이 들어간 이미지를 만든 직후 6.1절에서 수행한다. 최초 배포에서 아직 이미지가 없는데 이전 이미지에 기대어 설정을 검사하지 않는다.

## 6. 3단계: 이미지 빌드와 자동 검증

### 6.1 이미지 빌드

```powershell
docker compose build
docker image inspect verbose-waffle:local --format '{{.Id}}'
```

빌드 중 `pdftopdf`, `rastertoufr2`, Canon PPD, Canon 라이브러리를 검사한다. 하나라도 없으면 Dockerfile 단계가 실패해야 정상이다. 설치 실패를 무시하거나 Dockerfile의 검사를 제거하지 않는다.

기본 Compose는 이미지의 `/opt/project/verbose-waffle` 코드를 그대로 실행해야 한다. `docker-compose.yml`의 `volumes`에는 운영 데이터용 `./temp:/temp`만 있고 `./verbose-waffle:/opt/project/verbose-waffle` 같은 소스 bind mount가 없어야 한다. 소스 mount가 있으면 검증한 이미지와 실제 코드가 달라지고 이미지 태그 롤백도 성립하지 않으므로 배포를 중단한다.

최신 이미지와 현재 `.env`를 함께 사용해 애플리케이션의 시작 시 설정 검증을 실행한다. entrypoint는 이 명령 전에도 CUPS 시작/readiness를 검사한다.

```powershell
docker compose run --rm --no-deps `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle" `
  verbose-waffle `
  python -c "from core.config import PrintConfig; PrintConfig.from_env(); print('PRINT_CONFIG_OK')"
```

판정 기준은 명령 종료 코드 0과 `PRINT_CONFIG_OK`이다. 환경변수 이름이 포함된 `ValueError`가 나오면 임의 값을 넣지 말고 해당 변수만 표에 맞게 수정한다.

### 6.2 단위 테스트

테스트는 실제 캠퍼스 업로드·등록 서버를 호출하지 않는다. 이미지에 테스트를 포함하지 않으므로 호스트 테스트 디렉터리를 읽기 전용으로 마운트한다.

```powershell
docker compose run --rm --no-deps `
  --volume "${PWD}\tests:/opt/project/tests:ro" `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle:/opt/project" `
  verbose-waffle `
  python -m unittest discover -s /opt/project/tests -v
```

판정 기준은 모든 단위 테스트 성공과 `RUN_CUPS_INTEGRATION`이 없어서 발생한 통합 테스트의 의도된 skip뿐이다. 실패한 테스트를 제외하거나 skip 조건을 넓혀 통과시키지 않는다.

### 6.3 실제 CUPS 통합 테스트

```powershell
docker compose run --rm --no-deps `
  --volume "${PWD}\tests:/opt/project/tests:ro" `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle:/opt/project" `
  --env "RUN_CUPS_INTEGRATION=1" `
  verbose-waffle `
  python -m unittest tests.test_cups_integration -v
```

컨테이너 entrypoint가 이미 CUPS를 fail-fast로 시작하므로 테스트 명령에서 `service cups start`를 다시 호출하지 않는다. 테스트는 다음 두 경계를 실제 구성요소로 검증한다.

* 실제 Canon PPD와 `pdftopdf`: A3 세로·가로, 정확한 A4, A5, A3/A4/A5 혼합 문서를 변환해 페이지 수와 A4 MediaBox를 확인하고, Poppler 렌더에서 네 색 모서리 표식이 남아 있는지 검사한다.
* 실제 CUPS와 Canon `rastertoufr2`: A3 PDF를 A4 `auto-fit` 작업으로 제출해 0바이트보다 큰 PRN이 생성되고 작업별 큐가 제거되는지 확인한다.

외부 캠퍼스 서버와 실제 프린터는 호출하지 않는다. 종료 코드 0과 skip 없는 성공이 필수이다.

## 7. 4단계: 배포와 런타임 점검

1. 새 이미지를 사용해 서비스를 재생성한다.

   ```powershell
   docker compose up -d --force-recreate --no-build
   docker compose ps
   ```

2. `docker-entrypoint.sh`의 CUPS 시작/readiness 실패와 애플리케이션 시작 실패를 확인한다. 애플리케이션은 전화번호를 직접 로그에 남기지 않지만 파일명, 작업 ID, 외부 응답에 개인정보가 포함될 수 있으므로 화면 공유나 티켓 첨부 전에 가린다.

   ```powershell
   docker compose logs --tail 200 verbose-waffle
   docker compose exec verbose-waffle sh -lc 'cat /tmp/cups-start.log'
   docker compose exec verbose-waffle sh -lc 'cat /tmp/cups-readiness.log'
   ```

3. CUPS scheduler, 모델, 필터를 확인한다.

   ```powershell
   docker compose exec verbose-waffle lpstat -r
   docker compose exec verbose-waffle id -u
   docker compose exec verbose-waffle sh -lc 'lpinfo -m | grep -F "$PRINT_CUPS_MODEL"'
   docker compose exec verbose-waffle test -x /usr/lib/cups/filter/pdftopdf
   docker compose exec verbose-waffle test -x /usr/lib/cups/filter/rastertoufr2
   ```

4. 민감하지 않은 출력 정책만 확인한다. 연동 주소와 프랜차이즈 값은 전체 `printenv`로 출력하지 않는다.

   ```powershell
   docker compose exec verbose-waffle printenv PRINT_CUPS_MEDIA_A4
   docker compose exec verbose-waffle printenv PRINT_CUPS_MEDIA_A3
   docker compose exec verbose-waffle printenv PRINT_CUPS_SCALING
   docker compose exec verbose-waffle printenv PRINT_RETAIN_JOB_FILES
   ```

판정 기준은 서비스가 `running (healthy)`, scheduler가 `running`, 현재 구조에서 UID가 `0`, 모델 한 건 이상 조회, 두 필터의 종료 코드 0, 배율 값 `auto-fit`이다. healthcheck는 CUPS scheduler와 `http://127.0.0.1:64550/openapi.json`을 함께 확인한다.

Docker entrypoint를 우회해 `python main.py`나 `uvicorn`을 직접 실행하는 비표준 절차에서는 운영자가 CUPS를 먼저 시작하고 `lpstat -r` 성공을 확인해야 한다. 일반 배포에서는 entrypoint를 우회하지 않는다.

## 8. 5단계: 실물 검수용 합성 PDF 생성

실제 사용자 파일을 복제하지 않고 저장소의 합성 PDF 생성기를 사용한다. 자동 맞춤 fixture에는 테두리, 네 모서리 색상 표식, 중앙 십자가 들어 있다. 양면 fixture에는 Canon 비인쇄 여백보다 안쪽의 테두리, 위쪽을 가리키는 검은 화살표, 앞면 빨강/뒷면 파랑 표식이 들어 있다.

```powershell
New-Item -ItemType Directory -Force -Path .\tmp | Out-Null
docker compose run --rm --no-deps `
  --volume "${PWD}\tests:/opt/project/tests:ro" `
  --volume "${PWD}\scripts:/opt/project/scripts:ro" `
  --volume "${PWD}\tmp:/opt/project/tmp" `
  --env "PYTHONDONTWRITEBYTECODE=1" `
  --env "PYTHONPATH=/opt/project/verbose-waffle:/opt/project" `
  verbose-waffle `
  python /opt/project/scripts/generate_print_fit_fixtures.py
```

`tmp/pdfs`에 다음 파일이 있어야 한다.

* `a3-portrait.pdf`
* `a3-landscape.pdf`
* `exact-a4.pdf`
* `a5-portrait.pdf`
* `mixed-a3-a4-a5.pdf`
* `duplex-a4-safe.pdf`

## 9. 6단계: 시험 작업의 CUPS 증거 확인

평소에는 일반 로그 수준을 유지한다. 작업 옵션을 확인해야 할 때만 짧은 승인 시간 동안 CUPS 디버그 로그를 켠다.

```powershell
docker compose exec verbose-waffle cupsctl --debug-logging
```

합성 PDF 한 건을 시험 클라이언트로 제출한 직후 다음 로그를 확인한다.

```powershell
docker compose exec verbose-waffle sh -lc 'tail -n 300 /var/log/cups/error_log'
docker compose exec verbose-waffle lpstat -p
```

다음을 확인한다.

* 작업 옵션에 의도한 `media=A4`와 `print-scaling=auto-fit`이 전달되었다.
* `-l` 또는 `-o raw`처럼 PDF 필터를 우회하는 옵션이 없다.
* `pdftopdf`, `gstoraster`, `rastertoufr2` 중 구성에 해당하는 필터가 실행되었다.
* 작업별 출력 경로가 다른 요청과 겹치지 않는다.
* 변환 후 작업별 큐가 제거되었다.
* filter/backend 종료 코드가 성공이다.

확인이 끝나면 즉시 디버그 로그를 끈다.

```powershell
docker compose exec verbose-waffle cupsctl --no-debug-logging
```

디버그 로그에도 파일명과 작업 식별자가 포함될 수 있다. 원문 로그를 외부에 공유하지 않는다.

## 10. 7단계: API와 등록 계약 확인

승인된 시험용 클라이언트와 계정만 사용한다. 실제 사용자 전화번호나 문서는 사용하지 않는다.

1. A4 선택 요청에서 CUPS media와 등록 서버의 문서 용지가 모두 A4인지 확인한다.
2. A3 선택 요청에서 둘 다 A3인지 확인한다.
3. 단면, 긴 변 넘김, 짧은 변 넘김을 각각 한 번 확인한다.
4. 지원하지 않는 `is_a3` 또는 `duplex_mode`가 HTTP 400으로 거부되는지 비운영 환경에서 확인한다.
5. 페이지 수와 등록된 매수가 합성 PDF의 실제 페이지 수와 같은지 확인한다.

등록 결과를 기록할 때 전화번호, 작업 ID, 파일 전송 주소는 가린다. 실제 비용이 발생하는 환경이면 승인자가 정한 최소 건수만 실행한다.

<a id="physical-acceptance"></a>

## 11. 8단계: 실물 인쇄 인수 테스트

아래 행렬을 순서대로 수행한다. 각 PDF는 먼저 앱에서 A4 출력을 선택한다. A3 선택 회귀는 별도 행으로 수행한다.

| 시험 파일/설정 | 기대 결과 | 합격 판정 |
| --- | --- | --- |
| `a3-portrait.pdf`, A4 단면 | A3 페이지가 비율 유지 축소됨 | 검은 테두리, 네 색 모서리, 중앙 십자가 모두 보이고 잘림 없음 |
| `a3-landscape.pdf`, A4 단면 | 가로 페이지가 A4에 적절히 배치됨 | 네 모서리와 테두리 모두 보이고 한쪽으로 치우친 잘림 없음 |
| `exact-a4.pdf`, A4 단면 | Bookworm `auto-fit`에서는 원본 A4 배율을 유지할 수 있음 | 배포 전 기준 출력과 비교해 예상 밖 확대·추가 잘림 없음 |
| `a5-portrait.pdf`, A4 단면 | 작은 페이지를 강제로 A4 전체 크기로 확대하지 않음 | A5 크기 의미가 유지되고 잘림 없음 |
| `mixed-a3-a4-a5.pdf`, A4 단면 | A3만 축소하고 A4/A5는 원래 배율 의미를 유지함 | 3쪽 모두 존재하고 A3 네 모서리가 보이며 A4/A5는 단독 기준 출력과 같음 |
| `duplex-a4-safe.pdf`, A4 긴 변 양면 | 2쪽을 긴 변 기준으로 뒤집음 | 왼쪽 긴 변으로 책처럼 넘겼을 때 둘째 면의 검은 화살표가 위를 향하고, 안전 여백 테두리와 앞면 빨강/뒷면 파랑 표식이 모두 보임 |
| `duplex-a4-safe.pdf`, A4 짧은 변 양면 | 2쪽을 짧은 변 기준으로 뒤집음 | 위쪽 짧은 변으로 넘겼을 때 둘째 면의 검은 화살표가 위를 향하고, 안전 여백 테두리와 앞면 빨강/뒷면 파랑 표식이 모두 보임 |
| `a3-portrait.pdf`, A3 단면 | A3 media와 A3 등록값 사용 | A3 용지에 출력되고 등록 정보도 A3 |

실물 사진에는 합성 표식만 포함해야 한다. 시험 계정 화면, 전화번호, 작업 ID, 주변의 사용자 문서는 촬영 전에 제거하거나 가린다.

다음 중 하나라도 발생하면 불합격이다.

* A4로 축소한 A3 세로·가로 페이지의 테두리나 네 모서리 중 하나가 잘림
* 가로 문서가 잘못 회전하거나 지나치게 작아짐
* A5가 의도와 달리 페이지 전체로 확대됨
* 정확한 A4 또는 A5가 배포 전 기준보다 더 잘림
* 혼합 PDF에서 페이지 누락 또는 페이지별 용지 정책 불일치
* CUPS 용지와 캠퍼스 등록 용지 불일치
* 양면 fixture의 안전 여백 표식이 잘리거나 요청한 넘김 축으로 넘겼을 때 둘째 면 화살표가 거꾸로 보임

불합격 시 추가 사용자 요청을 중지하고 16절의 롤백 절차를 따른다.

## 12. 9단계: 배포 완료와 보존 정책 확정

다음 항목이 모두 충족되어야 완료로 판정한다.

* 단위 테스트 전체 성공
* 실제 CUPS 통합 테스트 성공
* 런타임 CUPS/필터/모델 검사 성공
* 실물 인수 행렬 전체 성공
* 기존 A3와 양면 계약 회귀 없음
* 배포 시각, commit, 신규/이전 이미지 ID, 설정 백업 위치, 인수 담당자 기록 완료
* 디버그 로그 비활성화 확인
* 운영 `PRINT_RETAIN_JOB_FILES` 결정과 파일 보존 종료 시각 기록

안정화 관찰 기간이 끝나면 개인정보 최소 보관을 위해 `PRINT_RETAIN_JOB_FILES=false`를 권장한다. `true`가 꼭 필요하면 접근자, 목적, 종료 시각을 명시하고 종료 직후 확인된 파일만 정리한다.

## 13. 로그·파일·코드 조사 경로

| 조사 대상 | 위치/명령 | 포함될 수 있는 민감정보 | 담당 코드 |
| --- | --- | --- | --- |
| 애플리케이션 시작·작업 로그 | `docker compose logs verbose-waffle` | 원본 파일명, 작업 ID, 외부 응답 요약; 응답에 개인정보가 포함될 가능성 | `verbose-waffle/core/printers.py`, `core/printing/gateway.py` |
| CUPS 변환 오류 | 컨테이너 `/var/log/cups/error_log` | 큐/작업 ID, 파일 경로, 옵션 | `verbose-waffle/core/printing/cups.py` |
| CUPS 접근·페이지 로그 | `/var/log/cups/access_log`, `/var/log/cups/page_log` | 작업·사용자 관련 메타데이터 | `cups-files.conf` |
| CUPS 시작·readiness 오류 | `/tmp/cups-start.log`, `/tmp/cups-readiness.log` | 시스템 경로·서비스 오류 | `docker-entrypoint.sh` |
| 컨테이너 health | `docker compose ps`, Docker healthcheck | 서비스 상태 | `Dockerfile`, `docker-compose.yml` |
| 업로드 PDF | 기본 `/temp/<JOB_ID>.pdf`, 호스트 `./temp` | 문서 원문 전체 | `PrintConfig.temp_dir`, `LocalJobFileStore.save_upload()` |
| 생성 PRN | 기본 `/root/<JOB_ID>.prn` | 인쇄 가능한 문서 내용 | `CupsPrintFileConverter` |
| API 파싱 | `verbose-waffle/core/routes/print_jobs.py` | 요청 필드 | `receive_file()` |
| 용지·배율·양면 정책 | `verbose-waffle/core/printing/models.py` | 없음 | `PaperSize`, `PrintScaling`, `DuplexMode` |
| 애플리케이션 오류 분류 | `verbose-waffle/core/printing/errors.py` | 작업 ID가 포함될 수 있음 | 저장·문서·변환·업로드·등록별 오류 |
| 환경변수 검증 | `verbose-waffle/core/config.py`, `.env.example`, `docker-compose.yml` | 연동 주소·운영 식별값 | `PrintConfig.from_env()` |
| CUPS 옵션·큐 수명주기 | `verbose-waffle/core/printing/cups.py` | 작업 ID와 경로 | `CupsPrintOptionsBuilder`, `CupsPrintFileConverter` |
| 작업 파일 저장·정리 | `verbose-waffle/core/printing/files.py` | PDF/PRN 경로와 내용 | `LocalJobFileStore` |
| PRN 업로드·문서 등록 | `verbose-waffle/core/printing/gateway.py` | 전화번호, 문서명, 등록 payload | `RequestsPrintServerGateway` |
| 전체 유즈케이스 순서 | `verbose-waffle/core/printers.py` | 문서명, 작업 ID, 응답 요약 | `PrintJobService` |
| 의존성 조립 | `verbose-waffle/main.py`, `verbose-waffle/core/dependencies.py` | 없음 | `create_app()`, `get_print_service()` |

장애 티켓에는 원문 PDF/PRN, `.env`, 전체 로그를 첨부하지 않는다. 필요한 경우 시간 범위와 증상만 기록하고 전화번호·파일명·작업 ID·주소를 `[REDACTED]`로 치환한다.

## 14. 증상별 진단 순서

| 증상 | 가장 먼저 확인 | 다음 조사 위치 | 조치 |
| --- | --- | --- | --- |
| 시작 즉시 `ValueError` | 오류에 표시된 `PRINT_*` 이름 | `.env` → `docker-compose.yml` → `core/config.py` | 표의 허용값으로 고치고 설정 검증부터 재실행 |
| 컨테이너가 기동하지 않거나 unhealthy | `/tmp/cups-start.log`, `/tmp/cups-readiness.log`, `docker compose logs` | `docker-entrypoint.sh`, Docker/Compose healthcheck | CUPS readiness 또는 API health 원인을 해결하고 entrypoint를 우회하지 않음 |
| 여전히 A3/대형 페이지가 잘림 | 유효 `PRINT_CUPS_SCALING`, CUPS debug 로그의 `media`/`print-scaling` | `core/printing/cups.py`, PPD media 값 | `auto-fit`과 A4 media가 실제 작업에 함께 있는지 확인 |
| 옵션은 맞지만 `pdftopdf`가 실행되지 않음 | 작업 명령의 `-l`, `-o raw`, raw/pass-through 큐 여부 | `core/printing/cups.py`, CUPS filter log | raw 우회를 제거하고 실제 PPD 필터 큐로 통합 테스트 재실행 |
| A5가 A4 전체로 확대됨 | `PRINT_CUPS_SCALING=fit` 여부 | `core/printing/models.py`, `core/config.py` | 요구가 큰 페이지만 축소라면 `auto-fit`으로 복원 |
| `is_a3` 또는 양면 값이 HTTP 400 | 요청 원문과 허용 표기 | `core/routes/print_jobs.py`, `core/printing/models.py` | 조용한 A4 fallback을 기대하지 말고 허용된 불리언/양면 값으로 클라이언트 수정 |
| A4와 A3 등록값이 다름 | 요청의 `is_a3`, 로그의 `paper_size` | `core/printers.py`, `core/printing/models.py`, `core/printing/gateway.py` | CUPS와 등록에 동일한 `PaperSize`가 전달되는지 테스트 |
| 서버 로그에 `CUPS stage '...' failed` | 단계명, 실행 파일, 종료 코드, stderr와 `/var/log/cups/error_log` | `core/printing/cups.py`, `core/printing/errors.py` | `prepare_output`, `create_queue`, `submit_job`, `wait_for_job`, `cleanup_queue` 단계별로 원인 분리 |
| 예상 PRN 파일 없음 | `PRINT_OUTPUT_DIR`, 디스크/권한, backend 종료 코드 | `cups-files.conf`, `core/printing/cups.py` | file device와 정확한 출력 경로 확인 |
| 기존 PRN 경로 재사용 거부 | 같은 작업 ID의 파일 존재 여부 | `core/printing/cups.py`, `core/printing/files.py` | 파일을 덮어쓰지 말고 충돌 원인·UUID 생성·보존 정책 조사 |
| `file:` device URI 거부 | `cups-files.conf`의 `FileDevice Yes` | Dockerfile의 설정 복사와 CUPS 재시작 로그 | 설정을 직접 임시 편집하지 말고 이미지 구성 수정 후 재빌드 |
| 모델을 찾지 못함 | `lpinfo -m`, `PRINT_CUPS_MODEL` | Dockerfile의 Canon 설치·검사 | 설치된 정확한 PPD 이름으로 구성하고 통합 테스트 재실행 |
| 필터 실행 파일 없음 | `test -x` 명령 | Dockerfile의 `cups-filters`와 Canon 설치 단계 | 실패한 이미지를 배포하지 말고 빌드 원인 해결 |
| CUPS 전체 제한 시간 초과 | `lpstat -W not-completed -o <QUEUE_NAME>`, CUPS log, CPU/디스크 | job/poll timeout 환경변수, `core/printing/cups.py` | `<QUEUE_NAME>`은 애플리케이션 작업 ID와 같은 임시 destination이며 `QUEUE-N` request ID가 아님. 원인 없이 제한 시간만 늘리지 말고 정체 단계와 비어 있지 않은 PRN 조건부터 해결 |
| 큐 정리만 시간 초과 | `cleanup_queue` 단계와 남은 큐 | cleanup timeout, `core/printing/cups.py` | 활성 작업 여부를 확인하고 정확한 큐만 수동 제거 |
| 작업 후 큐가 남음 | `lpstat -p`와 해당 요청의 오류 | `CupsPrintFileConverter.convert()`의 `finally` | 활성 작업이 아님을 확인한 정확한 큐만 제거 |
| `/temp` 또는 `/root` 증가 | `PRINT_RETAIN_JOB_FILES`, 파일 시각·작업 ID | `core/printing/files.py::LocalJobFileStore.cleanup` | 승인된 보존 정책 확인 후 정확한 작업 파일만 정리 |
| PRN 생성은 되지만 업로드 실패 | PRN 존재, connect/read timeout, 외부 HTTP 상태 | `core/printing/gateway.py::upload_print_file` | CUPS를 변경하지 말고 업로드 주소·네트워크·상태 코드를 조사 |
| 업로드 후 등록만 실패 | timeout, HTTP 상태, payload의 용지/페이지 | `core/printing/gateway.py::register_document` | 등록 주소·계약을 조사하고 중복 등록 여부 확인 |

수동으로 `printers.conf`, PPD 또는 생성된 PRN을 편집하지 않는다. 재현 가능한 설정점은 `.env`, `docker-compose.yml`, `PrintConfig`, CUPS 어댑터이며 원인 수정 후 전체 자동/실물 검증을 다시 수행한다.

## 15. 개인정보 파일 정리 절차

1. 먼저 자동 정리 설정을 확인한다.

   ```powershell
   docker compose exec verbose-waffle printenv PRINT_RETAIN_JOB_FILES
   ```

2. `true`이면 디렉터리 목록에서 승인된 시간과 작업 ID를 식별한다. 아래 명령은 Compose 기본 경로용이다. 경로 환경변수를 바꿨다면 `printenv PRINT_TEMP_DIR`와 `PRINT_OUTPUT_DIR`로 확인한 정확한 경로를 사용한다. 목록이나 파일 내용을 티켓에 복사하지 않는다.

   ```powershell
   docker compose exec verbose-waffle ls -l /temp
   docker compose exec verbose-waffle ls -l /root
   ```

3. 삭제 전에 작업이 종료되었고 정확한 `<JOB_ID>`가 대상인지 두 사람이 확인한다.
4. 컨테이너의 정확한 두 경로만 삭제한다. `<JOB_ID>`는 검증한 값으로 대체하며 와일드카드를 사용하지 않는다.

   ```powershell
   docker compose exec verbose-waffle rm -- /temp/<JOB_ID>.pdf /root/<JOB_ID>.prn
   ```

5. 파일 부재를 확인하고 삭제 시각과 승인자만 기록한다. 문서명이나 전화번호는 기록하지 않는다.

`rm -rf`, `*`, 전체 `/temp` 또는 `/root` 삭제는 금지한다. CUPS spool이나 다른 작업이 포함될 수 있는 디렉터리를 통째로 지우지 않는다.

## 16. 롤백 절차

### 16.1 배율 기능만 긴급 중지

자동 맞춤 자체가 즉시 장애를 만든다는 근거가 있고 전체 이미지 롤백보다 설정 변경이 안전할 때만 사용한다.

1. `.env`에서 다음 값을 설정한다.

   ```dotenv
   PRINT_CUPS_SCALING=none
   ```

2. 컨테이너를 재생성하고 값을 확인한다.

   ```powershell
   docker compose up -d --force-recreate --no-build
   docker compose exec verbose-waffle printenv PRINT_CUPS_SCALING
   ```

3. `none`은 이전처럼 대형 PDF를 자를 수 있음을 사용자·운영자에게 명시한다. 영구 해결이 아니며 원인 수정 후 `auto-fit`과 전체 인수 테스트로 복귀한다.

### 16.2 이전 설정과 이미지로 전체 롤백

기본 Compose에 애플리케이션 소스 bind mount가 없다는 전제에서만 이미지 태그 롤백이 코드까지 되돌린다. `docker compose config`에 `/opt/project/verbose-waffle` 대상 volume이 보이면 즉시 중단하고 그 mount를 제거한 뒤 다시 검증한다.

1. 4절에서 승인 기록에 남긴 값을 새 PowerShell 세션에 **리터럴 값으로 다시 지정**한다. 아래 예시를 실제 기록값으로 바꾸며, 추측한 태그나 다른 날짜의 백업을 사용하지 않는다.

   ```powershell
   $envOriginallyExisted = $true
   $envBackupPath = 'C:\approved-backup\verbose-waffle-env-YYYYMMDD-HHMMSS.backup'
   $rollbackImage = 'verbose-waffle:rollback-YYYYMMDD-HHMMSS'
   $rollbackImageId = 'sha256:RECORDED_PREVIOUS_IMAGE_ID'
   ```

   최초 `.env`가 없었다는 기록이면 `$envOriginallyExisted = $false`, `$envBackupPath = $null`로 지정한다. `RollbackImage=<none>`으로 기록된 최초 배포라면 이 절차를 계속하지 말고 서비스를 중지한 뒤 승인된 복구 이미지를 확보한다.

2. 복구 대상을 읽기 전용으로 검증한다.

   ```powershell
   if ($envOriginallyExisted -and -not (Test-Path -LiteralPath $envBackupPath -PathType Leaf)) {
     throw "The approved .env backup does not exist. Stop the rollback."
   }
   $actualRollbackImageId = docker image inspect $rollbackImage --format '{{.Id}}'
   if ($LASTEXITCODE -ne 0) { throw "The approved rollback image does not exist." }
   if ($actualRollbackImageId -ne $rollbackImageId) {
     throw "The rollback tag no longer points to the recorded image ID."
   }
   ```

3. 이전 설정 상태를 정확히 복원한다. 최초 `.env`가 있었으면 검증한 백업을 복사하고, 없었으면 이 배포가 만든 루트의 정확한 `.env` 파일만 제거해 Compose 기본값 상태로 되돌린다.

   ```powershell
   if ($envOriginallyExisted) {
     Copy-Item -LiteralPath $envBackupPath -Destination .env -Force
   } elseif (Test-Path -LiteralPath .env -PathType Leaf) {
     Remove-Item -LiteralPath .env -Force
   }
   ```

4. 이전 이미지 태그를 Compose가 참조하는 로컬 태그로 되돌린다.

   ```powershell
   docker tag $rollbackImage verbose-waffle:local
   if ($LASTEXITCODE -ne 0) { throw "Failed to restore the rollback image tag." }
   ```

5. 빌드하지 않고 컨테이너를 재생성한다.

   ```powershell
   docker compose up -d --force-recreate --no-build
   docker compose ps
   docker compose logs --tail 200 verbose-waffle
   ```

6. 7절의 CUPS/필터 점검과 최소 A4/A3/양면 회귀를 다시 수행한다. 롤백도 검증 전에는 완료가 아니다.
7. 롤백 중 남은 큐는 `lpstat -p`로 확인한다. 활성 작업이 아니고 정확한 작업 ID가 확인된 큐만 다음처럼 제거한다.

   ```powershell
   docker compose exec verbose-waffle lpadmin -x <JOB_ID>
   ```

8. 안정화 기간이 끝난 뒤 `.env` 백업 파일과 롤백 이미지를 보존 정책에 따라 정리한다. 운영값이 담긴 백업 파일을 저장소로 옮기지 않는다.

이번 기능은 데이터베이스 스키마를 변경하지 않으므로 별도 데이터 마이그레이션 롤백은 없다. 그러나 이미 외부 캠퍼스 서버에 업로드·등록된 시험 작업은 이미지 롤백으로 취소되지 않으므로 중복 제출 여부를 별도로 확인한다.

## 17. 공식 표준과 명령 참고

* [PWG 5100.13-2023 IPP Driver Replacement Extensions v2.0](https://ftp.pwg.org/pub/pwg/candidates/cs-ippnodriver20-20230301-5100.13.pdf): `print-scaling=auto-fit`의 표준 의미
* [PWG IPP Print Job Template Attributes](https://www.pwg.org/ipp/print.html): `print-scaling`, `media`, `sides` 속성 목록
* [CUPS Command-Line Printing and Options](https://openprinting.github.io/cups/doc/options.html): media, scaling, duplex 작업 옵션
* [CUPS Command-Line Printer Administration](https://openprinting.github.io/cups/doc/admin.html): `cupsctl --debug-logging`과 관리 명령
* [CUPS lpadmin(8)](https://openprinting.github.io/cups/cups-local/lpadmin.html): 큐 생성·삭제
* [CUPS lpstat(1)](https://openprinting.github.io/cups/cups-local/lpstat.html): `-W not-completed -o` 작업 완료 조회
* [CUPS cups-files.conf(5)](https://openprinting.github.io/cups/doc/man-cups-files.conf.html): `FileDevice Yes`의 제약과 보안 경계
* [CUPS Design Description](https://openprinting.github.io/cups/doc/spec-design.html): 필터와 backend 처리 순서
