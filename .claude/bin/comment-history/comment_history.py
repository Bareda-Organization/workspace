#!/usr/bin/env python3
"""주석 경위 측정·검사 (Ruling 903 A). 사용 — python3 comment_history.py <작업 공간 루트> [--check | --lines <영역> | --update-baseline | --selftest] [--repo 이름=경로 …]
코드 주석(//, ///, /* */) 안에서 경위 표지(라운드 · Phase · 날짜 · 경위 낱말 · 커밋 해시)가 든 줄을 영역별로 센다. 문자열 · 텍스트 블록 · 템플릿 안의 // 와 /* 는 주석이 아니다.
`Ruling N` · `BR-N` · 기능 ID 는 표지가 아니다(남긴다 — query.py goal-rows 가 코드 주석에서 판정 번호를 찾는다). --check 는 baseline.json 을 넘거나 kept-lines.tsv 의 남긴 줄이 낡았으면 종료 코드 1.
--repo backend=<워크트리> 처럼 저장소 위치를 바꿔 워크트리를 잰다. --kept <파일> 은 kept-lines.tsv 대신 그 파일을 쓴다. 범위 밖 — yml · sql · sh 주석.
--same-code <기준 커밋> (--repo backend=<경로> 와 함께) — 기준 → 작업 트리에서 바뀐 .java 마다 주석 뺀 코드 · 설명 주석(/**) 수 · Ruling/BR 표시 집합을 비교한다. 어긋나면 종료 코드 1."""
import json, os, re, subprocess, sys
sys.dont_write_bytecode = True

MARKERS = {
    "round": r"\bR\d{2,3}\b|\bRQA\b",
    "phase": r"\bPhase ?[A-Z]?\d+",
    "date": r"\b20\d\d-\d\d-\d\d\b|\b20\d\d년",
    "word": r"(?<!백그)라운드|당시|이전에는|원래는|바뀌기 전|예전",  # 백그라운드 는 경위가 아니다
    "hash": r"커밋 `?[0-9a-f]{7,}",
}
MARK = re.compile("|".join(f"(?:{v})" for v in MARKERS.values()))
SKIP_DIRS = {"build", "node_modules", ".dart_tool", "graft", ".next", "design-system", ".gradle"}
# 영역 → (저장소 이름, 저장소 안 하위 경로들, 확장자)
AREAS = {
    "backend-main": ("backend", ["backend/src/main/java"], (".java",)),
    "backend-test": ("backend", ["backend/src/test/java"], (".java",)),
    "web": ("web", ["src"], (".ts", ".tsx")),
    "mobile": ("mobile", ["apps", "packages"], (".dart",)),
}

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

def same_code(repo, base):
    """기준 커밋 → 작업 트리에서 바뀐 .java 를 비교해 어긋난 줄을 낸다(C-3)."""
    git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
    bad, n = [], 0
    for row in git("diff", "--name-status", base, "--", "*.java").splitlines():
        st, *paths = row.split("\t")
        if st != "M":
            bad.append(f"{row} — 파일 추가 · 삭제 · 이동"); continue
        n += 1
        (oc, od, ot), (nc, nd, nt) = code_shape(git("show", f"{base}:{paths[0]}")), code_shape(open(os.path.join(repo, paths[0]), encoding="utf-8").read())
        if oc != nc:
            bad.append(f"{paths[0]} — 주석 아닌 코드가 바뀜")
        if nd < od:
            bad.append(f"{paths[0]} — 설명 주석 /** {od} → {nd}")
        if ot != nt:
            bad.append(f"{paths[0]} — 표시 빠짐 {sorted(ot - nt)} · 생김 {sorted(nt - ot)}")
    for b in bad:
        print("⚠", b)
    print(f"same-code — 비교한 파일 {n} · 어긋남 {len(bad)}")
    return 1 if bad else 0

def hits(text):
    return [(ln, c.strip()) for ln, c in comments(text) if MARK.search(c)]

def files(root, sub, exts):
    base = os.path.join(root, sub)
    for dp, dn, fn in os.walk(base):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for f in sorted(fn):
            if f.endswith(exts) and not f.endswith((".g.dart", ".freezed.dart")):
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
    for area, (repo, subs, exts) in AREAS.items():
        root = repos[repo]
        rows, k = [], 0
        for sub in subs:
            for p in files(root, sub, exts):
                rel = os.path.relpath(p, root)
                for ln, c in hits(open(p, encoding="utf-8", errors="ignore").read()):
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
    ok = got == want
    print("selftest", "OK" if ok else f"FAIL got={got} want={want}")
    return 0 if ok else 1

def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    if "--selftest" in argv:
        return selftest()
    args = [a for j, a in enumerate(argv) if not a.startswith("--") and (j == 0 or argv[j - 1] not in ("--repo", "--kept", "--same-code", "--lines"))]
    ws = os.path.abspath(args[0]) if args else os.getcwd()
    repos = {r: os.path.join(ws, r) for r in ("backend", "web", "mobile")}
    for j, a in enumerate(argv):
        if a == "--repo" and j + 1 < len(argv):
            name, path = argv[j + 1].split("=", 1)
            repos[name] = os.path.abspath(path)
    if "--same-code" in argv:
        return same_code(repos["backend"], argv[argv.index("--same-code") + 1])
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
