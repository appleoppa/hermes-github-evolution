#!/usr/bin/env python3
"""Run the awakening state machine with cycle-level pacing.

Policy:
- Inside one cycle: execute consecutive rounds immediately, with no intentional wait.
- Between cycles: wait at least 15 minutes after a cycle completes before starting the next one.
- Never generate future-round evidence; every round is executed by execute_current_round_once.py and must pass before advancing.
"""
import datetime as _dt
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path('/Users/appleoppa/.hermes/workspace/github-evolution')
STATE_ROOT = ROOT / 'cron_cycles/real_runs/ten_cycle_state_machine'
STATE = STATE_ROOT / 'state.json'
RUN_ONE = STATE_ROOT / 'execute_current_round_once.py'
ROUND_TIMEOUT_SECONDS = 150
CYCLE_GAP_SECONDS = 15 * 60


def now_utc():
    return _dt.datetime.utcnow().replace(microsecond=0)


def iso(dt):
    return dt.isoformat() + 'Z'


def parse_iso_z(value):
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None


def load_state():
    if not STATE.exists():
        return {
            'cycle': 1,
            'current_round': 1,
            'total_cycles': 10,
            'rounds_per_cycle': 5,
            'status': 'running',
            'created_at': iso(now_utc()),
            'history': [],
        }
    return json.loads(STATE.read_text(encoding='utf-8'))


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    state = load_state()
    if state.get('status') == 'all_completed':
        print(json.dumps({'status': '全部完成', 'message': '10个周期已完成'}, ensure_ascii=False))
        return 0

    cycle = int(state.get('cycle', 1))
    round_no = int(state.get('current_round', 1))
    total_cycles = int(state.get('total_cycles', 10))

    if cycle > total_cycles:
        state['status'] = 'all_completed'
        state['completed_at'] = state.get('completed_at') or iso(now_utc())
        save_state(state)
        print(json.dumps({'status': '全部完成'}, ensure_ascii=False))
        return 0

    # Enforce gap only at cycle boundary, not between rounds.
    if round_no == 1 and cycle > 1:
        not_before = parse_iso_z(state.get('next_cycle_not_before'))
        current = now_utc()
        if not_before and current < not_before:
            wait_seconds = int((not_before - current).total_seconds())
            print(json.dumps({
                'status': '周期间隔等待中',
                'cycle': cycle,
                'wait_seconds': wait_seconds,
                'next_cycle_not_before': state.get('next_cycle_not_before'),
            }, ensure_ascii=False))
            return 0

    started_cycle = cycle
    executed = []
    while True:
        state_before = load_state()
        current_cycle = int(state_before.get('cycle', 1))
        current_round = int(state_before.get('current_round', 1))

        if state_before.get('status') == 'all_completed' or current_cycle > total_cycles:
            break
        if current_cycle != started_cycle:
            break

        proc = subprocess.run(
            [sys.executable, str(RUN_ONE)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=ROUND_TIMEOUT_SECONDS,
        )
        executed.append({
            'cycle': current_cycle,
            'round': current_round,
            'returncode': proc.returncode,
            'stdout_tail': proc.stdout.strip()[-1200:],
            'stderr_tail': proc.stderr.strip()[-1200:],
        })
        if proc.returncode != 0:
            state_fail = load_state()
            state_fail['status'] = 'blocked'
            state_fail['blocked_gate'] = '单回合执行异常'
            state_fail['blocked_at'] = iso(now_utc())
            state_fail['last_runner_error'] = executed[-1]
            save_state(state_fail)
            print(json.dumps({'status': '阻塞', 'executed': executed}, ensure_ascii=False))
            return proc.returncode or 1

        state_after = load_state()
        if state_after.get('status') == 'blocked':
            print(json.dumps({'status': '门禁阻塞', 'executed': executed, 'state': state_after}, ensure_ascii=False))
            return 0

        next_cycle = int(state_after.get('cycle', current_cycle))
        next_round = int(state_after.get('current_round', current_round))
        if next_cycle != started_cycle:
            # One full cycle has just completed. Set the 15-minute boundary before the next cycle.
            state_after['last_cycle_completed'] = started_cycle
            state_after['last_cycle_completed_at'] = iso(now_utc())
            state_after['next_cycle_not_before'] = iso(now_utc() + _dt.timedelta(seconds=CYCLE_GAP_SECONDS))
            save_state(state_after)
            break

        if next_round == current_round:
            print(json.dumps({'status': '未推进', 'executed': executed, 'state': state_after}, ensure_ascii=False))
            return 1

        # No intentional sleep: next round starts immediately.
        time.sleep(0)

    final_state = load_state()
    print(json.dumps({
        'status': '本次触发完成',
        'started_cycle': started_cycle,
        'executed_rounds': executed,
        'current_cycle': final_state.get('cycle'),
        'current_round': final_state.get('current_round'),
        'state_status': final_state.get('status'),
        'next_cycle_not_before': final_state.get('next_cycle_not_before'),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
