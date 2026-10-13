#!/usr/bin/env python3
"""조율자 세션 한 구간의 요청 수 · 토큰 · 추정 비용 — round-verify 도입 전후 비교용(2026-10-13).

사용: round-cost.py <세션.jsonl> [시작 ISO] [끝 ISO]
     예) round-cost.py ~/.claude/projects/-Users-mskim-Desktop-PJ-baraeda/e01cb42f-….jsonl 2026-10-10T09:10 2026-10-10T13:05
같은 응답이 여러 줄에 걸쳐 기록되므로 message.id 로 중복을 뺀다. 서브에이전트는 <세션>/subagents/*.jsonl 을 모델별로 더한다.
단가(백만 토큰당)는 기억 round-cost-eval-2026-10-11 의 역산값 — 바뀌면 PRICE 만 고친다.
"""
import glob
import json
import os
import sys
from collections import defaultdict

# 입력 · 출력 · 캐시 쓰기 1h · 캐시 쓰기 5m · 캐시 읽기 — opus·sonnet 은 [1m] 값
PRICE = {"opus": (4, 20, 8, 5, 0.2), "sonnet": (2, 10, 4, 2.5, 0.1), "haiku": (0.1, 0.5, 0.2, 0.125, 0.01)}


def tally(path, start, end, acc):
    seen = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"usage"' not in line:
            continue
        d = json.loads(line)
        m, ts = d.get("message") or {}, d.get("timestamp", "")
        if d.get("type") != "assistant" or not m.get("usage") or m.get("id") in seen:
            continue
        if (start and ts < start) or (end and ts >= end):
            continue
        seen.add(m["id"])
        tier = next((k for k in PRICE if k in m.get("model", "")), "opus")
        u, cc = m["usage"], m["usage"].get("cache_creation") or {}
        w1h = cc.get("ephemeral_1h_input_tokens", 0)
        w5m = cc.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - w1h)
        a = acc[tier]
        for k, v in (("요청", 1), ("입력", u.get("input_tokens", 0)), ("출력", u.get("output_tokens", 0)),
                     ("쓰기1h", w1h), ("쓰기5m", w5m), ("읽기", u.get("cache_read_input_tokens", 0))):
            a[k] += v


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path, start, end = argv[1], (argv[2] if len(argv) > 2 else None), (argv[3] if len(argv) > 3 else None)
    main_acc, sub_acc = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    tally(path, start, end, main_acc)
    for sub in glob.glob(os.path.join(path[:-len(".jsonl")], "subagents", "*.jsonl")):
        tally(sub, start, end, sub_acc)
    for label, acc in (("조율자", main_acc), ("서브에이전트", sub_acc)):
        for tier, a in sorted(acc.items()):
            p = PRICE[tier]
            cost = (a["입력"] * p[0] + a["출력"] * p[1] + a["쓰기1h"] * p[2] + a["쓰기5m"] * p[3] + a["읽기"] * p[4]) / 1e6
            avg = a["읽기"] // max(1, a["요청"])
            print(f"{label} {tier}: 요청 {a['요청']} · 요청당 캐시 읽기 {avg:,} · 출력 {a['출력']:,} · 추정 ${cost:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
