---
name: orca-launch
description: Orca 로 워크트리·작업 창(워커)을 만들거나 띄우기 전에 반드시 읽는다. orca worktree create · worker-start · terminal create 를 치기 전, 작업 창의 모델·effort 를 정할 때, 워커가 5분 뒤 exited 로 죽거나 worker_done 이 안 올 때. --setup skip 기본 · sonnet 은 언제나 [1m] · effort high · Haiku 5.5 는 effort medium · 한 줄 기동 · Default view 함정 · worktreeBaseRef.
---

# Orca 로 워크트리·작업 창 띄우기 (2026-09-18~)

2026-09-24 프로젝트 `CLAUDE.md` 에서 옮겼다(매 세션 5k tok 을 싣던 절). 조율 루프(기다리기·정산)는 이 스킬이 아니라 Skill `orchestration` 이다.

```bash
orca worktree create --name <이름> --setup skip     # 기본 — 이걸 쓴다
orca worktree create --name <이름> --setup run      # 프론트 의존성이 필요할 때만
```

- ⚠ **`--setup skip` 을 기본으로 쓴다.** 저장소에 `setup: pnpm install` 이 `run-by-default` 로 등록돼 있어, 생략하면 워크트리마다 프론트 의존성을 내려받는다. 백엔드만 만지는 작업에는 낭비다. **이 정책은 Orca CLI 로 못 바꾼다**(`orca repo` 에 설정 명령이 부재) — 앱 화면에서 바꾸거나 매번 플래그를 준다.
- `--setup run` 이 필요한 때 — `frontend/apps/academy-web` 또는 `frontend/packages/` 를 빌드·실행·시험하는 작업.
- ⚠⚠ **작업 창을 띄울 때 `--model` 을 빠뜨리면 그 창이 `opus[1m]` 로 뜬다.** `.claude/settings.json` 의 기본값이 **주 세션 기준으로 `opus[1m]`** 이기 때문이다(판정·병합 결정을 그 창에서 하므로 의도한 값이다). 작업 창은 성격이 달라서 **매번 명시해야 한다** — 2026-08-29 에 이 누락으로 구현 좌석 5개가 전부 opus 로 돌았고 한 개가 35만 토큰을 썼다(Skill `parallel-agents` §4.1).

  | 작업 | 붙일 것 |
  |---|---|
  | 결과 집계 · 로그 추출 · 개수 세기 · 찾기 | `--model claude-haiku-5-5 --effort medium` |
  | 사양이 정해진 작은 구현(함수 1~2개 + 그 시험) | `--model claude-haiku-5-5 --effort medium` — 끝나면 조율자가 시험 재실행 + 결함 심기로 확인 |
  | 구현 · 리뷰 | **`--model 'claude-sonnet-5-5[1m]' --effort high`** — ⭐ **sonnet 은 언제나 `[1m]`**(2026-09-19 사용자 상시 지시) · ⭐ **effort 는 `high`**(2026-10-09 사용자 승인 — Sonnet 5.5 는 effort 눈금이 재조정돼 `xhigh` 가 과하다. 공식 지침은 에이전트 코딩 `medium` 시작이나 낮은 effort 에서 검사 생략 경향이 있어 한 단계 위. 그 전 2026-10-01 지시는 `xhigh`) |
  | 코드를 건드려 재현하는 디버깅 | 워크트리 + `--model claude-opus-5-5 --effort xhigh` — Opus 5.5 는 기본 effort 가 `medium` 이라 반드시 적는다 |

  ⚠ **사양 충돌 판정 · 원인 미상 디버깅은 기본적으로 창을 띄우지 않는다 — 주 세션이 이미 `opus[1m]` · `xhigh` 다.** 별도 창이 값을 하는 경우는 둘뿐이다: ①**코드를 건드려 재현**해야 해서 워크트리 격리가 필요할 때 ②로그·파일을 대량으로 읽어 **주 세션의 조율 맥락을 밀어낼 때**. 둘 다 아니면 여기서 한다.

  **아래 등급으로 먼저 가고, 막히면 그때 올린다** (2026-09-18 사용자 결정). 미리 올려 두지 않는다 — Haiku→Sonnet 도, `xhigh`→`max` 도 같은 규칙이다. 공식 지침도 *"`max` 는 아래 단계에서 여유가 없다는 것이 측정으로 확인될 때만"*.

  배정 기준의 본문은 **Skill `parallel-agents` §4.1** 이다. 여기 다시 적지 않는다 — 두 벌이 되면 한쪽이 낡는다.
- ⭐ **Orca 로 일할 때도 서브에이전트를 쓴다 — 작업 창 안에서도, 조율자도(2026-10-09 사용자 지시).** 라운드 공통 규칙에 *"서브에이전트를 띄우지 마라"* 를 넣지 말고 **Skill `parallel-agents` §4.4.2 의 문단**을 넣는다(창의 서브에이전트는 창과 같은 워크트리·DB 를 쓰므로 쓰기는 한 번에 하나 · 전용 DB·포트를 그대로 · 리뷰는 조율자 몫). 조율자는 위치 파악·끝난 창의 시험 재실행·결함 심기 확인·읽기 전용 조사를 서브에이전트로 돌리고 **Orca 창은 쓰기 갈래에** 쓴다(§4.4.1)
- **`effortLevel` 기본값도 `xhigh` 다**(주 세션이 opus 라서). `--effort` 를 빠뜨린 작업 창은 모델만 내려가고 **노력 수준은 `xhigh` 로 남는다** — 모델 누락과 같은 형태의 누출이라 위 표대로 둘을 같이 적는다.
- ⚠⚠ **Orca 가 띄우는 창에서는 `.claude/settings.json` 의 `model`·`effortLevel` 이 기준이 아니다.** Orca 는 자체 선택기 값을 **명령줄 인자로** 넘기고, 인자는 설정 파일보다 세다. 2026-09-18 실측 — 설정이 `opus[1m]`·`xhigh` 인데 실제 명령은 `claude --model 'opus[1m]' --effort 'medium'` 이었다(Orca 선택기가 Medium).
  - **Orca 를 거쳐 띄울 때는 Orca 의 `Effort`·`Model` 선택기를 맞춘다.** `settings.json` 은 **Orca 가 아무 값도 안 줄 때의 바닥값**이다
  - ⚠ **`Effort` 는 Orca 설정 화면에 없다 — 모델별로 딸린 값이라 모델을 고르는 자리에만 나타난다.** 저장 위치는 `~/Library/Application Support/orca/profiles/local-default/orca-data.json` 의 `settings.nativeChatSessionOptions.claude.valuesByModel["<모델>"].effort` 이고, 키 이름대로 **네이티브 채팅 창의 모델 선택기** 소속이다. 2026-09-18 접근성 스냅샷 실측 — 설정 화면·터미널 화면 어디에도 effort 요소가 부재했고 채팅 창은 접혀 있었다(`채팅 보기 표시` 토글)
  - ✅ **작업 창은 선택기를 쓰지 말고 명령을 직접 준다** — `orca terminal create --worktree <선택자> --title <이름> --command 'claude --model <모델> --effort <값>'`. Orca 공식 안내(`orca skills get orca-cli`)도 *"`worktree create --agent` 는 per-call model/effort 플래그가 없으니 `terminal create --command` 로 넘기라"* 고 적고 있다. 2026-09-18 실측으로 3종 전부 배너에서 확인 — `Haiku 4.5`(effort 표기 부재) · `Sonnet 5 with high effort` · `Opus 5 with xhigh effort`
  - ✅ **선택기를 우회해도 오케스트레이션은 그대로 붙는다.** `worker-start` 의 인자가 `(--agent <에이전트> | --terminal <핸들>)` 둘 중 하나이고, **`--model`·`--effort` 는 `--terminal` 과 함께 못 쓴다**(터미널이 이미 자기 인자로 떠 있으므로). **①`terminal create --command 'claude --model … --effort …'` → ②`worker-start --spec "<지시>" --terminal <핸들>`** 은 **이미 떠 있는 창에 붙일 때만** 쓴다 — 새로 띄우는 것은 아래 한 줄 경로다. 2026-09-18 실측 — `[ready] stage=input_accepted`, 워커가 지시를 읽고 답까지 냈다. **2026-09-18 오전에 `worker-start --agent claude` 가 `session is not attached` 로 실패한 것과 대비된다 — 깨져 있던 것은 오케스트레이션이 아니라 Orca 가 claude 를 대신 띄우는 부분이었다**
  - ✅✅ **한 줄 기동이 정식 경로다 — `worker-start --spec "<지시>" --worktree current --agent claude --model <모델> --effort <값>`.** 위 ①②(창을 먼저 만들고 붙이기)는 **아래 설정을 고치기 전의 우회책**이며 지금은 불필요하다. 2026-09-18 실측 — `launch.effective` 가 요청과 일치 · `term_` 핸들 · `ready`/`input_accepted` · `live` · 배너 `Sonnet 5` · `worker_done` 수신 · 해제 후 미정리 0건. `--model`·`--effort` 는 여전히 **`--terminal` 과 같이 못 쓴다**(창을 이미 그 인자로 띄웠으므로)
  - ⚠⚠ **그 한 줄이 5분 뒤 `exited` 로 죽으면 코드가 아니라 Orca 설정이다 — `설정 → 실험 → Chat UI → Default view`.** `worker-start --help` 가 *"워커가 어떻게 뜨는지는 사용자의 새 에이전트 탭 설정을 따르며 이를 위한 플래그는 부재"* 라고 적고 있다. 2026-09-18 실측 — `Default view = Chat UI` 이면 워커가 **화면 없는 구조화 채팅 세션**(`mode: structured` · `surface: background` · `structworker_` 핸들)으로 떠서 **`stage=dispatch_input` 에서 지시를 못 받고** 죽는다(`worker_done` 0건 · `worker-read` 는 `session is not attached`). **`Default view = Terminal chat` 으로 바꾸면 `mode: null` 로 정상 기동.** 앱 코드의 성립 조건은 `experimentalNativeChat && openAgentTabsInChatByDefault && experimentalStructuredNativeChat` 3개 전부 참일 때이므로 **가운데 하나만 끄면 되고 `Chat UI` 토글 자체는 켜 둔다.** 설정 변경 CLI 는 부재하고(`orca settings` 없음) 값은 `~/Library/Application Support/orca/profiles/local-default/orca-data.json` 의 `settings.openAgentTabsInChatByDefault` 에서 읽어 확인한다 — ⚠ **앱이 그 값을 메모리에 들고 있어 파일을 직접 고치지 않는다**
  - ✅ **상속 부재의 결정적 근거 — 워커의 모델 ID 에 `[1m]` 이 미부착.** 2026-09-18 실측: 조율자 세션이 `claude-opus-5[1m]`(1M 컨텍스트)인데 거기서 띄운 opus 워커가 **자기 시스템 프롬프트를 인용해 답한 값은 `claude-opus-5`**. 상속이면 `[1m]` 이 동반됐어야 한다. **배너로 판정하지 말고 본인에게 물어 확인**한다(Skill `parallel-agents §4.1.1`) — 3좌석 전원 진술 확보: `claude-haiku-4-5-20251001` · `claude-sonnet-5` · `claude-opus-5`
  - 🔴🔴 **조율을 시작하기 전에 Skill `orchestration` 을 먼저 읽고, 거기서 시키는 대로 `orca skills get orchestration` 으로 *바이너리가 주는* 가이드를 받아라. 이 파일에 그 절차를 옮겨 적지 마라.** 가이드가 파일이 아니라 **CLI 에서 나오는 이유가 "실행할 바이너리와 어긋나지 않게" 이므로**, 여기 복제하면 그 설계를 무너뜨린다.
    - ⚠ **2026-09-19 사고 — 이걸 안 읽고 CLI 를 손으로 다루다 영구 대기에 빠졌다.** 위 기동 항목들이 *띄우는 법* 만 다루고 **조율 루프(기다리기·정산)는 없어서**, 워커 2개가 `worker_done` 을 정상 발신했는데도 조율자가 못 받고 멈춰 있었다. 사용자가 알려주지 않았으면 안 끝났다.
    - **가이드의 정식 루프가 그 답을 이미 담고 있다** — 발주 후 마지막 줄이 **막아서 기다리는 호출**이고(`check --wait --types "worker_done,escalation,question"`), `check` 가 **확인 처리 전까지 같은 배치를 재생한다**는 것도 명시돼 있다(메시지 유실 방지 설계이지 결함이 아니다). 완료 뒤 **정산(재사용·`worker-retain`·`worker-release`) 중 하나를 반드시** 한다는 것도 거기 있다.
    - ⚠ **`stage=settled` 는 완료 *통지* 가 아니다** — dispatch 상태일 뿐이다. **Orca 는 조율자 대화로 밀어 넣지 않는다.** 기다리는 것은 조율자 몫이고, 그 수단이 위 `--wait` 다.
  - ⚠ **`worker_done` 은 자동으로 오지 않는다 — 워커가 명령을 직접 실행해야 한다.** 위 실측에서 Haiku 는 `orchestration send … --type worker_done …` 을 **코드 블록으로 출력만 하고 실행하지 않았고**, 조율자 인박스는 `No messages` 로 남았다. **2026-09-18 하루에 3회 전부 Haiku 에서만 재발**(Sonnet·Opus 는 6회 전부 정상 발신) — 경향이 아니라 **Haiku 고유 형태로 확정**. ⇒ **Haiku 좌석은 완료 수집에 기대지 말고 처음부터 `orca terminal read` 로 답을 회수**하고, 미settle 로 남은 Dispatch 는 `worker-stop` 으로 닫는다(한 줄 기동으로 만든 창은 `worker-start` 소유라 `stop`·`release` 가 창까지 닫는다 — **`terminal create` 로 미리 만든 창은 `retained` 로 남아 손으로 닫아야 한다**). 완료 수집에 기대려면 발주문에 **"이 명령을 실제로 실행하라"** 를 못박고, 그래도 `[ready]` 로 머물면 산출물을 직접 확인한다
    - ⚠ **위 관측은 Haiku 4.5 다. Haiku 5.5 는 미확인**(2026-10-09 기준) — 처음 Orca 창으로 띄울 때 `worker_done` 이 오는지 보고 이 줄을 고친다. 확인 전까지는 4.5 와 같이 `orca terminal read` 로 회수한다
  - ⚠ **Orca 의 `Agent Permissions` 를 `yolo` 로 두지 않는다.** `claude` 에 `--dangerously-skip-permissions` 가 붙어 권한 분류기가 통째로 꺼진다(ECC `common/hooks.md` 가 금지 — 그 파일은 2026-09-24 `~/.claude/ecc-unloaded/common/` 로 옮김). 2026-09-18 에 이 플래그 때문에 확인 대화상자가 뜨고, 터미널 포커스 신호가 그 대화상자에 입력으로 들어가 **기동이 취소**되기도 했다. `manual` 로 둔다
- ⭐ **Haiku 는 5.5(`claude-haiku-5-5`)를 쓴다 — 2026-10-09 사용자 승인.** 4.5 의 제약 둘이 풀렸다.
  - **effort 를 받는다**(low~max, 기본 `medium`) — `--effort medium` 을 적는다. 빠뜨리면 부모의 `xhigh` 를 물려받아 생각이 길어진다. (Haiku 4.5 는 effort 를 지원하지 않아 Claude Code 가 빼고 넘겼다 — 2026-09-18 실측)
  - **컨텍스트 1M** — 접미사 없이 1M 이다(2026-10-09 `claude -p --model claude-haiku-5-5` 의 `modelUsage.contextWindow = 1000000`). 넓은 탐색에도 쓸 수 있다
  - 단가는 프롬프트 100K 이하 $0.10/$0.50 · 초과 $0.50/$2.50(초과해도 Sonnet 의 1/4)
  - 근거 실측(2026-10-09 · 같은 문제 Haiku `medium` 2회 · Sonnet `high` 1회) — 찾기(`@Scheduled` 12개) 12/12 · 심은 결함 3개 리뷰 3/3(단 1회는 영향 방향을 반대로 적음) · TDD 작은 구현 숨긴 정답 9/9 · 심은 변형 4/4 를 자기 시험이 잡음 · **비용 약 1/10**
  - ⚠ **맡기지 않는다** — 사양이 모호한 작업 · 여러 모듈·저장소에 걸친 변경 · API 계약 판단 · 원인 미상 디버깅 · 최종 게이트 판정(첫 단계 후보 뽑기까지만)
  - ⚠ 공식 문서상 약점 — 긴 작업 지시를 `low` 로 받으면 일찍 멈추고, `low`·`medium` 에서 고친 뒤 검사를 생략할 때가 있다. 그래서 `low` 로 내리지 않고, 결과는 조율자가 시험을 다시 돌려 확인한다
- ⭐⭐ **sonnet 작업 창은 예외 없이 `[1m]` 을 붙인다 — 2026-09-19 사용자 상시 지시.** *"앞으로 sonnet 은 오케스트레이터든 다른 방식이든 전부 1m 으로 띄워줘."* **접미사는 적어야만 붙고 부모에게서 상속되지 않는다** — 2026-09-19 실측: 조율 세션이 `claude-opus-5[1m]` 인데 `--model claude-sonnet-5` 로 띄운 워커 2개의 기동 기록이 `requested`·`effective` 둘 다 접미사 부재였다.
  - 확인 — `orca orchestration worker-show --dispatch <id> --json` 의 `result.worker.startOptions.launch.effective.model` 에 `[1m]` 이 실재하는지 본다. **배너로 판정하지 않는다**
  - ⚠ **쉘에서 대괄호가 글로브로 해석되므로 따옴표로 감싼다** — `--model 'claude-sonnet-5[1m]'`
  - ⚠ **`--effort` 는 별개다** — 모델만 바꾸고 빠뜨리면 노력 수준이 부모(`xhigh`)로 남는다
- ⚠ **모델을 섞으면 프롬프트 캐시가 갈린다** — 캐시는 모델별 이름공간이라 창마다 모델이 다르면 공통 앞부분(시스템 프롬프트·CLAUDE.md)의 재사용이 끊긴다. 그래서 **같은 등급 안에서 비용을 줄일 때는 모델 교체보다 `--effort` 를 먼저 내린다**(공식 지침). ⚠ **Haiku 5.5 로 내리는 것은 이 고려 밖이다** — Haiku 의 캐시 없는 입력($0.10/M)이 Sonnet 의 캐시 읽기($0.20/M)보다 싸다.
- ⚠⚠ **`worktreeBaseRef` 는 `refs/heads/main`(로컬)이어야 한다.** 기본값이 `origin/main` 이었고, push 하지 않는 저장소라 원격은 **360 커밋 뒤처져** 있었다 — 그대로 두면 워크트리가 몇 달 전 코드에서 갈라진다. 2026-09-18 에 `orca repo set-base-ref --repo id:88941bb9-3200-415e-a8a9-0e2d5bb4ab7a --ref refs/heads/main` 으로 고쳤다. 저장소를 다시 등록하면 이 값을 확인한다.
- ⚠⚠ **처음 여는 폴더(새 저장소)에 작업 창을 띄우면 Claude Code 의 "이 폴더를 신뢰하는가" 확인이 먼저 뜬다 — 기본 선택이 "No, exit" 라 지시문 제출의 Enter 가 그것을 확정해 Claude 가 바로 종료된다.** 2026-09-26 `observability-stack` 에서 실제 발생.
  - **증상** — 영수증 `stage: turn_start_unobserved` · `worker-list` 가 `start_unknown` · 화면 끝이 신뢰 확인 문구 뒤 **셸 프롬프트**(`❱❱❱`)
  - **처리** — 셸 프롬프트가 보이면 에이전트가 끝난 것이 확인된 상태이니 `worker-stop` 으로 닫는다. **신뢰는 사용자가 직접 수락하게 한다**(그 폴더에서 `claude` → "Yes, I trust this folder" → `/exit`). ⚠ `~/.claude.json` 을 고쳐 대신 수락하지 마라 — 보안 확인을 우회하는 것이다. 수락 뒤 `worker-start --task <원 task> --retry-of <원 dispatch>` 로 다시 띄운다
  - **예방** — 새 폴더를 만들어 창을 띄울 계획이면 **발주 전에** 사용자에게 신뢰 수락을 먼저 부탁한다. Orca 워크트리(`~/orca/workspaces/…`)는 이 확인이 뜨지 않았다
- ⚠⚠ **`worker-start` 여러 개를 한꺼번에(백그라운드 병렬·2초 간격) 치지 마라 — 하나씩 순서대로 친다.** 2026-09-25 백엔드 전체 검사에서 10개를 2초 간격 병렬로 쳤더니 **9개가 `turn_start_unobserved`**(종료 코드 1)였다. 화면을 읽어 보니 지시문이 **입력창(`draft`)에 들어가 있기만 하고 제출되지 않은 채** 빈 프롬프트에서 대기 — 창은 `live` 라 살아 있는 것처럼 보인다.
  - **증상** — 영수증 `stage: turn_start_unobserved` · `orca terminal read --screen` 의 `draft:` 에 지시 전문 · 프롬프트 `❯` 가 비어 있음
  - **복구** — `worker-stop` 으로 멈추고(8개 `stopped`, 1개는 `user_owned` 라 `stop_unknown` → 화면을 확인한 뒤 `worker-abandon` + `terminal close`), `worker-start --task <원 task> --retry-of <원 dispatch>` 로 **하나씩** 다시 띄우면 전부 `input_accepted`. 한 번에 1개씩 치면 9개가 약 1분 안에 모두 뜬다 — 병렬로 줄이는 시간이 거의 없다
  - 원인은 미확인(앱이 동시에 여러 창의 첫 제출을 처리하다 일부를 놓치는 것으로 보임). **병렬 기동으로 아낄 시간이 없으니 순차가 기본**
  - ⚠ **순차로 띄워도 0건이 되지는 않는다** — 2026-10-03 검사 창 10개를 for 루프로 하나씩 띄웠는데 **마지막 1개가 `turn_start_unobserved`** 였다(`draft` 에 지시 전문이 남아 있었다). 그러니 **기동 루프가 끝나면 영수증마다 `stage` 를 확인**하고, `input_accepted` 가 아닌 창은 위 복구 절차(`worker-stop` → `--task … --retry-of …`)로 다시 띄운다. 재기동 1회로 정상이 됐다
- ⭐ **하트비트는 대기 루프가 걷어내고, 조율자는 완료·문제 신고·질문에만 깨어난다(2026-10-04 사용자 지시).** 하트비트 알림마다 턴을 쓰면 그 턴마다 대화 전체를 다시 읽는다 — R48 은 대화 약 80만 토큰에서 하트비트 처리 턴만 수십 번이었다(Opus 기준 턴당 캐시 읽기 약 $0.16).
  - 발주 직후 `python3 .claude/skills/orca-launch/waitloop.py <run_id> 1500` 을 **백그라운드로 하나만** 건다. 루프가 하트비트만 든 묶음을 확인 처리하고, `worker_done`·`escalation`·`question` 이 오면 그 묶음을 출력하고 끝난다(확인 처리는 조율자가 내용을 처리한 뒤 `check --run <id> --ack <deliveryId>`)
  - **시간 만료(`TIMEOUT`)가 멈춘 창 점검 주기다** — 25분마다 깨어나 창별 커밋 수 · `orca terminal read` 마지막 줄을 보고 루프를 다시 건다. 사용량 한도 · API 오류 끊김으로 멈춘 창은 하트비트가 아니라 이것으로 잡힌다(R48 실측 — 멈춤 3회 모두 커밋 수와 화면으로 알아챘다)
  - 대화에 들어오는 *"You have N orchestration message(s)"* 알림은 루프가 돌고 있으면 **도구 호출 없이 한 줄로 넘긴다.** 알림 자체를 끄는 CLI 옵션 · 하트비트 간격 옵션은 부재(간격은 Orca 가 지시문 머리에 넣는다)
  - ⚠ 루프를 두 개 띄우지 마라 — 서버가 `waiter_exists` 로 거절하고, 출력 파일이 같으면 서로 덮는다(R48 실제 발생)
  - 알림 한 번의 비용을 가장 크게 줄이는 수단은 **라운드마다 새 세션으로 시작해 대화를 짧게 두는 것**이다
- **워크트리를 만든 직후 `.claude/skills/orca-launch/wt-prep.sh <원본 저장소> <워크트리>` 를 돈다** — git 이 무시하는 `.env` · `.env.local` · `*.g.dart` · `*.freezed.dart` 를 복사하고 워크트리가 깨끗한지 확인한다(2026-10-03 · Skill `parallel-agents` §12.1 을 손으로 하던 것). ⚠ `git -C <저장소> worktree add <상대 경로>` 의 상대 경로는 **그 저장소 기준**이다 — 작업 공간의 `.claude/wt/` 에 두려면 절대 경로를 준다(2026-10-03 실제로 `web/.claude/wt/` 에 생겼다)
- ⚠ **작업 창이 `API Error: Server error mid-response` 로 끊기면 `worker_done` 없이 빈 프롬프트에서 멈춘다 — `worker-list` 는 여전히 `live` 라 기다려도 안 끝난다**(2026-10-03 창 A · 35분 방치). 판별은 `worker-read --dispatch <id> --limit 5` 의 마지막 항목이 그 오류 문구인지 · 작업 트리 `git status --porcelain`. 복구는 새로 띄우지 말고 **같은 창에 입력** — `orca terminal send --terminal <그 창 핸들> --text "[조율자] … 끊긴 지점부터 이어서 · 이미 커밋한 것은 다시 하지 마라" --enter --wait-submit 15`(핸들은 기동 영수증 `effects[].kind=terminal`). 대화 맥락이 남아 있어 재조사 없이 이어진다. ⚠ 커밋이 몇 시간째 늘지 않는 창은 `check --wait` 만 걸지 말고 이 판별을 먼저 한다
- ⭐ **web · mobile 디자인 작업 창은 디자인 스킬을 붙여 띄운다(2026-10-03 사용자 지시 — 메인 세션은 지시만 하고 그 스킬을 읽지 않는다).**
  - 스킬은 `web/.claude/skills/`(`agent-browser` · `web-design-guidelines` · `design-references`) · `mobile/.claude/skills/`(`web-design-guidelines` · `design-references`)에 있다. 두 저장소의 `.git/info/exclude` 로 git 밖(공개 저장소에 외부 스킬을 올리지 않는다)
  - 메인 세션은 `.claude/settings.local.json` 의 `skillOverrides: off` 로 막혀 있다(대조 시험 — web 이 별도 저장소라 메인은 원래도 못 찾지만, 동작이 바뀔 때의 안전장치)
  - 띄우는 법 — 한 줄 기동(`worker-start --agent`)은 인자를 못 붙이므로 **창을 먼저 만들고 붙인다**:
    `orca terminal create --worktree current --title <이름> --command "claude --model 'claude-sonnet-5-5[1m]' --effort high --add-dir /Users/mskim/Desktop/PJ/baraeda/<web|mobile> --settings /Users/mskim/Desktop/PJ/baraeda/.claude/design-worker.settings.json"` → `orca orchestration worker-start --spec "…" --terminal <핸들>`. `--add-dir` 가 그 저장소의 스킬을 읽게 하고 `--settings` 가 메인의 `off` 를 그 창에서만 `on` 으로 되돌린다(둘 다 실측 2026-10-03)
  - ⚠ **작업 창을 워크트리 폴더 안에서 직접 띄우지 마라**(`--worktree id:<repo>::<워크트리 경로>`) — git 저장소 경계가 달라 Claude Code 신뢰 확인이 뜨고 기본값 "No, exit" 가 지시문 제출의 Enter 로 확정돼 즉시 종료된다(작업 공간이 신뢰돼 있어도, 2026-10-03 실측)
  - ⚠ `terminal create` 로 만든 창은 끝난 뒤 `worker-release` 가 `retained` 로 남긴다 — `orca terminal close --terminal <핸들>` 로 직접 닫는다
