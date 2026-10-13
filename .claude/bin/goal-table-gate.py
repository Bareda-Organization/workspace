#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 목표 표 없이 Orca 작업 창에 일을 맡기는 것을 막는다 (2026-10-13).

Skill phase-goal-loop §1 "착수 전에 목표를 먼저 고정한다" 는 글로만 있어서 빠뜨려도 막는 것이 없었다
(2026-08-25 목표 표 없이 에이전트를 먼저 띄움 · 2026-10-12 R53 재조사 Orca 창 6개는 목표 표 없이 기동.
R51·R52 는 작업 지시서마다 `| # | 조건 | 실행 명령 · 단언 |` 표가 있어 통과 — 과거 기동 명령으로 확인).

통과 조건 — `orca orchestration worker-start --spec …` 명령이 가리키는 라운드 폴더(.claude/rNN/)의
가리킨 지시서(또는 라운드의 PLAN.md · GOALS.md)에 머리행이 "조건" 과 "명령" 을 함께 가진 표가 데이터 행 1개 이상으로 있을 것.
건너뛰기 — `--retry-of`(이미 맡긴 일의 재기동) · 명령 앞 `GOAL_TABLE_SKIP=<이유>`(목표 표가 필요 없는 일).
판정은 표의 존재와 형식만이다. 내용이 맞는지는 goal-verifier 와 조율자의 몫.
"""
import glob
import json
import os
import re
import sys

ROUND_RE = re.compile(r"((?:/[^\s'\"]*)?\.claude/r\d+[\w.-]*)((?:/[\w.-]+)*)")
MD_RE = re.compile(r"((?:/[^\s'\"]*)?\.claude/r\d+[^\s'\")]*\.md)")
# 명령으로 실행되는 자리의 기동만 — 문자열·문서 안에 글자만 있는 것(편집 heredoc 등)은 제외(10-13 오탐 실측)
DISPATCH_RE = re.compile(r"(?:^|[;&|(]|\bdo\b|\bthen\b)\s*(?:\w+=\S*\s+)*orca\s+orchestration\s+worker-start\b", re.M)
# 건너뛰기는 orca 명령 바로 앞 환경변수일 때만 — 주석 `# GOAL_TABLE_SKIP=…` 은 인정하지 않는다(10-13 비판 평가 우회 실측)
SKIP_RE = re.compile(r"(?:^|[;&|(]|\n)\s*(?:\w+=\S*\s+)*GOAL_TABLE_SKIP=\S+\s+(?:\w+=\S*\s+)*orca\s")


def has_goal_table(text):
    lines = text.split("\n")
    for i, line in enumerate(lines[:-2]):
        if line.lstrip().startswith("|") and "조건" in line and "명령" in line \
                and re.match(r"\s*\|[\s:|-]+\|\s*$", lines[i + 1]) and lines[i + 2].lstrip().startswith("|"):
            return True
    return False


def expand_vars(cmd):
    """같은 명령 안에서 값을 준 변수만 푼다 — R51 은 `R=…/.claude/r51` 뒤 `$R/BRIEF-$n.md` 로 지시서를 가리켰다"""
    env = dict(re.findall(r"(?:^|[\s;&(])(\w+)=([^\s;&|'\"]+)", cmd))
    return re.sub(r"\$\{?(\w+)\}?", lambda m: env.get(m.group(1), m.group(0)), cmd)


def candidate_files(cmd, cwd):
    """명령이 가리킨 .md(`$n` 은 `*` 로) + 라운드 폴더와 가리킨 하위 폴더의 PLAN.md · GOALS.md.
    폴더 안 아무 .md 나 보지 않는다 — 다른 창의 지시서에 있는 표로 통과하던 우회(10-13 비판 평가)."""
    dirs = []
    for root, rest in ROUND_RE.findall(cmd):
        base = os.path.normpath(os.path.join(cwd, root))
        dirs.append(base)
        sub = os.path.normpath(os.path.join(base, rest.lstrip("/")))
        dirs.append(sub if os.path.isdir(sub) else os.path.dirname(sub))
    files = []
    for path in MD_RE.findall(cmd):
        # 풀지 못한 변수 · `${p%%:*}` 같은 셸 치환은 `*` 로 — R52 는 `BRIEF-${p%%…}.md` 로 이름을 만들었다
        files += sorted(glob.glob(os.path.join(cwd, re.sub(r"\$\{[^}]*\}?|\$\w+", "*", path))))
    for d in dict.fromkeys(dirs):
        files += [os.path.join(d, f) for f in ("PLAN.md", "GOALS.md") if os.path.isfile(os.path.join(d, f))]
    files = [f for f in dict.fromkeys(files) if not os.path.basename(f).startswith(("report-", "verdict-"))]
    return dirs, files


def decide(payload):
    """(통과 여부, 이유)"""
    if payload.get("tool_name") != "Bash":
        return True, ""
    cmd = payload.get("tool_input", {}).get("command", "")
    if not DISPATCH_RE.search(cmd) or "--spec" not in cmd:
        return True, ""
    if "--retry-of" in cmd or SKIP_RE.search(cmd):
        return True, ""
    dirs, files = candidate_files(expand_vars(cmd), payload.get("cwd") or os.getcwd())
    if not dirs:
        return False, ("작업 지시에 라운드 폴더 경로(.claude/rNN/…)가 없어 목표 표를 확인할 수 없음. "
                       "지시문이 그 라운드의 지시서를 가리키게 하거나, 목표 표가 필요 없는 일이면 "
                       "명령 앞에 GOAL_TABLE_SKIP=<이유> 를 붙인다.")
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            if has_goal_table(fh.read()):
                return True, ""
    return False, ("목표 표 없음 — " + ", ".join(dict.fromkeys(dirs)) + " 의 가리킨 지시서 · PLAN.md · GOALS.md 에 머리행이 '조건' 과 '명령' 을 "
                   "함께 가진 표가 없다. Skill phase-goal-loop §1 대로 '완료 조건 | 실행 명령 | 무엇이 깨지면 거짓인가' "
                   "표를 PLAN.md 등에 먼저 적는다(규칙을 바꾸면 §1.1 닿는 곳 표도). "
                   "필요 없는 일이면 명령 앞에 GOAL_TABLE_SKIP=<이유>.")


def main():
    ok, why = decide(json.load(sys.stdin))
    if not ok:
        print(why, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
