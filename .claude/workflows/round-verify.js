export const meta = {
  name: 'round-verify',
  description: '끝난 Orca 작업 창마다 diff 묶음 → 목표 표 실측 + 지시서 대비 리뷰를 돌려 통과·수정 판정 요약만 돌려준다',
  whenToUse: '작업 창이 worker_done 을 보낸 뒤 — 조율자가 보고서·검증 출력을 직접 읽지 않고 창별 판정만 받는다 (2026-10-13 시험 도입)',
  phases: [
    { title: 'Package', detail: '창별 diff 묶음 파일 생성', model: 'haiku' },
    { title: 'Verify', detail: 'goal-verifier — 목표 표 · 닿는 곳 표 실측', model: 'sonnet' },
    { title: 'Review', detail: 'task-gate-reviewer — 지시서 대비 판정', model: 'sonnet' },
  ],
}

// 인자 — 조율자가 Workflow({name: 'round-verify', args}) 로 준다. 경로는 전부 절대 경로.
// { round: 'r54', base: '<기준 커밋>', common: '<라운드 COMMON.md>',
//   windows: [{ task: 't1', worktree: '<워크트리>', brief: '<BRIEF-x.md>', report: '<report-x.md>', touch: true, base: '<그 창의 기준 커밋 — 저장소가 다르면>' }] }
// touch: 규칙을 바꾸는 창 — 닿는 곳 표가 없으면 미통과(Skill phase-goal-loop §1.1)
const A = args || {}
const windows = A.windows || []
if (!A.round || !A.base || !A.common || !windows.length) {
  throw new Error('args 에 round · base · common · windows[{task, worktree, brief, report}] 가 모두 필요')
}

const PACKAGE = {
  type: 'object',
  properties: { path: { type: 'string' }, commits: { type: 'integer' }, error: { type: 'string' } },
  required: ['path', 'commits'],
}
const VERIFY = {
  type: 'object',
  properties: {
    passed: { type: 'integer' },
    total: { type: 'integer' },
    failing: {
      type: 'array',
      items: {
        type: 'object',
        properties: { id: { type: 'string' }, why: { type: 'string' }, evidence: { type: 'string' } },
        required: ['id', 'why'],
      },
    },
    touch_total: { type: 'integer' },
    touch_failing: { type: 'array', items: { type: 'string' } },
    blocked: { type: 'string' },
  },
  required: ['passed', 'total', 'failing'],
}
const REVIEW = {
  type: 'object',
  properties: {
    approve: { type: 'boolean' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          file: { type: 'string' },
          summary: { type: 'string' },
        },
        required: ['severity', 'summary'],
      },
    },
    blocked: { type: 'string' },
  },
  required: ['approve', 'findings'],
}

const id = w => `${A.round}-${w.task}`
// 창마다 저장소가 다를 수 있다(R55 — 작업 공간·backend·web·mobile 기준 커밋이 다 다름)
const baseOf = w => w.base || A.base

function packagePrompt(w) {
  const out = `${w.report.replace(/\/[^/]+$/, '')}/diff-${id(w)}.txt`
  return `워크트리 ${w.worktree} 에서 아래 셋을 순서대로 한 파일 ${out} 에 쓴다. 다른 파일은 만들지도 고치지도 않는다.
1) git -C ${w.worktree} log --oneline ${baseOf(w)}..HEAD
2) git -C ${w.worktree} diff --stat ${baseOf(w)}..HEAD
3) git -C ${w.worktree} diff -U10 ${baseOf(w)}..HEAD
path 에 그 파일 경로, commits 에 1) 의 줄 수를 돌려준다. 명령이 실패하면 error 에 출력 첫 줄을 담는다.`
}

function verifyPrompt(w) {
  return `작업 창 ${id(w)} 의 완료 조건 실측. 목표 표는 지시서 ${w.brief} 에 있고, 닿는 곳 표가 붙어 있으면 그것도 판정한다(기준 커밋 ${baseOf(w)}).
명령은 워크트리 ${w.worktree} 에서 실행한다. 결과는 스키마로만 돌려준다 — failing 에 미통과·실행불가 행의 번호 · 거짓이 된 문장 · 근거 출력 한두 줄, touch_failing 에 닿는 곳 표의 미통과 행 번호.
목표 표가 없거나 실행 명령 칸이 빈 행이 있으면 blocked 에 이유를 적고 실행하지 않는다.
⚠ 다른 창의 검증이 동시에 돈다. 실서버 계약 시험(공용 서버 :8080 · 시드를 소비하는 시험)과 눈 확인 행은 실행하지 말고 failing 이 아니라 "조율자 병합 뒤" 로 적는다 — 동시에 또는 두 번 돌리면 서로의 시드를 소비해 실패가 코드 결함과 구별되지 않는다. backend 시험은 scripts/test.sh(실행마다 전용 DB)로만 돌린다.`
}

function reviewPrompt(w, diffPath) {
  return `작업 창 ${id(w)} 의 태스크 게이트 판정. 입력 4종 — 지시서 ${w.brief} · 구현자 보고서 ${w.report} · diff 묶음 ${diffPath} · 전역 제약 ${A.common}.
판정 결과는 스키마로만 돌려준다. approve 는 CRITICAL·HIGH 가 0건이고 지시서 항목을 모두 했을 때만 true. 입력이 없으면 blocked 에 이유.`
}

function verdict(w, v, r) {
  const high = r ? r.findings.filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH') : []
  // 목표 0건은 통과가 아니다 · 규칙을 바꾸는 창은 닿는 곳 표가 있어야 한다(10-13 비판 평가 지적)
  const touchOk = !!v && !(v.touch_failing || []).length && (!w.touch || v.touch_total > 0)
  const ok = !!v && !!r && !v.blocked && !r.blocked && v.total > 0 && v.passed === v.total
    && touchOk && r.approve && high.length === 0
  return {
    window: id(w),
    verdict: ok ? 'pass' : 'fix',
    goals: v ? `${v.passed}/${v.total}` : '실행 실패',
    failing: v ? v.failing : [],
    touch: v && v.touch_total ? `${v.touch_total - (v.touch_failing || []).length}/${v.touch_total}` : (w.touch ? '표 없음 — 미통과' : '해당 없음'),
    touch_failing: v ? v.touch_failing || [] : [],
    blocked: (v && v.blocked) || (r && r.blocked) || null,
    review_high: high,
    // 중간·낮음도 문장으로 — 개수만 받으면 조율자가 journal 을 다시 읽어야 했다(R54 1회차)
    review_other: r ? r.findings.filter(f => !high.includes(f)).map(f => `${f.severity} ${f.file || ''} — ${f.summary}`) : null,
  }
}

const results = await pipeline(
  windows,
  w => agent(packagePrompt(w), {
    label: `${id(w)}-diffpkg-gp-haiku`, phase: 'Package', schema: PACKAGE, model: 'haiku', effort: 'medium',
  }),
  (pkg, w) => parallel([
    () => agent(verifyPrompt(w), {
      label: `${id(w)}-goalverify-goal-sonnet`, phase: 'Verify', schema: VERIFY,
      agentType: 'goal-verifier', model: 'sonnet', effort: 'high',
    }),
    () => (pkg && !pkg.error
      ? agent(reviewPrompt(w, pkg.path), {
        label: `${id(w)}-review-gate-sonnet`, phase: 'Review', schema: REVIEW,
        agentType: 'task-gate-reviewer', model: 'sonnet', effort: 'high',
      })
      : Promise.resolve({ approve: false, findings: [], blocked: `diff 묶음 실패: ${pkg ? pkg.error : '응답 없음'}` })),
  ]).then(([v, r]) => verdict(w, v, r)),
)

const done = results.filter(Boolean)
log(`통과 ${done.filter(r => r.verdict === 'pass').length} / ${windows.length}`)
return done
