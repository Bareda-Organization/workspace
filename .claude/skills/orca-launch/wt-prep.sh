#!/bin/bash
# 워크트리 준비 — git 이 무시해 워크트리에 따라오지 않는 파일 중 빌드·시험이 먹는 것만 원본에서 복사한다.
# 쓰는 법: wt-prep.sh <원본 저장소> <워크트리>     예) wt-prep.sh backend .claude/wt/f2-a
# 무엇을 복사하나: .env · .env.local · *.g.dart · *.freezed.dart (캐시·빌드 산출물·색인은 뺀다 — Skill parallel-agents §12.1)
# ⚠ .env 는 실 API 키를 담는다. 실 API 를 부르지 않는 작업이면 지시서에서 호출 금지를 함께 준다.
set -euo pipefail
src=$(cd "$1" && pwd)
dst=$(cd "$2" && pwd)

git -C "$src" ls-files --others --ignored --exclude-standard \
  | grep -E '(^|/)\.env(\.local)?$|\.g\.dart$|\.freezed\.dart$' \
  | grep -vE 'node_modules|(^|/)build/|\.dart_tool|/\.gradle/' \
  | while read -r f; do
      mkdir -p "$dst/$(dirname "$f")"
      cp -p "$src/$f" "$dst/$f"
      echo "복사 $f"
    done

# 복사본이 추적 대상으로 잡히면(무시 규칙이 원본과 다르면) 원복 검증이 거짓이 된다 — 빈 결과여야 한다.
left=$(git -C "$dst" status --porcelain)
if [ -n "$left" ]; then
  echo "⚠ 워크트리가 깨끗하지 않다:"; echo "$left"; exit 1
fi
echo "준비 끝: $dst"
