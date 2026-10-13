#!/usr/bin/env python3
"""규칙 사본 측정·검사 (Ruling 895). 사용 — python3 rule_copies.py <저장소 루트> [--check | --lines [규칙이름|ALL] | --update-baseline | --selftest] [--loose]
정의처(FEATURE_SPEC '## 2.' ~ '## 3.' 머리 사이)·참조 줄(정의처를 가리키는 줄)·kept-lines.tsv 의 남긴 줄을 뺀 '사본' 줄 수를 규칙별로 세고, --check 는 baseline.json 을 넘거나 남긴 줄 목록에 낡은 기준점이 있으면 종료 코드 1.
검사 범위 — 규칙 번호 없이 값을 다시 쓴 줄을 센다. 규칙 번호가 붙은 줄은 값을 다시 써도 이 검사에서 빠진다 — 그 규칙을 바꾸는 라운드의 목표 표에 `query.py goal-rows '<규칙 번호>'` 닿는 곳 표를 붙여 처리한다(Skill phase-goal-loop §1.1)."""
import json, os, re, sys
sys.dont_write_bytecode = True

DOCS = ["docs/planning/FEATURE_SPEC.md", "docs/planning/PRD.md", "docs/planning/USER_FLOWS.md",
        "docs/planning/API_SPEC.md", "docs/backend/ARCHITECTURE.md", "docs/backend/ERD.md", "docs/qa/QA_SCENARIOS.md"]
DEF_DOC, DEF_START, DEF_END = DOCS[0], re.compile(r"^## 2\. 공통 규칙"), re.compile(r"^## 3\. ")
# 정의처를 가리키는 줄은 사본이 아니라 참조로 센다
POINT_BASE = r"§ ?2\.1|§ ?2\b|정의처|정책 상수|FEATURE_SPEC\.md|정본"
STRICT = "--loose" not in sys.argv  # --loose 는 Ruling 895 이전 측정(어느 C-번호든 있으면 참조)과 맞출 때만
# C-17: 같은 줄(표 칸 경계 무시)에 비상 토큰과 「끌 수 없음」 표현이 함께 있어야 한다. 지연·운행 시작 알림 행은 비상 토큰이 없어 빠진다
C17_PAT = r"^(?=.*(?:비상|emergency|EXC-04)).*(?:항상 발송|수신 설정 항목|끌 수 없|설정 항목[^|]{0,6}부재|on/off 항목 부재)"
# 자체 확인(--selftest) 표본: 규칙 이름 → (잡혀야 하는 줄, 안 잡혀야 하는 줄)
SELFTEST = {"C-17 비상 알림 항상 발송": (
    ["| 비상 알림 | 수신 설정 항목 부재 |", "| 비상 알림 | 끌 수 없음 |", "항상 발송되는 비상 알림", "| emergency | EXC-04 | 관계자 | 항상 발송 |"],
    ["| `delay` | `POST /runs/{runId}/delay` | **관계자** + 학생·학부모 (M-05) | **부재 — 항상 발송** |", "| 운행 시작 | `Run.status` → `moving` | 학부모 · 학생 · 관계자 | **항상 발송**하되 단말 푸시 수신은 `boarding` 토글로 조절 |"])}
# (규칙 이름, 묶음, 패턴) — 묶음이 같으면 한 규칙이다(895 ① 의 5개 규칙)
RULES = [
 ("C-04 ②한도 1회", "C-04", r"회차당 ?1회|회차 ?1회|1회만|1회씩|한도는 회차당"),
 ("C-04 ②창 ±10분·출발+10분", "C-04", r"±\s?10분|출발 시각 ?\+ ?10분|출발 시각 \+10분|시각 \+ 10분|출발 시각 ?\+ ?10 ?분|\+ 10분"),
 ("C-04 ①30분 전 확정", "C-04", r"30분 전"),
 ("C-04 ②30분 안쪽", "C-04", r"30분 안쪽"),
 ("C-02 미승차 대기 3분", "C-02", r"(미승차|에스컬|카운트다운).{0,30}3분|3분.{0,30}(미승차|에스컬|카운트)|미승차 대기"),
 ("정책 위치 송신 2초", "정책", r"송신 ?(주기)?\**\s?\**2초|2초\s?(마다|주기)|\*\*2초\*\*|2초 ?\(2026|2초\s?×"),
 ("정책 승하차 반영 5초", "정책", r"5초 이내"),
 ("정책 알림 보관 14일", "14일", r"14일"),
 ("C-11 로그인 5회", "C-11", r"5회 누적|실패 ?5회|5회.{0,6}차단|계정 단위"),
 ("정책 근접 300m", "300m", r"300 ?m(?![a-zA-Z])"),
 ("정책 출발판정 100m", "정책", r"100 ?m(?![a-zA-Z])"),
 ("정책 지연 5분 단위", "정책", r"5분 단위"),
 ("정책 카카오 4곳", "정책", r"4곳"),
 ("정책 정시출발 +5분", "정책", r"\+5분|5분 이내 운행"),
 ("정책 비상 취소 1분", "정책", r"(취소|발신)[^|]{0,12}1분 이내|1분 이내 (취소|에만)|발신 ?\+ ?1분"),
 ("정책 자녀코드 10분 5회", "정책", r"10분에 ?5회"),
 ("C-07 전원 자동 하차", "C-07", r"전원 자동 (하차|승차|`?(boarded|alighted))|자동 (하차|승차) 처리"),
 ("C-17 비상 알림 항상 발송", "C-17", C17_PAT),
 # 측정만 하는 규칙(895 ③) — 정리는 그 규칙을 고칠 때(888)
 ("C-01 form 가입·승인", "C-01", r"form 회원가입|코드 로그인|승인 대기 화면 하나만"),
 ("C-03 노선 3종", "C-03", r"노선 3종|고정 노선 ?=|확정 노선 ?=|실시간 노선 ?="),
 ("C-05 미경유 skipped", "C-05", r"잔여 탑승자 0명|`skipped` 처리"),
 ("C-06 승하차 처리 주체", "C-06", r"동승자만|유일 주체|기사는 조회만"),
 ("C-08 시간 정보 비노출", "C-08", r"ETA.{0,20}(미표시|비노출)|탑승 인원 미표시"),
 ("C-09 변경분 색", "C-09", r"당일 추가 ?= ?초록|취소선"),
 ("C-10 낙관적 UI 금지", "C-10", r"낙관적 UI"),
 ("C-12 공용 정류장 부재", "C-12", r"공용 정류장"),
 ("C-13 서비스 대상", "C-13", r"휴대전화.{0,10}보유|학생 계정 전제"),
 ("C-14 토큰 보관 위치", "C-14", r"HttpOnly|기기 보안 저장소"),
 ("C-15 종료 겸함", "C-15", r"별도 운행 종료 버튼|종료는 보류"),
 ("C-16 일일 승하차지 입력", "C-16", r"일일 승하차지"),
 ("C-18 네이버 API", "C-18", r"네이버 API"),
]

def load(root):
    here = os.path.dirname(os.path.abspath(__file__))
    kept = []  # (규칙 이름 또는 *, 문서, 줄 앵커, 이유)
    with open(os.path.join(here, "kept-lines.tsv"), encoding="utf-8") as f:
        for l in f:
            if l.strip() and not l.startswith("#"):
                p = l.rstrip("\n").split("\t")
                kept.append((p[0], p[1], p[2], p[3] if len(p) > 3 else ""))
    base = json.load(open(os.path.join(here, "baseline.json"), encoding="utf-8"))
    return kept, base

def measure(root, kept):
    """규칙 이름 → {'copies': [(문서, 줄번호, 줄)], 'kept': 수, 'defs': 수, 'refs': 수}"""
    out = {n: {"copies": [], "kept": 0, "defs": 0, "refs": 0} for n, _, _ in RULES}
    # 참조 줄은 그 규칙 자신의 번호(C-04 등) 또는 정의처 표현이 있어야 한다 — 다른 규칙의 번호는 참조로 치지 않는다
    point = {n: re.compile((POINT_BASE + ("|" + grp if grp.startswith("C-") else "")) if STRICT else POINT_BASE + r"|C-\d\d") for n, grp, _ in RULES}
    found_def, used = False, set()
    for d in DOCS:
        in_def, lines = False, open(os.path.join(root, d), encoding="utf-8").read().split("\n")
        for i, l in enumerate(lines, 1):
            if d == DEF_DOC:
                if DEF_START.match(l): in_def = found_def = True
                elif DEF_END.match(l): in_def = False
            for name, _, pat in RULES:
                if not re.search(pat, l): continue
                r = out[name]
                if in_def: r["defs"] += 1
                elif point[name].search(l): r["refs"] += 1
                elif any(k[1] == d and k[0] in (name, "*") and k[2] in l for k in kept):
                    r["kept"] += 1
                    used.update(j for j, k in enumerate(kept) if k[1] == d and k[0] in (name, "*") and k[2] in l)
                else: r["copies"].append((d, i, l))
    if not found_def: sys.exit("정의처 머리('## 2. 공통 규칙')를 FEATURE_SPEC 에서 찾지 못했다 — 절 머리가 바뀌었으면 DEF_START 를 고친다")
    # 낡은 기준점 — 문서에서 사라졌거나 아무 규칙에도 더는 걸리지 않는 남긴 줄은 면제로 쌓이지 않게 실패시킨다
    out["__stale__"] = [k for j, k in enumerate(kept) if j not in used]
    return out

def by_group(res):
    g = {}
    for name, grp, _ in RULES:
        g[grp] = g.get(grp, 0) + len(res[name]["copies"])
    return g

def selftest():
    """패턴이 표본을 제대로 가르는지 본다 — 못 가르면 종료 코드 1"""
    bad = []
    for name, _, pat in RULES:
        if name not in SELFTEST: continue
        pos, neg = SELFTEST[name]
        bad += [f"[{name}] 못 잡음: {l}" for l in pos if not re.search(pat, l)]
        bad += [f"[{name}] 오탐: {l}" for l in neg if re.search(pat, l)]
    for b in bad: print(b)
    print("selftest", "실패" if bad else f"통과 (규칙 {len(SELFTEST)}개 · 표본 {sum(len(p)+len(n) for p, n in SELFTEST.values())}개)")
    sys.exit(1 if bad else 0)

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    flags = [x for x in sys.argv[1:] if x.startswith("--")]
    if "--selftest" in flags: selftest()
    if not a: sys.exit(__doc__)
    root = a[0]; kept, base = load(root); res = measure(root, kept)
    if "--update-baseline" in flags:
        json.dump({n: len(res[n]["copies"]) for n, _, _ in RULES}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("기준치 갱신"); return
    if "--lines" in flags:
        want = a[1] if len(a) > 1 else "ALL"
        for name, _, _ in RULES:
            if want in ("ALL", name):
                for d, i, l in res[name]["copies"]: print(f"[{name}] {d}:{i}: {l.strip()[:160]}")
        return
    over = 0
    stale = res["__stale__"]
    for name, _, _ in RULES:
        n, b = len(res[name]["copies"]), base.get(name, 0)
        mark = "" if n <= b else f"  ← 기준치 {b} 초과"
        print(f"{name}: 사본 {n} · 참조 {res[name]['refs']} · 정의처 {res[name]['defs']} · 남긴 줄 {res[name]['kept']} (기준치 {b}){mark}")
        if n > b:
            over += 1
            for d, i, l in res[name]["copies"]: print(f"    {d}:{i}: {l.strip()[:140]}")
    print("묶음별 사본:", by_group(res), "· 합계", sum(len(res[n]["copies"]) for n, _, _ in RULES))
    for k in stale: print(f"낡은 기준점: {k[1]} 「{k[2][:40]}」 — 문서에 없거나 어떤 규칙에도 걸리지 않는다. kept-lines.tsv 에서 지운다")
    if "--check" in flags and (over or stale):
        print(f"기준치를 넘은 규칙 {over}개 · 낡은 기준점 {len(stale)}개 — 정의처 참조로 바꾸거나 kept-lines.tsv 에 이유와 함께 남기고, 낡은 기준점은 지운다"); sys.exit(1)

if __name__ == "__main__": main()
