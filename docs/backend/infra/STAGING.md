# 스테이징 — 팀원 체험용 서버 (집 PC + Cloudflare Tunnel)

멀리 있는 팀원이 관계자 웹과 Android 앱을 직접 써 보고 피드백하기 위한 서버. 실사용자용이 아니다 — 실사용자 단계는 `DEPLOYMENT.md`(AWS).

| 항목 | 결정 (2026-09-29 사용자 확정) |
|---|---|
| 서버 | 집 PC 1대(i5 10세대 · 16GB) · `docker-compose.staging.yml` 한 파일 |
| 공개 | Cloudflare Tunnel — 공유기 포트 개방 부재 · HTTPS 는 Cloudflare 가 처리. **또는 ngrok**(Docker 확장 · 고정 도메인 — `STAGING.md §4.1` · `Ruling 841`) |
| 웹 | 같은 서버·같은 주소(Vercel 미사용 — 새로 고침 쿠키가 `SameSite=Strict` 라 웹과 API 가 다른 **사이트**가 되면 로그인 유지 불가). 운영은 `Ruling 481` 로 웹만 Vercel 이지만 웹·API 를 같은 사이트의 커스텀 도메인(`app.<도메인>` · `api.<도메인>`)에 두어 `Strict` 가 성립하게 한 것이고(`DEPLOYMENT.md §12.2`), 스테이징은 도메인 1개(`bus.<도메인>`)라 서버 한 곳에 묶음. ngrok 구성(`STAGING.md §4.1`)은 웹을 Vercel `web-dev` 에 둔다 — 새로 고침하거나 15분이 지나면 다시 로그인(감수) |
| 앱 | Android 만 · APK 를 서버의 `/download/` 에 두고 QR 로 설치. iOS 는 제외(원격 설치에 Apple 개발자 등록 필수) |
| 데이터 | 백엔드 `local,staging` 프로파일 — QA Mock 시드(`db/qa-seed` · 경기 부천 학원 3곳 · 계정과 시나리오는 [`docs/qa/QA_SCENARIOS.md`](../../qa/QA_SCENARIOS.md)) + 버스 시뮬레이터. **매일 새벽 시드 상태로 초기화** · 팀원이 웹 머리말 **[테스트 데이터 초기화]** 로 언제든 초기화(`Ruling 364`) |

모든 요청은 `https://bus.<도메인>` → Cloudflare → 집 PC 의 `cloudflared` → `proxy`(nginx) → `/api`·`/ws` 는 backend, `/download` 는 APK 폴더, 나머지는 web.

프록시 설정은 `infra/proxy/nginx.staging.conf` 다(개발용 `nginx.conf` 가 아니다, 2026-09-30 BR-230). 인터넷에 열린 주소라 운영 프록시의 보호를 옮겼다 — ①로그인·가입·복구·자녀 연결 경로는 접속자 IP 당 분당 20회로 제한(초과 `429`) ②**Swagger UI·`/v3/api-docs` 는 공개하지 않는다**(`404` — API 스펙은 로컬 `localhost:8080` 에서 본다) ③Cloudflare 의 `CF-Connecting-IP` 를 사설 대역(터널 컨테이너)에서 온 요청에서만 채택해 감사 로그의 접속 IP 가 터널 주소로 찍히지 않는다. 설정을 고친 뒤 문법은 파일 머리말의 `nginx -t` 한 줄로 확인한다.

---

## 1. 준비물

- 도메인 1개 — **Cloudflare Registrar 에서 사면** 네임서버 변경 단계가 없어진다
- Cloudflare 계정(무료)
- 집 PC 에 Ubuntu Server 24.04 LTS
- NCP(네이버 클라우드) 콘솔 — 지도 키에 새 주소·앱 패키지를 등록해야 한다(§5)

## 2. 집 PC 설치 (1회)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 다시 로그인해야 적용
```

- BIOS 에서 **정전 후 자동 전원 켜기**(AC Power Recovery = On) — 모든 컨테이너가 `restart: unless-stopped` 라 PC 만 켜지면 서버도 돌아온다

## 3. 코드와 비밀값 옮기기

스테이징에 필요한 저장소는 `backend` · `web` 둘이다(compose 가 형제 폴더 `../web` 을 빌드한다) — 같은 폴더 아래 나란히 받는다.

⚠ GitHub 의 `main` 은 push 한 시점까지만 반영돼 있다 — Mac 에서 저장소마다 `git -C <저장소> log origin/main -1` 과 `git -C <저장소> log -1` 을 견줘 확인한다. **둘이 다르면 GitHub 이 아니라 Mac 에서 받는다** — 주소를 `ssh://<mac 사용자>@<mac IP>/Users/mskim/Desktop/PJ/baraeda/<저장소>` 로 바꾸고, Mac 의 시스템 설정 → 일반 → 공유 → "원격 로그인" 을 켠다.

```bash
mkdir baraeda && cd baraeda
git clone https://github.com/Bareda-Organization/backend.git
git clone https://github.com/Bareda-Organization/web.git
cd backend

# git 에 없는 비밀값 파일 2개 (네이버 API 키 · 웹 지도 키)
scp <mac 사용자>@<mac IP>:Desktop/PJ/baraeda/backend/backend/.env backend/.env
scp <mac 사용자>@<mac IP>:Desktop/PJ/baraeda/web/.env.local ../web/.env.local
```

## 4. Cloudflare Tunnel

1. Cloudflare 대시보드 → Zero Trust → Networks → Tunnels → **Create a tunnel** → `cloudflared` 선택
2. 설치 명령 화면에 나오는 **토큰**(`eyJ…`)만 복사한다 — 설치 명령은 실행하지 않는다(compose 가 띄운다)
3. Public Hostname — Subdomain `bus` · Domain `<도메인>` · Service **`HTTP`** · URL **`proxy:80`**

### 4.1 ngrok 으로 대신할 때 (`Ruling 841` · 2026-10-05 사용자 결정)

도메인·Cloudflare 계정 없이 Mac 에서 바로 띄우는 구성이다. 웹은 Vercel `web-dev`, API·앱은 ngrok 고정 도메인(ngrok 대시보드 → Domains, 무료 1개 — 실제 값은 저장소에 적지 않고 `.env` 의 `PUBLIC_URL` 에만 둔다).

1. `.env`(§6) 에서 `COMPOSE_FILE` · `TUNNEL_TOKEN` 줄을 빼고 `COMPOSE_PROFILES=ngrok` · `NGROK_AUTHTOKEN=<ngrok 대시보드 → Your Authtoken>` · `WEB_ORIGIN=https://<web-dev 운영 주소>.vercel.app` 을 쓴다. ngrok 에이전트가 스테이징 compose 의 `ngrok` 컨테이너로 같이 떠서 고정 도메인(`PUBLIC_URL`)을 `proxy:80` 으로 보낸다. `WEB_ORIGIN` 은 허용 출처(CORS · WebSocket)에 웹 주소를 함께 싣는다 — 허용 출처(CORS · WebSocket)에 웹 주소가 함께 실린다. `COMPOSE_FILE` 을 빼는 이유는 같은 폴더의 개발용 compose 명령이 스테이징으로 바뀌지 않게 하려는 것 — 기동은 `docker compose -f docker-compose.staging.yml up -d --build`
2. **Docker Desktop 의 ngrok 확장은 쓰지 않는다** — 공개를 컨테이너 ID 에 묶어 `up --build` 로 프록시가 새로 만들어질 때마다 끊기고, 2026-10-05 에는 스테이징 프록시로 켠 공개가 요청을 프록시까지 전달하지 못해 503(`ERR_NGROK_3004`)만 냈다. 같은 도메인을 두 에이전트가 잡을 수 없으므로 확장의 공개는 꺼 둔다. ⚠ 특히 **개발용 `school-bus-proxy-1`(3000) 은 공개하지 않는다** — 전 계정 비밀번호가 공개된 `password` 이고 Swagger 가 열린다(같은 날 실제로 열렸다가 닫음)
3. Vercel `web-dev` 운영(Production) 환경변수 — `NEXT_PUBLIC_API_BASE_URL` = 고정 도메인 · `NEXT_PUBLIC_TEST_DATA_RESET=true` · `NEXT_PUBLIC_QUICK_LOGIN_PASSWORD` = 시드 공통 비밀번호(로그인 화면의 역할별 빠른 로그인 — `Ruling 877`, 값이 없으면 단추가 안 보인다) → 재배포. `NEXT_PUBLIC_*` 는 빌드 때 화면 코드에 박혀 값만 바꾸면 반영되지 않는다
4. §5 의 Web 서비스 URL 에 Vercel 주소를 등록한다
5. 앱은 §7 의 `API_BASE_URL` 에 `<고정 도메인>/api/v1`

한계
- 웹(`vercel.app`)과 API(`ngrok-free.dev`)가 다른 사이트라 새로 고침 쿠키(`SameSite=Strict` · `Ruling 502`)가 붙지 않는다 — **새로 고침하거나 access 토큰(15분)이 끝나면 다시 로그인.** 쿠키는 완화하지 않는다
- 프록시는 접속자 IP 를 `CF-Connecting-IP` 로만 읽는다 — ngrok 뒤에서는 팀원 전원이 한 IP 로 보여 로그인 제한(분당 20회)을 함께 쓰고 감사 로그의 IP 가 터널 쪽 주소다
- Mac 이 잠자기에 들어가면 서버도 멈춘다

## 5. 네이버 지도 키에 새 주소 등록

NCP 콘솔 → Maps → 애플리케이션 수정. **안 하면 지도가 401 로 막혀 "지도를 불러오지 못했습니다" 만 뜬다.**

- Web 서비스 URL — `https://bus.<도메인>` 추가 (기존 `http://localhost:3000` 은 개발용이라 남긴다)
- Android 앱 패키지 이름 — `com.baraeda.parent_app` · `com.baraeda.manager_app`

## 6. `.env` 작성 후 기동

backend 저장소 루트(`baraeda/backend/.env`, git 무시 대상)에 쓴다.

```bash
# 시드 계정 전부가 쓸 비밀번호의 BCrypt 해시
docker run --rm httpd:2.4-alpine htpasswd -nbBC 10 "" '<팀원에게 알려 줄 비밀번호>' | tr -d ':\n'; echo
openssl rand -hex 32   # JWT_SECRET 용
```

```dotenv
COMPOSE_FILE=docker-compose.staging.yml
PUBLIC_URL=https://bus.<도메인>
# ⚠ 작은따옴표 필수 — 해시 속 `$` 를 compose 가 변수로 읽지 않게 한다
SEED_PASSWORD_HASH='$2y$10$...'
JWT_SECRET=<위 openssl 결과>
# cloudflared 는 이 프로필일 때만 뜬다(ngrok 구성 §4.1 은 ngrok 프로필과 NGROK_AUTHTOKEN 으로 바꾼다)
COMPOSE_PROFILES=cloudflare
TUNNEL_TOKEN=<§4 토큰>
```

```bash
mkdir -p downloads
docker compose up -d --build      # COMPOSE_FILE 덕에 -f 불필요. 첫 빌드 수 분
docker compose ps                 # 6개 전부 running
```

- `PUBLIC_URL` · `SEED_PASSWORD_HASH` · `JWT_SECRET` 중 하나라도 비면 compose 가 기동 전에 멈춘다 — 저장소에 공개된 비밀번호·JWT 키로 뜨는 일을 막는 장치. `TUNNEL_TOKEN` 은 필수가 아니다(비면 `cloudflared` 컨테이너만 실패)
- 확인 — 브라우저에서 `https://bus.<도메인>` 로그인. 계정 ID 는 [`docs/qa/QA_SCENARIOS.md`](../../qa/QA_SCENARIOS.md) §1(QA Mock — 2026-10-03 시드 분리 뒤 옛 `SeedFixtures`(`staffA` 등)는 시험 전용이라 스테이징에 없다), 비밀번호는 위에서 정한 값

## 7. APK 빌드 · 올리기 · QR

Mac 에서 빌드한다(두 앱 모두).

```bash
cd mobile/apps/parent-app        # 매니저 앱은 manager-app (Mac 의 작업 공간 baraeda/ 에서)
flutter build apk --release \
  --dart-define=API_BASE_URL=https://bus.<도메인>/api/v1 \
  --dart-define=NAVER_MAP_CLIENT_ID=<웹 .env.local 과 같은 ID> \
  --dart-define=QUICK_LOGIN_PASSWORD=<시드 공통 비밀번호>   # 역할별 빠른 로그인(Ruling 877) — 운영 빌드에는 넣지 않는다
scp build/app/outputs/flutter-apk/app-release.apk <집 PC>:baraeda/backend/downloads/parent.apk
```

- ⚠ **`/api/v1` 까지 붙인다.** 빠뜨리면 모든 요청이 404
- 크기 — 학부모 125MB · 매니저 132MB(모든 CPU 종류를 한 파일에 담은 크기). 줄이려면 `--split-per-abi` 후 `app-arm64-v8a-release.apk` 만 올린다
- 파일만 바꾸면 되고 서버 재시작은 필요 없다
- **테스트 시나리오** — [`docs/qa/QA_SCENARIOS.md`](../../qa/QA_SCENARIOS.md)(git 추적 · 2026-10-03 옛 `TEST_SCENARIOS.html` 대체). 스테이징 데이터가 그 문서의 부천 QA Mock 이다. 팀원에게는 저장소 링크로 주거나 사람용 렌더를 만들어 이 폴더에 올린다
- **QR** — PC Chrome 에서 `https://bus.<도메인>/download/` 을 열고 주소창의 공유 → **QR 코드 만들기**. 팀원은 찍고 → `parent.apk` 또는 `manager.apk` → "출처를 알 수 없는 앱 설치" 허용 → 설치

## 8. 초기화

시드의 운행 시각이 **초기화 시각 기준**이라 하루가 지나면 버스가 움직이지 않는다. 방법 셋 — 결과는 같다(DB 시드 상태 · 버스 다시 출발).

| 방법 | 누가 | 걸리는 시간 |
|---|---|---|
| 관계자 웹 머리말 **[테스트 데이터 초기화]** | 로그인한 팀원 누구나 | 수 초 · 누른 사람은 로그아웃된다 |
| `docker compose restart backend` | 집 PC 운영자 | 약 20초 접속 불가 |
| 매일 새벽 자동 (아래 cron) | — | 약 20초 |

```bash
crontab -e
0 5 * * * cd $HOME/baraeda/backend && docker compose restart backend
```

- ⚠ **모든 팀원의 데이터가 함께 되돌아간다** — 다른 사람이 테스트 중이면 먼저 알린다
- 초기화 뒤 앱은 다음 토큰 갱신 때 로그인 화면으로 돌아간다(로그인 유지 토큰이 지워지기 때문 — 결함 아님)

## 9. 코드 갱신 · 문제 확인

```bash
git pull && docker compose up -d --build   # PUBLIC_URL 을 바꿨다면 web 까지 다시 빌드된다
docker compose logs -f backend
```

| 증상 | 원인 |
|---|---|
| 지도만 안 뜸(401) | §5 NCP 등록 누락 |
| 웹 로그인 직후 다시 로그인 화면 | `PUBLIC_URL` 과 실제 접속 주소가 다름(쿠키·CORS 둘 다 이 값) |
| 앱이 서버에 못 붙음 | APK 빌드 때 `API_BASE_URL` 의 `https`·`/api/v1` 누락 |
| `bus.<도메인>` 이 502/1033 | `cloudflared` 컨테이너 중지 또는 Public Hostname 의 URL 이 `proxy:80` 이 아님 |
| 요청이 느리거나 실패, 백엔드 로그에 `Connection is not available` | DB 연결 풀(기본 10개)이 마름 — 연결 대기 상한 3초(`connection-timeout`) 뒤 실패. 5초 넘게 연결을 쥔 스레드의 스택이 `leak-detection` 경고로 로그에 남으므로 `docker compose logs backend \| grep -i leak` 로 누가 쥐었는지 찾음 |

## 10. 운영(AWS) 변경 중 스테이징에 해당하지 않는 것 (2026-10-01 R46 확인)

R46 운영 작업(`DEPLOYMENT §7` 백업 · `DEPLOYMENT §11` 관측 · `DEPLOYMENT §12` Vercel · `DEPLOYMENT §13` 운영 규칙)이 이 서버 절차를 바꾸지 않는 근거. `docker-compose.staging.yml` 을 직접 읽은 결과다.

| 운영 변경 | 스테이징 |
|---|---|
| 매시 DB 백업 · 매일 사진 백업 · 복구 연습(`Ruling 480`·`500`) | **해당 없음** — postgres 가 `tmpfs`(메모리)라 디스크에 데이터가 없고 매일 새벽 시드로 초기화하는 서버. 백업 대상이 아님 |
| 경보 수신(텔레그램·이메일, Prometheus·Alertmanager) | **해당 없음** — 컨테이너 6개(postgres · redis · backend · web · proxy · cloudflared)뿐이고 관측·경보 컨테이너가 없음 |
| 첫 메인 관리자 러너(`FirstSystemAdminBootstrap`) | **동작 안 함** — 시드에 메인 관리자(`sysadmin`)가 이미 있어 이 러너는 값을 읽지 않고 건너뜀. 스테이징에는 `BOOTSTRAP_ADMIN_*` 변수를 넣지 않음 |
| 웹 Vercel 배포 · 허용 출처 검사(`infra/scripts/deploy.sh`) | **해당 없음** — 이 검사는 운영 배포 스크립트에만 있음. 스테이징은 `PUBLIC_URL` 한 값이 REST 허용 출처(`CORS_ALLOWED_ORIGINS`)와 WebSocket 허용 출처(`WS_ALLOWED_ORIGIN_PATTERNS`)에 그대로 들어감 |
| prod 프로파일 명시(`b18c60bf`) | **해당 없음** — 스테이징은 `local,staging` 프로파일이고 필수 환경변수는 §6 의 넷 |
| 이미지 태그 부 버전 고정(`postgres:18.6` · `redis:8.10.1` 등) | **적용됨** — 별도 조치 없음. 태그를 올릴 때는 `docker-compose.staging.yml` 의 값을 바꿈 |
| 연결 대기 3초 · 누수 감지 5초(`R46 D #17`) | **적용됨** — `staging` 프로파일에 들어 있음(§9 증상표) |
| 경보 6종 추가(`BackendDown` · `Http5xxRatioHigh` 등 — `R46-FIXOPS`) | **해당 없음** — 관측·경보 컨테이너가 없음 |
| 로그 `non-blocking` 전송(`awslogs`) · 운영 프록시 JSON 압축(`nginx.prod.conf` `/api/`) | **해당 없음** — 로그는 Docker 기본 드라이버이고 프록시는 `nginx.staging.conf` 라 이번에 바꾸지 않음(터널 뒤라 응답 크기보다 접속이 목적) |
| OOM 이면 프로세스 종료 · 종료 대기 35초(`R46-FIXOPS` `Ruling 641`·`643`) | **적용됨** — backend 에 `JAVA_TOOL_OPTIONS: -XX:+ExitOnOutOfMemoryError` · `stop_grace_period: 35s`. `docker compose restart backend`(§8 초기화)도 이 종료 대기를 쓴다. 힙 상한은 두지 않음(컨테이너 메모리 한도가 없음) |
| postgres `pg_stat_statements` · `random_page_cost=1.1`(`Ruling 644`) | **적용됨** — 운영과 같은 `command` + `infra/postgres/init` 초기화 스크립트. 메모리 DB 라 컨테이너를 다시 만들 때마다 스크립트가 돈다. 쿼리 통계는 `ops_stats.pg_stat_statements` — **`public` 이 아닌 이유**: 이 서버는 기동·초기화마다 Flyway `clean()` 이 `public` 을 비우는데 그때 `public` 의 확장이 같이 지워진다(2026-10-01 로컬 실측) |
