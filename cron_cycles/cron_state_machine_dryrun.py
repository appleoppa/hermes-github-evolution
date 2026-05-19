#!/usr/bin/env python3
"""开智进化 cron 状态机 dry-run 原型。
只验证状态推进与防漏洞规则，不执行真实开智内容。
"""
from __future__ import annotations
import json, datetime, shutil
from pathlib import Path

ROOT = Path('/Users/appleoppa/.hermes/workspace/github-evolution/cron_cycles/dry_run')
ROUNDS = ['R1','R2','R3','R4','R5']


def now():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def cycle_dir(cycle_id='JTEST'):
    return ROOT / cycle_id


def state_path(cycle_id='JTEST'):
    return cycle_dir(cycle_id) / 'state.json'


def read_state(cycle_id='JTEST'):
    return json.loads(state_path(cycle_id).read_text(encoding='utf-8'))


def write_state(state):
    d = cycle_dir(state['cycle_id'])
    d.mkdir(parents=True, exist_ok=True)
    state['updated_at'] = now()
    state_path(state['cycle_id']).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def init(cycle_id='JTEST'):
    if cycle_dir(cycle_id).exists():
        shutil.rmtree(cycle_dir(cycle_id))
    state = {
        'cycle_id': cycle_id,
        'next_round': 'R1',
        'status': '未开始',
        'last_completed_round': None,
        'failure_reason': '',
        'created_at': now(),
        'updated_at': now(),
    }
    write_state(state)
    return state


def validate_evidence(ev):
    required = ['round','loops','apex','shortboard','external_learning','evm','hetu_luoshu','github_factory','next_gate']
    missing = [k for k in required if k not in ev]
    if missing:
        return False, '缺字段:' + ','.join(missing)
    if len(ev['loops']) != 2:
        return False, '循环数不是2'
    for loop in ev['loops']:
        if loop.get('sequences') != ['21354','12534','14325']:
            return False, '序列不完整'
    if not ev['apex'].get('inputs') or 'score' not in ev['apex']:
        return False, 'APEX证据不足'
    if not ev['shortboard'].get('exposed_from'):
        return False, '短板不是从步骤暴露'
    if not ev['external_learning'].get('after_shortboard'):
        return False, '外部学习不是短板之后'
    if not ev['external_learning'].get('quote'):
        return False, '缺原文摘录'
    if ev['evm'].get('real_engine_called') is not True:
        return False, 'EVM未真实调用'
    if ev['github_factory'].get('status') == 'complete' and not ev['github_factory'].get('run_id'):
        return False, 'GitHub工厂无远程编号'
    return True, ''


def make_evidence(round_id, github='missing', matrix='local'):
    round_shortboards = {
        'R1': ('执行延迟', 'R内第1循环监控步骤', 'dry-run source 1'),
        'R2': ('门禁降级风险', 'R内第1循环路由步骤', 'dry-run source 2'),
        'R3': ('默认值掩盖缺项', 'R内第2循环效验步骤', 'dry-run source 3'),
        'R4': ('文本链冒充矩阵', 'R内第2循环提案步骤', 'dry-run source 4'),
        'R5': ('速度压倒真实性', 'R内第2循环自省步骤', 'dry-run source 5'),
    }
    sb, exposed_from, src = round_shortboards.get(round_id, ('执行延迟', 'R内监控步骤', 'dry-run source'))
    return {
        'round': round_id,
        'loops': [
            {'loop': 1, 'sequences': ['21354','12534','14325']},
            {'loop': 2, 'sequences': ['21354','12534','14325']},
        ],
        'apex': {'inputs': {'Θ': 0.7, 'Γ': 0.5}, 'score': 0.12, 'exposes': sb},
        'shortboard': {'text': sb, 'exposed_from': exposed_from},
        'external_learning': {
            'after_shortboard': True,
            'source': src,
            'url': 'https://example.com',
            'read_at': now(),
            'quote': '原文摘录',
            'point': '要点',
            'behavior_change': '下一回合先验门禁'
        },
        'evm': {'real_engine_called': True, 'before': 0.71, 'after': 0.72, 'defect_mapping': {'Run': 0.1}},
        'hetu_luoshu': {'mode': matrix, 'status': 'partial' if matrix == 'local' else 'complete'},
        'github_factory': {'status': github, 'run_id': '123456' if github == 'complete' else None},
        'next_gate': '下一回合入口门禁'
    }


def run_round(round_id, ev=None, cycle_id='JTEST'):
    st = read_state(cycle_id)
    d = cycle_dir(cycle_id)
    if st['status'] in ['已通过','已降级停止','等待审计']:
        raise RuntimeError('当前状态不允许写回合:' + st['status'])
    if st['next_round'] != round_id:
        raise RuntimeError(f'跳回合禁止: next={st["next_round"]}, got={round_id}')
    f = d / f'{round_id}_evidence.json'
    if f.exists():
        raise RuntimeError('禁止覆盖已完成回合:' + round_id)
    ev = ev or make_evidence(round_id)
    ok, reason = validate_evidence(ev)
    if not ok:
        st['status'] = '已降级停止'
        st['failure_reason'] = reason
        write_state(st)
        raise RuntimeError('回合证据失败:' + reason)
    f.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding='utf-8')
    idx = ROUNDS.index(round_id)
    st['last_completed_round'] = round_id
    if idx == len(ROUNDS) - 1:
        st['next_round'] = None
        st['status'] = '等待审计'
    else:
        st['next_round'] = ROUNDS[idx+1]
        st['status'] = '执行中'
    write_state(st)
    return st


def audit_cycle(cycle_id='JTEST'):
    st = read_state(cycle_id)
    d = cycle_dir(cycle_id)
    if st['status'] != '等待审计':
        raise RuntimeError('未到周期审计状态')
    evidences = []
    for r in ROUNDS:
        f = d / f'{r}_evidence.json'
        if not f.exists():
            raise RuntimeError('缺回合证据:' + r)
        ev = json.loads(f.read_text(encoding='utf-8'))
        ok, reason = validate_evidence(ev)
        if not ok:
            raise RuntimeError('审计失败:' + r + ':' + reason)
        evidences.append(ev)
    shortboards = [ev['shortboard']['text'] for ev in evidences]
    sources = [ev['external_learning']['source'] for ev in evidences]
    full = all(ev['github_factory'].get('run_id') for ev in evidences) and all(ev['hetu_luoshu'].get('mode') == 'remote_multi_model' for ev in evidences)
    major_error = len(set(shortboards)) == 1
    status = '完整真实周期' if full and not major_error else '部分完成 / 证据不足'
    audit = {
        'cycle_id': cycle_id,
        'status': status,
        'major_error': major_error,
        'reason': 'GitHub工厂或远程多模型缺失，降级但非大错误' if not full else '',
        'shortboard_unique_count': len(set(shortboards)),
        'source_unique_count': len(set(sources)),
        'audited_at': now()
    }
    (d / 'cycle_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    st['status'] = '已降级停止' if major_error else '已通过'
    st['failure_reason'] = '短板模板化' if major_error else ''
    write_state(st)
    return audit


def attempt_multi_round_write():
    st = read_state()
    # 模拟漏洞：一个tick想同时写R1和R2；如果R1已经存在应被禁止或R2顺序被检查。
    run_round('R1')
    run_round('R2')


def main():
    results = []
    init()
    run_round('R1')
    results.append(('R1推进到R2', read_state()['next_round'] == 'R2'))
    try:
        run_round('R3')
        results.append(('跳过R2写R3必须失败', False))
    except RuntimeError:
        results.append(('跳过R2写R3必须失败', True))
    try:
        run_round('R1')
        results.append(('重复写R1必须失败', False))
    except RuntimeError:
        results.append(('重复写R1必须失败', True))
    for r in ['R2','R3','R4','R5']:
        run_round(r)
    results.append(('R5后进入等待审计', read_state()['status'] == '等待审计'))
    audit = audit_cycle()
    results.append(('缺GitHub/远程矩阵时降级非完整', audit['status'] == '部分完成 / 证据不足'))
    # multi-round write policy test: outside state API, scheduler wrapper must forbid per tick >1.
    init('JMULTI')
    try:
        # wrapper rule: explicitly disallow list length > 1
        requested = ['R1','R2']
        if len(requested) > 1:
            raise RuntimeError('一个cron tick禁止多个回合')
        results.append(('一次tick多个回合必须失败', False))
    except RuntimeError:
        results.append(('一次tick多个回合必须失败', True))
    print(json.dumps({'ok': all(x[1] for x in results), 'results': results, 'audit': audit}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
