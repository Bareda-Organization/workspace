#!/bin/bash
# 실서버 계약 시험 4단계를 한 명령으로 — 웹(시드 새로 + 이미지 --build) → 시드 다시 → manager-app → parent-app(FIXTURE_DB=schoolbus).
# 왜 (R63): 단계를 손으로 이어 치다 zsh 변수에 명령을 담아 5번 실패했고(`$common`), 조율자가 `backend/scripts/test.sh` 로 잘못 적어 종료 127 이 났다.
# 로그에서 통과·실패·건너뜀을 읽는 일(PROJECT_NOTES 판정: 실패 0 · 건너뜀 0, 웹은 의도된 1건 제외)도 이 스크립트가 한다.
#
#   contract-run.sh <out dir>           4단계를 돌려 <out dir>/{web,reseed,manager,parent}.log + summary.tsv 를 쓴다
#   contract-run.sh --judge <out dir>   저장된 로그만 다시 채점한다(아무것도 실행하지 않는다)
#
# 작업 공간은 BARAEDA_WS(없으면 이 파일 위치의 두 단계 위). web/ · backend/ · mobile/ 이 없으면 종료 2.
# 종료: 0 전부 통과 · 1 단계 실패/건너뜀 초과/시드 재생성 증거 없음 · 2 인자·환경 오류. 컨테이너를 내릴 때 `-v` 를 쓰지 않는다.
set -euo pipefail

ALLOW_SKIP_web=1        # 웹: 의도된 건너뜀 1건
ALLOW_SKIP_manager=0
ALLOW_SKIP_parent=0
STEPS="web reseed manager parent"

usage() { echo "usage: contract-run.sh <out dir> | contract-run.sh --judge <out dir>" >&2; exit 2; }

# ---- 채점: 로그 한 단계 → "passed failed skipped" ------------------------------------------------------------------------
vitest_counts() {       # vitest 의 `Tests  3 failed | 1539 passed | 1 skipped (1543)` 줄
  local line p f s
  line=$(grep -E '^[[:space:]]*Tests[[:space:]]' "$1" | tail -1 || true)
  [ -n "$line" ] || return 0
  p=$(grep -oE '[0-9]+ passed' <<<"$line" | grep -oE '[0-9]+' || true)
  f=$(grep -oE '[0-9]+ failed' <<<"$line" | grep -oE '[0-9]+' || true)
  s=$(grep -oE '[0-9]+ skipped' <<<"$line" | grep -oE '[0-9]+' || true)
  echo "${p:-0} ${f:-0} ${s:-0}"
}

flutter_counts() {      # flutter test 의 마지막 진행 줄 `01:09 +27 ~1 -2: …`
  local last p=0 f=0 s=0
  last=$(grep -E '^[0-9]{2}:[0-9]{2} \+[0-9]+' "$1" | tail -1 || true)
  [ -n "$last" ] || return 0
  [[ $last =~ \+([0-9]+) ]] && p=${BASH_REMATCH[1]}
  [[ $last =~ ~([0-9]+) ]] && s=${BASH_REMATCH[1]}
  [[ $last =~ [[:space:]]-([0-9]+) ]] && f=${BASH_REMATCH[1]}
  echo "$p $f $s"
}

judge_step() {          # <step> <dir> → summary.tsv 한 줄을 stdout 으로, 통과면 0
  local step=$1 dir=$2 log="$2/$1.log" ex counts p="-" f="-" s="-" allow why=""
  if [ ! -s "$log" ]; then printf '%s\t-\t-\t-\t-\t-\tFAIL: %s.log missing or empty\n' "$step" "$step"; return 1; fi
  ex=$(grep -E '^EXIT [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+' || true)
  if [ "$step" = reseed ]; then      # 시드 재생성: 백엔드가 떴고, 증거 줄이 있으면 OK 여야 한다(R63 이전 로그에는 증거 줄이 없다)
    grep -q 'backend UP' "$log" || why="backend did not come up"
    ! grep -q '^RESEED FAIL' "$log" || why="reseed proof failed: $(grep '^RESEED FAIL' "$log" | head -1)"
    [ -z "$why" ] && printf 'reseed\t%s\t-\t-\t-\t-\tok\n' "${ex:--}" || printf 'reseed\t%s\t-\t-\t-\t-\tFAIL: %s\n' "${ex:--}" "$why"
    [ -z "$why" ]; return
  fi
  if [ "$step" = web ]; then counts=$(vitest_counts "$log"); else counts=$(flutter_counts "$log"); fi
  allow_var=ALLOW_SKIP_$step; allow=${!allow_var}
  if [ -z "$counts" ]; then why="no result summary line in the log"
  else
    read -r p f s <<<"$counts"
    if [ -z "$ex" ]; then why="no EXIT line"
    elif [ "$ex" != 0 ]; then why="exit $ex"
    elif [ "$f" -gt 0 ]; then why="$f failed"
    elif [ "$s" -gt "$allow" ]; then why="skipped $s > allowance $allow"
    fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$step" "${ex:--}" "${p}" "${f}" "${s}" "$allow" "$([ -z "$why" ] && echo ok || echo "FAIL: $why")"
  [ -z "$why" ]
}

judge_all() {           # <dir> <쓰기 여부 0|1> → 표를 찍고(1 이면 <dir>/summary.tsv 에도 쓴다). 하나라도 실패면 1 — --judge 는 저장된 로그 폴더를 건드리지 않는다
  local dir=$1 write=$2 bad=0 step table
  table=$(printf 'step\texit\tpassed\tfailed\tskipped\tallowed_skipped\tverdict\n')
  for step in $STEPS; do table+=$'\n'$(judge_step "$step" "$dir") || bad=1; done
  echo "$table"
  [ "$write" = 1 ] && echo "$table" > "$dir/summary.tsv"
  return $bad
}

# ---- 인자 ---------------------------------------------------------------------------------------------------------------
case "${1:-}" in
  --judge) [ $# -eq 2 ] && [ -d "$2" ] || usage; judge_all "$(cd "$2" && pwd)" 0; exit $? ;;
  ""|-*) usage ;;
esac
[ $# -eq 1 ] || usage
OUT=$1; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)

WS=${BARAEDA_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
for d in web backend mobile; do
  [ -d "$WS/$d" ] || { echo "workspace $WS has no $d/ — set BARAEDA_WS to the folder that holds web/ backend/ mobile/" >&2; exit 2; }
done
# docker 는 PATH 에서 찾고, 없을 때만 이 기계의 설치 위치를 시도한다(backend/backend/scripts/test.sh 와 같은 규칙)
command -v docker >/dev/null 2>&1 || export PATH="/Applications/Code/Docker.app/Contents/Resources/bin:$PATH"
command -v docker >/dev/null 2>&1 || { echo "docker 를 찾을 수 없다 — Docker 를 설치·실행하라" >&2; exit 2; }
command -v flutter >/dev/null 2>&1 || { echo "flutter 를 찾을 수 없다" >&2; exit 2; }
export BACKEND_PROFILES=local,fixture
BASE_URL=http://localhost:3000/api/v1

step_run() {            # <log 이름> <명령…> — 종료 코드를 로그 끝 `EXIT n` 으로 남기고 스크립트는 계속 간다
  local name=$1 rc=0; shift
  echo "[contract-run] $name: start $(date -u +%H:%M:%SZ)"
  "$@" > "$OUT/$name.log" 2>&1 || rc=$?
  echo "EXIT $rc" >> "$OUT/$name.log"
}

web_step()     { ( cd "$WS/web" && scripts/test-contract.sh ); }
manager_step() { ( cd "$WS/mobile/apps/manager-app" && flutter test --tags real_backend --dart-define=API_BASE_URL="$BASE_URL" ); }
parent_step()  { ( cd "$WS/mobile/apps/parent-app" && flutter test --tags real_backend --dart-define=API_BASE_URL="$BASE_URL" --dart-define=FIXTURE_DB=schoolbus ); }

pg_created() {          # postgres 컨테이너의 Created 시각(없으면 빈 문자열)
  local id
  id=$( cd "$WS/backend" && docker compose -f docker-compose.yml -f docker-compose.app.yml ps -q postgres 2>/dev/null | head -1 || true )
  [ -n "$id" ] && docker inspect -f '{{.Created}}' "$id" 2>/dev/null || true
}

reseed_step() {         # 웹 계약이 가입 신청을 반려해 둔 시드를 버리고 새로 깐다 — 증거: postgres 컨테이너 Created 가 이전보다 늦다
  local before after c="docker compose -f docker-compose.yml -f docker-compose.app.yml"
  before=$(pg_created)
  cd "$WS/backend"
  $c down
  $c up -d
  for _ in $(seq 1 60); do
    if $c exec -T backend curl -sf localhost:8080/actuator/health 2>/dev/null | grep -q '"status":"UP"'; then echo "backend UP"; break; fi
    sleep 3
  done
  after=$(pg_created)
  if [ -n "$after" ] && [[ "$after" > "$before" ]]; then echo "RESEED OK created_before=${before:-none} created_after=$after"
  else echo "RESEED FAIL created_before=${before:-none} created_after=${after:-none}"; return 1; fi
}

step_run web web_step
step_run reseed reseed_step
if ! grep -q '^RESEED OK' "$OUT/reseed.log"; then
  echo "[contract-run] reseed proof missing — app steps skipped" >&2
  judge_all "$OUT" 1 || true
  exit 1
fi
step_run manager manager_step
step_run parent parent_step
judge_all "$OUT" 1
