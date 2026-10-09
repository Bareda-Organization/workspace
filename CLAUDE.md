# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is — 작업 공간

학원 통원버스 운행·학생 등하원 관리 **멀티 테넌트 플랫폼 "바래다"** 의 **작업 공간**(workspace)이다.
이 폴더(`baraeda/`)는 GitHub `Bareda-Organization/workspace` 저장소이고, **문서와 Claude 설정만** 추적한다.
코드는 아래 세 저장소가 각자 관리하며, 이 폴더 안에 나란히 clone 돼 있다(이 저장소의 `.gitignore` 가 셋을 무시한다).

| 폴더 | 저장소 | 받는 것 | 배포 |
|---|---|---|---|
| `./`(이 폴더) | `workspace` | **모든 문서 `docs/`** · 이 파일 · `.claude/`(설정·사실 노트·스킬) | — |
| `backend/` | `backend` | Spring Boot(`backend/backend/`) · `infra/` · `docker-compose*.yml` | AWS EC2 · 로컬(집 PC + Cloudflare Tunnel) |
| `web/` | `web` | 관계자 웹(Next.js) · `design-system/`(읽기 전용 킷 사본) | Vercel |
| `mobile/` | `mobile` | 앱 2종(`apps/manager-app` · `apps/parent-app`) · 공용 패키지 `packages/baraeda_{core,ui}` | App Store · Play Store |

- **2026-10-02 통합 저장소 `mskim98/School-Bus` 를 이렇게 나눴다**(커밋 이력은 `git filter-repo` 로 옮김). 문서 속 옛 코드 경로는 `docs/README.md §0` 의 대응표로 읽는다
- **git 은 저장소마다 따로다** — 이 폴더에서 `git` 은 문서·설정만 다룬다. 코드는 `git -C backend …` · `git -C web …` · `git -C mobile …`. 받기는 넷 다(`git pull` + `git -C <저장소> pull`)
- **API 를 바꾸는 작업은 문서 → backend → web·mobile 순으로 병합한다.** 사양(`docs/planning/API_SPEC.md`)이 먼저, 서버가 다음, 클라이언트가 마지막
- **세 저장소를 상대 경로로 잇는 곳** — web 의 에러 코드 대조 시험이 `../docs/planning/API_SPEC.md`, mobile 의 문구 대조 시험이 `../web/…`, backend compose 의 `web` 이 `../web` 을 읽는다. ⚠ **워크트리는 다른 위치에 생기므로** 그 안의 에이전트에는 `API_SPEC_PATH` · `WEB_REPO_DIR` 를 절대 경로로 준다
- ⚠ **원격은 모두 공개 저장소다.** push 전에는 `backend/backend/.env` · `web/.env.local` 의 실제 값이 커밋에 없는지 검사한다
- **추적 범위(이 저장소)** — `docs/**/*.md` · `CLAUDE.md` · `.claude/{settings.json,PROJECT_NOTES.md}` · 손으로 쓴 스킬 2개. 사람용 렌더(`docs/render/`) · 기획 원본(`docs/planning/source/` 의 `.docx`) · 보고서(`report/`) · 라운드별 작업 기록(`.claude/` 나머지) · 색인(`graft/` · `.docgraph/`)은 추적 밖
- 색인 — **문서는 docgraph**(이 폴더의 `.docgraph/`, 편집 훅이 자동 갱신) · **코드는 graft 를 저장소마다 따로**(`backend/graft/` · `web/graft/` · `mobile/graft/`). 이 폴더의 `.mcp.json` 이 셋을 `graft-backend` · `graft-web` · `graft-mobile` 로 띄운다 — 질문할 저장소의 도구를 고른다. CLI 는 `graft ask "…" web` 처럼 폴더를 준다
  - 한 색인으로 묶지 않은 이유(2026-10-02 실측) — graft 는 git 이 무시하는 하위 저장소를 건너뛴다. 묶으려면 이 저장소가 세 폴더를 무시하지 않아야 하는데, 그러면 `git add -A` 한 번에 세 저장소가 하위 저장소 링크로 잘못 추가된다

**프론트엔드는 2026-09-10 사용자 결정으로 범위 안이다** — 2026-09-04 Ruling 255(영구 범위 밖)를 뒤집었다. `docs/IMPLEMENTATION_PLAN` 의 Phase F1~F4 `➖` 표기는 옛 Flutter 계획에 대한 것이라 그대로 두고, **프론트 작업의 창구는 `docs/frontend/IMPLEMENTATION_PLAN.md` 로 분리**했다.

- 제품 3개 — 관계자 웹(**Next.js**, 메인 관리자 콘솔을 `(admin)` 라우트 그룹으로 합침) · 학부모·학생 앱(**Flutter**) · 매니저 앱(**Flutter**)
- **앱 하나가 로그인 결과의 역할로 갈라진다** — 학부모↔학생, 기사↔동승자. 갈리는 것은 화면이 아니라 권한과 진입점
- 코드 규칙은 `docs/frontend/web/CONVENTIONS_REACT.md`(React) · `docs/frontend/mobile/CONVENTIONS_FLUTTER.md`(Dart) 2종
- 디자인 시스템 사본은 web 저장소 `design-system/`(**읽기 전용**, 정본은 claude.ai 원격). ⚠ **킷이 구 기획 기반이라 `docs/` 와 어긋나는 곳이 있다** — 어긋나면 `docs/` 가 기준이고, 확인된 4건은 `docs/frontend/IMPLEMENTATION_PLAN.md §4`

- **작업 전 반드시 [`docs/README.md`](docs/README.md) 를 먼저 읽는다.** 제품 사양 4종(`FEATURE_SPEC` · `PRD` · `USER_FLOWS` · `API_SPEC`)의 진입점이며, 이 4개가 **단일 소스(SoT)** 다. **2026-08-24 서비스 방향 전환으로 전면 재작성됐고, 순수 기획(To-Be)이라 구현 상태 표기가 없다** — 현재 코드는 상당 부분이 이 사양과 어긋나며 앞으로 사양에 맞춰 수정할 대상이다.
- **기반 문서는 `docs/planning/FEATURE_SPEC.md`** — 공통 규칙 C-01~18, 정책 상수(확정 30분 전 · ②구간 회차당 1회 · 운행 시작 ±10분 등), 엔티티·상태머신, 기능 ID 체계가 여기서 정의되고 나머지 3종이 이를 참조한다. 새 기능 ID·상태값을 만들지 않는다.
- 문서의 `🔸` 는 구 기획에서 흡수해 **존치 미확정**인 항목이다 — 확정 사실로 취급하지 않는다. (근거 없는 신규 설계를 표시하던 `🆕` 는 2026-08-24 전건 승인되어 제거됐다.)
- **설계 문서는 `docs/backend/ARCHITECTURE.md`(모듈·인가·노선 파이프라인·시간 기반 배치)와 `docs/backend/ERD.md`(테이블·제약·인덱스)** 다. 둘 다 사양 4종에서 유도한 **To-Be 설계**이며 현재 코드와 다르다 — 코드를 이 설계에 맞추는 것이 앞으로의 작업이고, 방향 전환 이전의 코드 실측본은 `git show HEAD:docs/backend/ARCHITECTURE.md` 로 본다.
- **이 서비스의 중심축은 시간이다** — 회차 `idle → confirmed` 전이는 사용자 조작이 아니라 **출발 30분 전 도래**가 일으킨다(`ARCHITECTURE §9`). 배치는 30초 폴링 + 조건부 UPDATE 멱등이고, "실행 시각"과 "판정 시각(출발−30분)" 두 시계를 절대 섞지 않는다.
- **구현 계획·진행 추적은 [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) 단일 창구다.** 세션 재개 시 §8 진행 추적 표에서 현재 Phase 를 확인하고, 작업이 끝나면 그 표를 갱신한다. 횡단 규칙은 §7(**25개**). **2026-10-01 정리 — 본문은 규칙(§0~§7)·진행 추적 표(§8)·열린 항목(§9)·Ruling 색인(§11)과 최근 라운드 절(`R46-*`)만 두고, 끝난 Phase·라운드 기록은 원문 그대로 `docs/archive/rounds/` 로 옮겼다**(파일·절 번호 범위는 그 폴더의 `README.md` — 옛 절 번호(8.45 등)는 같은 번호 머리글로 찾는다). Ruling 번호는 §11 색인에서 기록 위치를 찾는다.
- **작업의 최소 단위는 Phase 가 아니라 기능 ID 1개이고, 그 단위를 `IMPLEMENTATION_PLAN §4.6` 의 TDD 사이클로 처리한다** — 목표 → RED(실패를 눈으로 확인) → GREEN(최소 구현) → REFACTOR → 검증. **실패를 보지 않은 테스트는 산출물로 인정하지 않는다.** 이 시스템의 결함 4종(시각·동시성·인가·개인정보 노출)은 전부 "통과하는 빈 테스트"와 구분되지 않는 형태라 RED 확인이 유일한 판별 수단이다.
- **코드 컨벤션은 `docs/backend/CODE_CONVENTIONS.md`** — 특히 §19(클래스·public 메서드·enum·이벤트·포트에 한 줄 설명 주석)와 §20(SRP·크기 기준·클린 코드)은 매 Phase 채점 대상이다.
- 기획 원본은 `docs/planning/source/학원 통학버스 통합관리 시스템.docx`(불변) 하나다. 루트 `projectInfo.md` 는 **2026-08-24 삭제** — 내용이 두 세대 낡아 오인용 위험이 컸다. 필요하면 `git show HEAD:projectInfo.md`.
- 사실이 여러 문서에서 어긋나면 **`docs/` 가 기준이다.**
- ⭐ **문서는 이 폴더의 `docs/` 하나에만 있다 — 기획 · 백엔드 · 프론트(웹 · 앱)로 나눴다(2026-10-02).** 폴더 지도는 `docs/README.md §0`.

  | 위치 | 받는 것 |
  |---|---|
  | `docs/` 루트 | 문서 지도 `README.md` · 전체 진행 추적과 Ruling 색인 `IMPLEMENTATION_PLAN.md` |
  | `docs/planning/` | **기획** — 사양 4종(`FEATURE_SPEC` · `PRD` · `USER_FLOWS` · `API_SPEC`) · 기획 원본 `source/` |
  | `docs/backend/` | **백엔드** — `ARCHITECTURE` · `ERD` · `TECH_DECISIONS` · `CODE_CONVENTIONS` · `LOAD_TESTING` · `plans/` · `infra/`(`DEPLOYMENT` · `STAGING`) |
  | `docs/frontend/` | **프론트 공통** — `IMPLEMENTATION_PLAN` · `SETUP` · `web/CONVENTIONS_REACT` · `mobile/CONVENTIONS_FLUTTER` |
  | `docs/archive/` | 끝난 기능별 계획·설계 · `rounds/` = 끝난 계획서 라운드·Phase 기록 |
  | `docs/render/` | 사람용 렌더(추적 밖) |

  - 코드 저장소에는 `README.md` · `CLAUDE.md` · `AGENTS.md` · 앱·패키지의 `README`·`CHANGELOG` 만 남긴다(도구가 디렉터리로 찾는다)

- 사용자 6종(`Role` enum): 학부모 `PARENT` · 학생 `STUDENT` · 운전기사 `DRIVER` · 동승자 `ESCORT` · 학원 관계자 `STAFF` · 메인 관리자 `SYSTEM_ADMIN` — 학원 관계자와 메인 관리자는 권한 범위가 완전히 다른 별개 역할
- 멀티 테넌시: 계정 1개가 학원 1곳에 속한다(`account.academy_id`, 메인 관리자만 null — `ck_account_academy_scope`). 옛 `User`↔`Tenant` N:M · `UserTenantRole` 연결 테이블은 2026-08-24 방향 전환으로 소멸했다. 격리는 DB 레벨(RLS·`@Filter`)이 아니라 **애플리케이션 코드**에서 강제된다 — 범위를 토큰에서만 얻는 `AcademyScope` + 저장소 쿼리의 학원 조건(`ARCHITECTURE §6`).

## Orca 로 워크트리·작업 창을 띄울 때

🔴 **`orca worktree create` · `worker-start` · `terminal create` 를 치기 전에 Skill `orca-launch`(전역 — 일반 규칙) 와 Skill `orca-baraeda`(이 저장소의 Orca id·기준 브랜치·워크트리 위치·디자인 창)를 먼저 읽는다.** `--setup skip` 기본 · 작업 창마다 `--model`·`--effort` 명시(sonnet 은 `[1m]`) · 한 줄 기동 · `Default view` 함정 · `worker_done` 발신(Haiku 4.5 는 미발신 · 5.5 는 발신 확인) · `worktreeBaseRef` 가 거기 있다. 조율(기다리기·정산)은 이어서 Skill `orchestration`.

## 저장소별 작업 안내

그 저장소의 파일을 다루면 그 폴더의 `CLAUDE.md` 가 함께 읽힌다.

- **backend** — 빌드·시험 명령(`-PtestDbUrl` 필수) · Docker 구성(포트 15432·16379·3000) · Flyway 정책 · 스택: `backend/CLAUDE.md`
- **web** — 명령(`scripts/verify.sh` · `scripts/test-contract.sh`) · Vercel 주의점: `web/CLAUDE.md`
- **mobile** — 명령(`scripts/verify.sh`) · `--dart-define=API_BASE_URL`: `mobile/CLAUDE.md`

**설계 제약·데이터 모델·기능 범위는 `docs/` 를 본다** — 공통 규칙·엔티티·상태머신·권한은 `docs/planning/FEATURE_SPEC.md`(§2·§3·§6), 정책 채택 이유와 우선순위는 `docs/planning/PRD.md`(§6·§7), 엔드포인트 계약은 `docs/planning/API_SPEC.md`. 모듈 경계·인가 3층·노선 파이프라인·시간 기반 배치는 `docs/backend/ARCHITECTURE.md`(§3·§5·§6·§8·§9) 다.

## 응답/문서 규칙

이 사용자는 Spring 입문 단계의 백엔드 개발자다. 전역 `~/.claude/CLAUDE.md` 규칙(한글 응답, 개념별 1줄 요약 → 번호 흐름 → request→처리→response, Controller/Service/Repository 연계 설명, 흔한 오해 1개 포함)을 따른다.

**문서 포맷 규칙**: 사람이 브라우저로 보는 기술문서(아키텍처·규칙 등)는 전역 정책대로 HTML+인라인 SVG로 작성한다. 단 **Claude가 매 세션 재참조하는 사양·설계·진행추적·컨벤션 문서(`docs/` 8종, `CODE_CONVENTIONS.md` 등)는 토큰 효율을 위해 Markdown으로 유지**한다(HTML의 SVG·CSS 골격은 재로딩 비용만 크다). 같은 내용의 인간용 HTML 렌더(예: `CODE_CONVENTIONS.html`)가 별도로 존재할 수 있으며, 둘은 원칙만 동기화하고 서로 대체하지 않는다.

**HTML 문서 수정 규칙 (2026-07-18 확정)**: `CODE_CONVENTIONS.html` 등 사람용 HTML 문서는 **사용자가 명시적으로 요청한 경우에만** 생성·수정한다. Markdown 원본(`CODE_CONVENTIONS.md` 등)을 바꿨다고 해서 대응하는 HTML을 자동으로 동기화하지 않는다 — 필요하면 사용자가 별도로 요청한다.
