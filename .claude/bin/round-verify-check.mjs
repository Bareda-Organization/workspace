// .claude/workflows/round-verify.js 를 가짜 agent 로 돌려 판정 로직만 확인 — 토큰을 쓰지 않는다
// 실행: node .claude/bin/round-verify-check.mjs .claude/workflows/round-verify.js
import { readFileSync } from 'fs'
const src = readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFn = Object.getPrototypeOf(async function () {}).constructor
const pipeline = async (items, ...stages) => Promise.all(items.map(async (it, i) => {
  let prev = it
  for (const s of stages) { prev = await s(prev, it, i) }
  return prev
}))
const parallel = async thunks => Promise.all(thunks.map(t => t().catch(() => null)))
const cases = {
  'r9-t1': { verify: { passed: 3, total: 3, failing: [], touch_total: 4, touch_failing: [] }, review: { approve: true, findings: [{ severity: 'LOW', summary: 'x' }] } },
  'r9-t2': { verify: { passed: 2, total: 3, failing: [{ id: 'G2', why: 'x' }] }, review: { approve: true, findings: [] } },
  'r9-t3': { verify: { passed: 3, total: 3, failing: [], touch_total: 2, touch_failing: ['2'] }, review: { approve: true, findings: [] } },
  'r9-t4': { verify: { passed: 3, total: 3, failing: [] }, review: { approve: true, findings: [{ severity: 'HIGH', summary: 'y' }] } },
  'r9-t5': { pkgError: 'fatal: bad revision', verify: { passed: 1, total: 1, failing: [] } },
  'r9-t6': { verify: { passed: 0, total: 0, failing: [] }, review: { approve: true, findings: [] } },
  'r9-t7': { verify: { passed: 2, total: 2, failing: [] }, review: { approve: true, findings: [] } },
}
const agent = async (prompt, o) => {
  const key = o.label.split('-').slice(0, 2).join('-')
  const c = cases[key]
  if (o.phase === 'Package') return c.pkgError ? { path: '', commits: 0, error: c.pkgError } : { path: `/x/diff-${key}.txt`, commits: 2 }
  return o.phase === 'Verify' ? c.verify : c.review
}
const args = { round: 'r9', base: 'abc', common: '/x/COMMON.md',
  windows: ['t1', 't2', 't3', 't4', 't5', 't6', 't7'].map(t => ({ task: t, worktree: '/w', brief: '/x/B.md', report: '/x/report.md', touch: t === 't7' })) }
const out = await new AsyncFn('args', 'agent', 'pipeline', 'parallel', 'log', 'phase', src)(args, agent, pipeline, parallel, console.log, () => {})
const want = { 'r9-t1': 'pass', 'r9-t2': 'fix', 'r9-t3': 'fix', 'r9-t4': 'fix', 'r9-t5': 'fix', 'r9-t6': 'fix', 'r9-t7': 'fix' }
let bad = 0
for (const r of out) { const ok = r.verdict === want[r.window] && (r.window !== 'r9-t5' || String(r.blocked).startsWith('diff 묶음 실패')); bad += !ok; console.log(ok ? 'OK ' : 'BAD', r.window, r.verdict, r.goals, r.touch, r.blocked || '') }
let threw = false
try { await new AsyncFn('args', 'agent', 'pipeline', 'parallel', 'log', 'phase', src)({ round: 'r9' }, agent, pipeline, parallel, console.log, () => {}) } catch { threw = true }
console.log(threw ? 'OK  인자 부족이면 멈춤' : 'BAD 인자 부족인데 진행'); bad += !threw
process.exit(bad ? 1 : 0)
