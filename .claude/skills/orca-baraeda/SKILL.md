---
name: orca-baraeda
description: 바래다 작업 공간에서 Orca 워크트리·작업 창을 띄울 때 전역 Skill orca-launch 와 함께 읽는다. 바래다 고유 사실 — Orca 저장소 4개의 ID·기준 브랜치 · 주 세션 기본값(opus[1m]·xhigh) · 워크트리 위치 .claude/wt · web·mobile 디자인 작업 창 기동법.
---

# 바래다에서 Orca 작업 창 띄우기 — 프로젝트 고유 사실 (2026-10-09 전역 `orca-launch` 에서 분리)

**먼저 전역 Skill `orca-launch` 를 읽는다** — 모델·effort 표 · 한 줄 기동 · 함정 · 대기 루프(`~/.claude/skills/orca-launch/waitloop.py`) · 워크트리 준비(`~/.claude/skills/orca-launch/wt-prep.sh`)는 거기 있다. 여기는 바래다에만 해당하는 값이다.

## Orca 저장소 (2026-10-09 `orca repo list --json` 확인)

| 저장소 | Orca id | `worktreeBaseRef` | setup |
|---|---|---|---|
| 작업 공간 `baraeda/` | `3c27bf9d-085f-4de6-8882-0ee85e31c889` | `refs/heads/main` | 없음 |
| `backend/` | `91d5c584-2268-46e7-898a-6571c12702a1` | `refs/heads/main` | 없음 |
| `web/` | `59c1f6de-ddb2-4fff-9b3e-ed0d76e32f13` | `refs/heads/main` | 없음 |
| `mobile/` | `d991ecf7-01e1-4d02-9089-bfd03de51365` | `refs/heads/main` | 없음 |

- setup 이 없어 `--setup skip`/`run` 이 같은 결과다. 저장소를 다시 등록하면 기준 브랜치부터 다시 본다(전역 스킬의 `worktreeBaseRef` 항목)
- 옛 통합 저장소(School-Bus · Orca id `88941bb9…`)는 2026-10-02 분리 뒤 삭제됐다 — 옛 기록의 그 id·`frontend/apps/academy-web` 경로는 쓰지 않는다

## 주 세션 기본값

- `.claude/settings.json` 이 `model: opus[1m]` · `effortLevel: xhigh` — 작업 창에 `--model`·`--effort` 를 빠뜨리면 **이 값으로 뜬다**(판정·병합하는 주 세션용 값)

## 워크트리 위치

- 작업 공간의 `.claude/wt/<이름>` 에 둔다(작업 공간 git 이 무시) — ⚠ `git -C <backend|web|mobile> worktree add` 의 상대 경로는 **그 저장소 기준**이라 **절대 경로**를 준다(2026-10-03 실제로 `web/.claude/wt/` 에 생겼다)
- 만든 직후 `~/.claude/skills/orca-launch/wt-prep.sh <원본 저장소> <워크트리>` — `backend/.env` · `web/.env.local` · 앱 생성 파일을 복사한다
- 워크트리 안 에이전트에는 `API_SPEC_PATH` · `WEB_REPO_DIR` 를 절대 경로로 준다(프로젝트 `CLAUDE.md` — 세 저장소가 상대 경로로 이어져 있다)

## web · mobile 디자인 작업 창

- ⭐ **web · mobile 디자인 작업 창은 디자인 스킬을 붙여 띄운다(2026-10-03 사용자 지시 — 메인 세션은 지시만 하고 그 스킬을 읽지 않는다).**
  - 스킬은 `web/.claude/skills/`(`agent-browser` · `web-design-guidelines` · `design-references`) · `mobile/.claude/skills/`(`web-design-guidelines` · `design-references`)에 있다. 두 저장소의 `.git/info/exclude` 로 git 밖(공개 저장소에 외부 스킬을 올리지 않는다)
  - 메인 세션은 `.claude/settings.local.json` 의 `skillOverrides: off` 로 막혀 있다(대조 시험 — web 이 별도 저장소라 메인은 원래도 못 찾지만, 동작이 바뀔 때의 안전장치)
  - 띄우는 법 — 한 줄 기동(`worker-start --agent`)은 인자를 못 붙이므로 **창을 먼저 만들고 붙인다**:
    `orca terminal create --worktree current --title <이름> --command "claude --model 'claude-sonnet-5-5[1m]' --effort high --add-dir /Users/mskim/Desktop/PJ/baraeda/<web|mobile> --settings /Users/mskim/Desktop/PJ/baraeda/.claude/design-worker.settings.json"` → `orca orchestration worker-start --spec "…" --terminal <핸들>`. `--add-dir` 가 그 저장소의 스킬을 읽게 하고 `--settings` 가 메인의 `off` 를 그 창에서만 `on` 으로 되돌린다(둘 다 실측 2026-10-03)
  - 끝난 뒤 정리·워크트리 안에서 띄우지 말 것은 전역 스킬의 마지막 두 항목
