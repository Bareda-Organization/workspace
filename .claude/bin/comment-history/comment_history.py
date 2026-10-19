#!/usr/bin/env python3
"""주석 경위 측정·검사 (Ruling 903 A). 사용 — python3 comment_history.py <작업 공간 루트> [--check | --lines <영역> | --update-baseline | --selftest] [--repo 이름=경로 …]
코드 주석(//, ///, /* */) 안에서 경위 표지(라운드 · Phase · 날짜 · 경위 낱말 · 커밋 해시)가 든 줄을 영역별로 센다. 문자열 · 텍스트 블록 · 템플릿 안의 // 와 /* 는 주석이 아니다.
`Ruling N` · `BR-N` · 기능 ID 는 표지가 아니다(남긴다 — query.py goal-rows 가 코드 주석에서 판정 번호를 찾는다). --check 는 baseline.json 을 넘거나 kept-lines.tsv 의 남긴 줄이 낡았으면 종료 코드 1.
--repo backend=<워크트리> 처럼 저장소 위치를 바꿔 워크트리를 잰다. --kept <파일> 은 kept-lines.tsv 대신 그 파일을 쓴다. 범위 밖 — yml · sql · sh 주석.
주석 영역 하위 경로 "." 는 저장소 루트 바로 아래 파일만이다(web 의 next.config.ts · vitest.setup.ts 등 — 2026-10-19 측정 때 src 밖 손으로 쓴 .ts 는 이 3개뿐, mobile 은 apps · packages 밖에 .dart 없음).
문자열 검사 — *-str 영역은 주석이 아니라 시험 이름 · 단언 메시지 문자열을 같은 표지로 센다. 텍스트 블록 · `+` 로 이은 조각 포함, 주석 · 대상 밖 문자열은 보지 않는다.
  backend(.java): @Operation · @DisplayName · @AcademyScopeExempt 괄호 안, .as · .describedAs · .withFailMessage · .overridingErrorMessage · fail 호출 괄호 안 전부.
  web(.ts/.tsx, web-str): it · test · describe · bench 호출(점 이어붙임 포함 — it.only · test.describe.serial · test.step …)의 첫 인자(제목)만. it.each(표)(제목, …) · it.skipIf(조건)(제목, …) 같은 두 번 호출은 두 번째 호출의 첫 인자.
    expect(값, 메시지) · expect.soft(값, 메시지) 의 둘째 인자. 시험 본문 콜백 안 문자열은 세지 않는다(첫 최상위 쉼표에서 멈춤).
    측정(2026-10-19 web src): it 1411 · describe 492 · it.each 30 · expect 3313(메시지 인자 있는 것은 극소수) · test 1(test.xxx 호출 아님) → 포함. fail( 9 → 제외(RunWaypointPanel · waypointErrors 의 지역 도우미 함수, 단언 아님). assert* 0 · expect.fail 0 · bench 0 · describe/it 점 이어붙임(.only · .skip) 0 → 코드는 처리하나 현재 해당 없음.
  mobile(.dart, mobile-str): test · testWidgets · group · fail 호출의 첫 인자, reason: 이름 인자(어디서든) 의 리터럴.
    측정(2026-10-19 mobile): expect 4241 · testWidgets 1199 · test 640 · group 227 · reason: 219 · fail( 2(진짜 호출, 나머지는 _fail 지역 함수라 제외) · expectLater 25(reason: 로 이미 포함) · testGoldens · blocTest 0 → 제외.
  리터럴: TS '…' "…" `…`(${…} 는 글 그대로), Dart '…' "…" '''…''' \"\"\"…\"\"\" r'…'(원문) · 이웃 리터럴 이어붙임('a' 'b') · `+` 이음. Java 의 작은따옴표는 문자 리터럴이라 여전히 무시.
  알려진 한계 — 정규식 리터럴(/…/) 안의 따옴표 · 백틱은 문자열로 읽힌다(작은따옴표 · 큰따옴표는 줄 끝에서 복구, 백틱은 다음 백틱까지).
--same-code <기준 커밋> [--to <커밋>] [--repo 이름=경로] [--same-code-repo 이름] — 기준 → 작업 트리(--to 가 있으면 그 커밋)에서 바뀐 소스 파일마다 주석 뺀 코드 · 설명 주석(/**) 수 · Ruling/BR 표시 집합을 비교한다. 어긋나면 종료 코드 1.
  어느 저장소(확장자)를 보는가 — --same-code-repo 가 있으면 그 이름, 없고 --repo 가 하나면 그 이름, 둘 다 없으면 backend. --repo 가 둘 이상인데 --same-code-repo 가 없으면 종료 코드 2. backend → .java · web → .ts .tsx · mobile → .dart(.g.dart · .freezed.dart 제외)."""
import json, os, re, subprocess, sys
sys.dont_write_bytecode = True

MARKERS = {
    "round": r"\bR\d{2,3}\b|\bRQA\b",
    "phase": r"\bPhase ?[A-Z]?\d+",
    "date": r"\b20\d\d-\d\d-\d\d\b|\b20\d\d년",
    "word": r"(?<!백그|포그)라운드|당시|이전에는|원래는|바뀌기 전|예전|시절",  # 백그라운드 · 포그라운드(안드로이드 서비스) 는 경위가 아니다
    # R58 2단계 검증(2026-10-18): 아래는 첫 판이 세지 않아 정리 뒤에도 약 580줄 남았다 — 지난 Phase 목표 번호 · 단계 · 작업 주인 · 리뷰 · 보고서 파일
    "goal": r"목표 ?[A-Z]?-?\d|\bgoal \d|\b[A-Z]\d* #\d+\b|\bM-P\d+\b|\b[A-Z]\d [A-Z]\d\b|\b[A-Z]\d-\d{2}\b",  # 지난 목표 번호 · 작업 묶음 이름(F5 M3) · 묶음 항목 번호(M2-01 — 기능 ID 는 글자 뒤에 숫자가 없다) · 피드백 목록 항목(B1 #14 · A #4)
    "step": r"\b[A-Z]\d+ S\d+\b",
    "owner": r"\bT\d+ ?소유|(?<![\w.<])T\d\b(?![\w>])|\bP\d+-T\d|이 태스크|다른 좌석|이 좌석|좌석 경계|이 워크트리",  # 좌석 하나만은 버스 좌석일 수 있어 세지 않는다
    "review": r"게이트 리뷰|리뷰 라운드|조율자 판단|보고서 [①-⑩]",
    "file": r"\bp\d+-task|report-p\d+|docs/archive/rounds|Task \d+ 판단|\b[BF]E-R\d+\b|phase-goal-loop|parallel-agents",
    # 라운드 작업 파일(지시서 · 공통 규칙 · 후속 · 보고서)을 가리키는 표시 — 그 파일은 저장소에 없다
    "brief": r"\b(?:BRIEF|COMMON|FIX)(?:-[A-Za-z0-9]+)+(?:\.md)?\b|\b(?:BRIEF|COMMON|GOALS)\.md\b|\bverdict-\w+\.md\b|\breport-\w[\w-]*\.md\b|보고서 ?(?:§|\d+ ?항)",
    "hash": r"커밋 `?[0-9a-f]{7,}",
}
MARK = re.compile("|".join(f"(?:{v})" for v in MARKERS.values()))
SKIP_DIRS = {"build", "node_modules", ".dart_tool", "graft", ".next", "design-system", ".gradle"}
# 영역 → (저장소 이름, 저장소 안 하위 경로들, 확장자)
AREAS = {
    "backend-main": ("backend", ["backend/src/main/java"], (".java",), "comment"),
    "backend-test": ("backend", ["backend/src/test/java"], (".java",), "comment"),
    "backend-main-str": ("backend", ["backend/src/main/java"], (".java",), "string"),
    "backend-test-str": ("backend", ["backend/src/test/java"], (".java",), "string"),
    "web": ("web", ["src", "."], (".ts", ".tsx", ".mts"), "comment"),
    "mobile": ("mobile", ["apps", "packages"], (".dart",), "comment"),
    "web-str": ("web", ["src", "."], (".ts", ".tsx"), "string"),
    "mobile-str": ("mobile", ["apps", "packages"], (".dart",), "string"),
}
LANG = {".java": "java", ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".dart": "dart"}
SAME_EXTS = {"backend": (".java",), "web": (".ts", ".tsx"), "mobile": (".dart",)}
GENERATED = (".g.dart", ".freezed.dart")

def comments(text, spans=None):
    """(줄 번호, 주석 본문) — 한 줄 주석은 줄마다, 블록 주석은 줄마다 나눠 낸다. spans 를 주면 주석 (시작, 끝) 위치를 담는다."""
    i, n, line, st, buf, start, cs = 0, len(text), 1, None, [], 1, 0
    while i < n:
        c = text[i]
        if c == "\n":
            if st in ("line", "block") and buf:
                yield start, "".join(buf)
            buf = []
            line += 1
            if st == "line":
                st = None
                if spans is not None:
                    spans.append((cs, i))
            elif st in ("'", '"'):  # 한 줄 문자열은 줄을 넘지 않는다 — JSX 글자의 don't 같은 짝 없는 따옴표가 다음 줄 주석을 가리지 않게
                st = None
            start = line
            i += 1
            continue
        if st is None:
            if text.startswith('"""', i) or text.startswith("'''", i):
                st = text[i:i + 3]; i += 3; continue
            if c in "\"'`":
                st = c; i += 1; continue
            if text.startswith("//", i) and not (i > 0 and text[i - 1] == ":"):
                st, start, cs = "line", line, i; i += 2; continue
            if text.startswith("/*", i):
                st, start, cs = "block", line, i; i += 2; continue
            i += 1
            continue
        if st == "line":
            buf.append(c); i += 1; continue
        if st == "block":
            if text.startswith("*/", i):
                if buf:
                    yield start, "".join(buf)
                if spans is not None:
                    spans.append((cs, i + 2))
                buf, st = [], None
                i += 2
                continue
            buf.append(c); i += 1; continue
        if c == "\\":
            i += 2; continue
        if len(st) == 3:
            if text.startswith(st, i):
                st = None; i += 3; continue
        elif c == st or (c == "\n" and st in "\"'"):
            st = None
        i += 1
    if st == "line" and spans is not None:
        spans.append((cs, n))

TAG = re.compile(r"Ruling \d+|BR-\d+")
# 줄을 합치다 생긴 깨짐 — 글 뒤에 남은 빈 ` *` 구분 줄, 글 뒤에 붙은 닫는 `*/`(R58 2단계 검증이 4곳 찾음 · 컴파일은 된다)
JOINED = re.compile(r"[^\s/*]\s+\*\s*$|[^\s/*]\s{2,}\*/\s*$", re.M)

def code_shape(text):
    """(주석 뺀 코드의 토큰 열, 설명 주석 /** 수, Ruling·BR 표시 집합) — 주석만 고쳤으면 앞의 것은 그대로다."""
    spans, tags = [], set()
    for _, c in comments(text, spans):
        tags.update(TAG.findall(c))
    out, k = [], 0
    for a, b in spans:
        out.append(text[k:a]); k = b
    out.append(text[k:])
    docs = sum(1 for a, _ in spans if text.startswith("/**", a) and not text.startswith("/**/", a))
    return " ".join("".join(out).split()), docs, tags

def same_code(repo, base, exts=(".java",), to=None):
    """기준 커밋 → 작업 트리(to 가 있으면 그 커밋)에서 바뀐 소스 파일(exts)을 비교해 어긋난 줄을 낸다(C-3)."""
    git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
    pathspec = [f"*{e}" for e in exts] + [f":(exclude)*{g}" for g in GENERATED if any(g.endswith(e) for e in exts)]
    read_new = (lambda path: git("show", f"{to}:{path}")) if to else (lambda path: open(os.path.join(repo, path), encoding="utf-8").read())
    bad, n = [], 0
    for row in git("diff", "--name-status", base, *([to] if to else []), "--", *pathspec).splitlines():
        st, *paths = row.split("\t")
        if st != "M":
            bad.append(f"{row} — 파일 추가 · 삭제 · 이동"); continue
        n += 1
        old_text, new_text = git("show", f"{base}:{paths[0]}"), read_new(paths[0])
        (oc, od, ot), (nc, nd, nt) = code_shape(old_text), code_shape(new_text)
        if oc != nc:
            bad.append(f"{paths[0]} — 주석 아닌 코드가 바뀜")
        if nd < od:
            bad.append(f"{paths[0]} — 설명 주석 /** {od} → {nd}")
        if ot != nt:
            bad.append(f"{paths[0]} — 표시 빠짐 {sorted(ot - nt)} · 생김 {sorted(nt - ot)}")
        old_lines = {l.strip() for l in old_text.splitlines()}
        joined = [l.strip()[-30:] for l in new_text.splitlines() if JOINED.search(l) and l.strip() not in old_lines]
        if joined:
            bad.append(f"{paths[0]} — 주석 줄이 합쳐짐 {joined[:3]}")
    for b in bad:
        print("⚠", b)
    print(f"same-code — 비교한 파일 {n} · 어긋남 {len(bad)}")
    return 1 if bad else 0

# 문자열 검사 대상 구문 — 애너테이션 3종과 단언 메시지 호출 5종
STR_CALL = re.compile(r"@(?:[\w$]+\.)*(?:Operation|DisplayName|AcademyScopeExempt)\s*\(|\.(?:as|describedAs|withFailMessage|overridingErrorMessage)\s*\(|(?<![\w$])fail\s*\(")

# TS — 시험 선언(첫 인자가 제목) · expect 류(둘째 인자가 메시지). 뒤에 이어 붙는 .only · .skip · .describe.serial 등은 점 이어붙임으로 받는다
TS_CALL = re.compile(r"(?<![\w$.])(?:(?P<t>(?:it|test|describe|bench)(?:\.\w+)*)|(?P<e>expect(?:\.soft)?))\s*\(")
CURRIED = ("each", "for", "skipIf", "runIf")  # it.each(표)(제목, …) — 첫 괄호는 건너뛰고 둘째 호출의 첫 인자가 제목
# Dart — 시험 선언 · fail 의 첫 인자, 그리고 reason: 이름 인자(어디서든)
DART_CALL = re.compile(r"(?<![\w$.])(?:(?:testWidgets|test|group|fail)\s*\(|reason\s*:)")

def arg_literals(text, i, line, lang, skip=0):
    """호출 괄호 바로 안(또는 `reason:` 바로 뒤) i 에서 skip 번째 인자의 최상위 문자열 리터럴만 읽는다 — 중첩 괄호 · 중괄호 · 대괄호 안(시험 본문 콜백)은 세지 않는다.
    → (끝 위치(호출을 닫는 괄호 · 또는 다음 인자 시작), 줄 번호, 첫 리터럴 줄, 조각들)"""
    n, depth, arg, first, parts = len(text), 0, 0, None, []
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2); j = n if j < 0 else j + 2
            line += text.count("\n", i, j); i = j
        elif c in "\"'" or (c == "`" and lang == "ts") or (c == "r" and lang == "dart" and text[i + 1:i + 2] in ("'", '"') and not (text[i - 1].isalnum() or text[i - 1] in "_$")):
            at = line
            i, line, lit = read_literal(text, i, line, lang)
            if lit is not None and arg == skip and depth == 0:
                first = at if first is None else first
                parts.append(lit)
        elif c in "([{":
            depth += 1; i += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1; i += 1
        elif c == "," and depth == 0:
            arg += 1; i += 1
            if arg > skip:
                break
        else:
            i += 1
    return i, line, first, parts

def js_calls(text, lang):
    """(줄 번호, 이어붙인 문자열) — TS · Dart 의 시험 이름 · 단언 메시지 문자열(모듈 설명 참고). 주석 · 대상 밖 호출의 문자열은 보지 않는다."""
    call, lead = (TS_CALL, "itdbe") if lang == "ts" else (DART_CALL, "tgfr")
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2); j = n if j < 0 else j + 2
            line += text.count("\n", i, j); i = j
        elif c in "\"'" or (c == "`" and lang == "ts") or (c == "r" and lang == "dart" and text[i + 1:i + 2] in ("'", '"') and not (text[i - 1].isalnum() or text[i - 1] in "_$")):
            i, line, _ = read_literal(text, i, line, lang)
        elif c in lead and (m := call.match(text, i)):
            i, skip = m.end(), 0
            if lang == "ts" and m["e"]:
                skip = 1
            elif lang == "ts" and m["t"].rsplit(".", 1)[-1] in CURRIED and "." in m["t"]:
                i, line, _, _ = arg_literals(text, i, line, lang, skip=1 << 30)  # 첫 괄호(표 · 조건) 통째로 건너뛴다
                i += 1
                while i < n and text[i] in " \t\r\n":
                    line += text[i] == "\n"; i += 1
                if text[i:i + 1] != "(":
                    continue
                i += 1
            i, line, first, parts = arg_literals(text, i, line, lang, skip)
            if parts:
                yield first, " ".join(parts)
        else:
            i += 1

def string_calls(text, lang="java"):
    """(줄 번호, 이어붙인 문자열) — STR_CALL 괄호 안의 문자열 리터럴(텍스트 블록 포함)을 구문마다 공백으로 이어 낸다. 주석 · 문자 리터럴 · 괄호 밖 문자열은 보지 않는다. ts · dart 는 js_calls."""
    if lang != "java":
        yield from js_calls(text, lang)
        return
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; i += 1; continue
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2); j = n if j < 0 else j + 2
            line += text.count("\n", i, j); i = j; continue
        if c in "\"'":                       # 괄호 밖 리터럴은 건너뛴다
            i, line, _ = read_literal(text, i, line); continue
        m = STR_CALL.match(text, i) if c in "@.f" else None
        if not m:
            i += 1; continue
        i, depth, first, parts = m.end(), 1, None, []
        while i < n and depth:
            c = text[i]
            if c == "\n":
                line += 1; i += 1
            elif text.startswith("//", i):
                while i < n and text[i] != "\n":
                    i += 1
            elif text.startswith("/*", i):
                j = text.find("*/", i + 2); j = n if j < 0 else j + 2
                line += text.count("\n", i, j); i = j
            elif c in "\"'":
                start_line = line
                i, line, lit = read_literal(text, i, line)
                if lit is not None:
                    first = start_line if first is None else first
                    parts.append(lit)
            else:
                depth += (c == "(") - (c == ")"); i += 1
        if parts:
            yield first, " ".join(parts)

def read_literal(text, i, line, lang="java"):
    """text[i] 의 문자열 · 텍스트 블록 · 문자 리터럴을 읽어 (다음 위치, 줄 번호, 내용) — 내용이 None 이면 값이 아니다(Java 문자 리터럴 · 줄 끝에서 닫히지 않은 리터럴).
    lang — java: "…" · \"\"\"…\"\"\" · '…'(문자) / ts: '…' "…" `…`(여러 줄 · ${…} 는 글 그대로) / dart: '…' "…" 셋따옴표 · r'…'(원문) · ${…} 는 글 그대로."""
    n = len(text)
    raw = lang == "dart" and text[i] == "r"
    i += raw
    q = text[i]
    if lang != "ts" and text.startswith(q * 3, i) and (lang == "dart" or q == '"'):
        j = i + 3
        while j < n and not text.startswith(q * 3, j):
            j += 2 if text[j] == "\\" and not raw else 1
        body = text[i + 3:j]
        return j + 3, line + body.count("\n"), " ".join(body.split())
    multi = q == "`"
    j = i + 1
    while j < n and text[j] != q and (multi or text[j] != "\n"):
        if text.startswith("${", j) and lang != "java" and not raw:  # 끼워넣기 안의 따옴표는 리터럴 끝이 아니다
            d, j = 1, j + 2
            while j < n and d:
                d += (text[j] == "{") - (text[j] == "}"); j += 1
            continue
        j += 2 if text[j] == "\\" and not raw else 1
    if j < n and text[j] == "\n" and not multi:  # 줄 끝에서 닫히지 않은 리터럴 — 줄바꿈을 먹으면 이어지는 줄 번호가 밀린다
        return j, line, None
    body = text[i + 1:j]
    return j + 1, line + body.count("\n"), (body if q != "'" or lang != "java" else None)

def str_hits(text, lang="java"):
    return [(ln, t) for ln, t in string_calls(text, lang) if MARK.search(t)]

def hits(text, lang=None):
    return [(ln, c.strip()) for ln, c in comments(text) if MARK.search(c)]

def files(root, sub, exts):
    base = os.path.join(root, sub)
    for dp, dn, fn in os.walk(base):
        dn[:] = [] if sub == "." else sorted(d for d in dn if d not in SKIP_DIRS)  # "." — 저장소 루트 바로 아래 파일만
        for f in sorted(fn):
            if f.endswith(exts) and not f.endswith(GENERATED):
                yield os.path.join(dp, f)

def load_kept(p):
    kept = []  # (영역, 저장소 기준 경로, 줄 안 글자, 이유)
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if l.strip() and not l.startswith("#"):
                a = l.rstrip("\n").split("\t")
                kept.append((a[0], a[1], a[2], a[3] if len(a) > 3 else ""))
    return kept

def measure(repos, kept):
    """영역 → {'lines': [(경로, 줄, 주석)], 'kept': 수} · 쓰인 kept 항목 집합"""
    out, used = {}, set()
    for area, (repo, subs, exts, kind) in AREAS.items():
        root = repos[repo]
        rows, k = [], 0
        for sub in subs:
            for p in files(root, sub, exts):
                rel = os.path.relpath(p, root)
                for ln, c in (str_hits if kind == "string" else hits)(open(p, encoding="utf-8", errors="ignore").read(), LANG[os.path.splitext(p)[1]]):
                    m = [j for j, e in enumerate(kept) if e[0] == area and e[1] == rel and e[2] in c]
                    if m:
                        used.update(m); k += 1
                    else:
                        rows.append((rel, ln, c))
        out[area] = {"lines": rows, "kept": k}
    return out, used

def selftest():
    java = '''/** 진입점 (R57 · Ruling 880). */
class A {
  String s = "/api/**";   // 문자열 안의 /** 는 주석이 아니다
  String u = "http://x";  // Phase 12 에서 추가
  String b = """
      -- R46 text block, not a comment /* nor this */
      """;
  // 옛 토큰을 쓴다 (Ruling 899 · RT-5 · R2 · BR-217)
  /* 2026-10-17 사용자 결정 */
}
'''
    dart = "/// 라운드 기록\n// 백그라운드로 가면 끊는다\nfinal t = '''// R50 not a comment''';\nvoid f() {} // 커밋 a1b2c3d 에서\n"
    ts = "const x = `line // R51 not comment\n${y} /* R52 */`;\n// 이전에는 두 연결\n"
    got = {"java": [ln for ln, _ in hits(java)], "dart": [ln for ln, _ in hits(dart)], "ts": [ln for ln, _ in hits(ts)]}
    want = {"java": [1, 4, 9], "dart": [1, 4], "ts": [3]}
    a = "/** 설명 (R1 · Ruling 7). */\nclass A { int x = 1; // 2026-01-01 추가\n}\n"
    shape = [code_shape(t) for t in (a, a.replace(" (R1 · Ruling 7)", " (Ruling 7)").replace(" // 2026-01-01 추가", ""),
                                     a.replace("x = 1", "x = 2"), a.replace("/** 설명 (R1 · Ruling 7). */\n", ""), a.replace("R1 · Ruling 7", "R1"))]
    got["shape"] = [shape[0][0] == s[0] for s in shape] + [s[1] for s in shape] + [shape[0][2] == s[2] for s in shape]
    want["shape"] = [True, True, False, True, True] + [1, 1, 1, 0, 1] + [True, True, True, False, False]
    got["more"] = [bool(MARK.search(c)) for c in ("(Phase 9 목표 6·15)", "F3 S2 목표 11", "T2 소유", "게이트 리뷰 실측", "p13-task-t2.md", "그 시절엔", "목표 시각 07:30", "Ruling 239 · BR-031",
                                                "── goal 1 — type 필터", "T3 담당", "P5-T6", "이 워크트리에 없다", "버스 좌석 수", "제네릭 <T1> · Map.T1")]
    want["more"] = [True, True, True, True, True, True, False, False, True, True, True, True, False, False]
    got["joined"] = [bool(JOINED.search(t)) for t in (" * 계속 늘어난다. *", " * 성립하지 않는다.     */", " *", " */", " * <p>문단")]
    want["joined"] = [True, True, False, False, False]
    # 문자열 검사 — 종류마다 경위 표지가 든 것(양)과 든 것이 없거나 대상 밖인 것(음)
    sj = '''@Operation(summary = "R58 에서 추가한 조회")
@Operation(summary = "목록 조회", description = "학생 목록을 준다")
@DisplayName("Phase 3 이후 동작")
@DisplayName("Ruling 903 · BR-5 를 지킨다")
@AcademyScopeExempt("2026-10-01 에 면제")
@AcademyScopeExempt(reason = "로그인 전이라 학원이 없다")
void t() {
  assertThat(x).as("당시 값").isEqualTo(1);
  assertThat(x).as("현재 값이다").isEqualTo(1);
  assertThat(x).describedAs("R50 라운드 기록").isTrue();
  assertThat(x).describedAs("정상 값").isTrue();
  assertThat(x).withFailMessage("이전에는 달랐다").isTrue();
  assertThat(x).withFailMessage("달라서는 안 된다").isTrue();
  assertThat(x).overridingErrorMessage("커밋 a1b2c3d 에서 바뀜").isTrue();
  assertThat(x).overridingErrorMessage("바뀌면 안 된다").isTrue();
  fail("Phase 7 에서 도입된 경로");
  fail("도달하면 안 되는 경로");
  assertThat(x).as(\"\"\"
      여러 줄 메시지 R57
      \"\"\").isTrue();
  assertThat(x).as("앞 조각 " + y + " 뒤 조각 " +
      "2026-10-17 결정").isTrue();
  @org.junit.jupiter.api.DisplayName("패키지 이름을 붙여도 R57 은 센다")
  void q() {}
  String plain = "R57 은 일반 문자열이라 세지 않는다";
  // .as("R57 주석 안의 호출") 도 세지 않는다
  assertThat(x).as("쓰이는 값").isTrue(); char q = '"';
}'''
    got["unterminated"] = [ln for ln, _ in str_hits('String s = "닫히지 않은 리터럴\n@DisplayName("R57 이후")\n')]  # 줄 끝에서 끝난 리터럴이 다음 줄 번호를 밀면 안 된다
    want["unterminated"] = [2]
    got["str"] = [ln for ln, _ in str_hits(sj)]
    want["str"] = [1, 3, 5, 8, 10, 12, 14, 16, 18, 21, 23]
    # TS · Dart 문자열 — 번호는 기대 줄(1부터). 음: 본문 안 문자열 · 값 문자열 · 일반 상수 · 주석 · 지역 fail
    st = '''describe("R57 묶음", () => {
  const s = "R58 상수";
  it("정상 이름", () => {
    const m = "Phase 3 본문";
    expect(a, "R59 메시지").toBe(1);
    expect(a, "정상 메시지").toBe(1);
    expect(a).toBe("R60 값");
  });
  it.each(t)("Phase 3 %s", (x) => {});
  it.each([
    ["a", 1],
  ])(`2026-10-17 ${x}`, () => {});
  test.describe.serial("당시 흐름", () => {
    test.step("커밋 a1b2c3d 단계", async () => {});
  });
  // it("R50 주석")
  /* it("R51 블록") */
  it.only("정상", () => { fail("R52 지역 도우미") });
  expect.soft(a, `R61 ${x}`).toBe(1);
  it('이전에는 달랐다', () => {});
  it("정상" +
    " Phase 9", () => {});
  it.skipIf(x)("R70 조건부", () => {});
  it("정상 둘", () => { expect(["R71", "x"]).toEqual(1); });
});
'''
    sd = '''group("""Phase 2 묶음""", () {
  test('R57 이름', () {
    final s = 'R58 본문';
    expect(a, b, reason: 'R59 이유');
    expect(a, b, reason: '정상 이유');
    expect(a, b, reason: 'x' 'R60 이어붙임');
  });
  testWidgets('정상', (t) async { fail('R61 실패'); });
  test(r'R62 raw', () {});
  // test('R50 주석', () {});
  test('값 ${m['k']} 이전에는', () {});
  final z = 'R63 상수';
  _fail('R64 지역');
  expect(a, reason: 'R65 ' +
      '이어붙임');
});
'''
    got["ts-str"] = [ln for ln, _ in str_hits(st, "ts")]
    want["ts-str"] = [1, 5, 9, 12, 13, 14, 19, 20, 21, 23]
    got["dart-str"] = [ln for ln, _ in str_hits(sd, "dart")]
    want["dart-str"] = [1, 2, 4, 6, 8, 9, 11, 14]
    # 같은 코드 판정 — 주석만 바뀐 TS · Dart 는 통과, 코드가 바뀐 것은 실패
    sh = [('const a = 1; // R50 메모\nit("x", () => { return "//not"; });\n', 'const a = 1;\nit("x", () => { return "//not"; });\n', 'const a = 2; // R50 메모\nit("x", () => { return "//not"; });\n'),
          ('final a = 1; /// R50 메모\ntest(\\\'x\\\', () { f(\\\'//not\\\'); });\n', 'final a = 1;\ntest(\\\'x\\\', () { f(\\\'//not\\\'); });\n', 'final a = 2; /// R50 메모\ntest(\\\'x\\\', () { f(\\\'//not\\\'); });\n')]
    got["same"] = [[code_shape(a)[0] == code_shape(b)[0], code_shape(a)[0] == code_shape(c)[0]] for a, b, c in sh]
    want["same"] = [[True, False], [True, False]]
    # 짝 없는 따옴표(JSX 글자의 don't)가 다음 줄의 주석을 가리면 안 된다
    got["fg"] = [bool(MARK.search(c)) for c in ("포그라운드 서비스 알림", "백그라운드로 가면", "이번 라운드에서")]
    want["fg"] = [False, False, True]
    got["brief"] = [bool(MARK.search(c)) for c in ("BRIEF-a1.md 참고", "BRIEF-web 의 규칙", "COMMON-B2 §2", "COMMON.md 3항", "FIX-H.md", "verdict-W.md", "보고서 §1", "보고서 4항", "README.md 참고", "CLAUDE.md", "공통 COMMON 상수", "report-r61-t2.md")]
    want["brief"] = [True, True, True, True, True, True, True, True, False, False, False, True]
    got["label"] = [bool(MARK.search(c)) for c in ("B1 #14 — 같은 이름", "A #5 외부 내비", "F5 M2 목표 A-2", "M-P1 지도", "PR #12 참고", "RUN-08 외부 내비", "목표 시각 07:30")]
    want["label"] = [True, True, True, True, False, False, False]
    got["lane"] = [bool(MARK.search(c)) for c in ("F5 M3 목표", "보고서 § 실측 참고", "M2-01 로그아웃", "M-15 비상", "RUN-08", "A4 용지 크기", "H3 제목")]
    want["lane"] = [True, True, True, False, False, False, False]
    got["apos"] = [ln for ln, _ in hits("<p>don't stop</p>\n// R57 에서 바꿈\nconst s = \"x\";\n")]
    want["apos"] = [2]
    ok = got == want
    print("selftest", "OK" if ok else f"FAIL got={got} want={want}")
    return 0 if ok else 1

def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    if "--selftest" in argv:
        return selftest()
    args = [a for j, a in enumerate(argv) if not a.startswith("--") and (j == 0 or argv[j - 1] not in ("--repo", "--kept", "--same-code", "--lines", "--to", "--same-code-repo"))]
    ws = os.path.abspath(args[0]) if args else os.getcwd()
    repos = {r: os.path.join(ws, r) for r in ("backend", "web", "mobile")}
    for j, a in enumerate(argv):
        if a == "--repo" and j + 1 < len(argv):
            name, path = argv[j + 1].split("=", 1)
            repos[name] = os.path.abspath(path)
    if "--same-code" in argv:
        given = [argv[j + 1].split("=", 1)[0] for j, a in enumerate(argv) if a == "--repo" and j + 1 < len(argv)]
        if "--same-code-repo" in argv:
            name = argv[argv.index("--same-code-repo") + 1]
        elif len(given) > 1:
            print("⚠ --repo 가 둘 이상이면 --same-code-repo <이름> 이 필요하다"); return 2
        else:
            name = given[0] if given else "backend"
        return same_code(repos[name], argv[argv.index("--same-code") + 1], SAME_EXTS[name], argv[argv.index("--to") + 1] if "--to" in argv else None)
    kept = load_kept(argv[argv.index("--kept") + 1] if "--kept" in argv else os.path.join(here, "kept-lines.tsv"))
    res, used = measure(repos, kept)
    base_p = os.path.join(here, "baseline.json")
    if "--update-baseline" in argv:
        json.dump({a: len(r["lines"]) for a, r in res.items()}, open(base_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("baseline 갱신:", {a: len(r["lines"]) for a, r in res.items()})
        return 0
    if "--lines" in argv:
        area = argv[argv.index("--lines") + 1]
        for rel, ln, c in res[area]["lines"]:
            print(f"{rel}:{ln}: {c[:160]}")
        return 0
    base = json.load(open(base_p, encoding="utf-8")) if os.path.exists(base_p) else {}
    fail = False
    for a, r in res.items():
        n, b = len(r["lines"]), base.get(a)
        over = b is not None and n > b
        fail |= over
        print(f"{a:13} 경위 줄 {n:5} · 남긴 줄 {r['kept']:3} · 기준치 {b if b is not None else '-'}{'  ⚠ 기준치 초과' if over else ''}")
    stale = [e for j, e in enumerate(kept) if j not in used]
    for e in stale:
        print(f"⚠ 낡은 남긴 줄 — {e[0]} {e[1]} '{e[2]}'")
    fail |= bool(stale)
    if "--check" in argv:
        return 1 if fail else 0
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
