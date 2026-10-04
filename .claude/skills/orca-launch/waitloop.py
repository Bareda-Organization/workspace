"""조율자 대기 루프 — 하트비트는 여기서 걷어내고 완료·문제 신고·질문이 올 때만 끝난다.

사용: python3 waitloop.py <run_id> [초=1500]   (백그라운드로 하나만 — 둘이면 waiter_exists)
끝나는 경우 ①worker_done·escalation·question 도착 → 그 묶음 출력(확인 처리는 호출한 쪽이)
          ②시간 만료 → 'TIMEOUT …' — 이것이 멈춘 창 점검 주기다(커밋 수 · 화면 마지막 줄)
"""
import json,subprocess,sys,time
RUN=sys.argv[1]
deadline=time.time()+int(sys.argv[2] if len(sys.argv)>2 else 1500)
def call(args):
    out=subprocess.run(['orca','orchestration']+args+['--json'],capture_output=True,text=True,cwd='/Users/mskim/Desktop/PJ/baraeda').stdout
    lines=[l for l in out.splitlines() if '"_keepalive"' not in l]
    s='\n'.join(lines); i=s.find('{')
    try: return json.loads(s[i:])
    except Exception: return {'raw':s[-1500:]}
while time.time()<deadline:
    left=int(min(590000,(deadline-time.time())*1000))
    if left<5000: break
    d=call(['check','--wait','--types','worker_done,escalation,question','--timeout-ms',str(left)])
    r=d.get('result') or {}
    if not d.get('ok',True) and d.get('error'):
        if d['error'].get('code')=='waiter_exists': time.sleep(30); continue  # 앞 대기가 서버에서 풀릴 때까지(최대 약 10분) 기다린다 — 동시에 두 개를 띄우지 않는 것은 호출하는 쪽 몫
        print('ERROR',d['error'].get('code'),d['error'].get('message')); time.sleep(20); continue
    msgs=r.get('messages') or []
    if r.get('timedOut') or not msgs:
        continue
    real=[m for m in msgs if m.get('type')!='heartbeat']
    if not real:
        call(['check','--run',RUN,'--ack',r.get('deliveryId')]); continue
    print('deliveryId',r.get('deliveryId'))
    for m in msgs:
        print('---',m.get('id'),m.get('type'),m.get('taskId'),m.get('dispatchId'))
        print((m.get('body') or '')[:3000])
    sys.exit(0)
print('TIMEOUT no real messages')
