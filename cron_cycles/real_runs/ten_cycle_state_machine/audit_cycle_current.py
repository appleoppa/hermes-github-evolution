#!/usr/bin/env python3
import json
import pathlib
import datetime

root = pathlib.Path('/Users/appleoppa/.hermes/workspace/github-evolution/cron_cycles/real_runs/ten_cycle_state_machine')
evdir = root / 'evidence'
state_path = root / 'state.json'
state = json.loads(state_path.read_text(encoding='utf-8'))
cycle = int(state.get('last_cycle_completed') or state.get('cycle', 1))
issues = []
evidences = []

for r in range(1, 6):
    p = evdir / f'C{cycle:02d}_R{r}.json'
    if not p.exists():
        issues.append(f'缺回合证据 C{cycle:02d}R{r}')
        continue
    d = json.loads(p.read_text(encoding='utf-8'))
    evidences.append(d)
    if d.get('cycle') != cycle or d.get('round') != r:
        issues.append(f'C{cycle:02d}R{r} 编号不一致')
    if '证据不足' in d.get('status_grade', '') or '失败' in d.get('status_grade', ''):
        issues.append(f'C{cycle:02d}R{r} 状态不合格:{d.get("status_grade")}')

    loops = d.get('loops')
    if not loops or len(loops) != 2:
        issues.append(f'C{cycle:02d}R{r} 缺两个循环loops证据')
    else:
        for lp in loops:
            if lp.get('sequences') != ['21354', '12534', '14325']:
                issues.append(f'C{cycle:02d}R{r} 序列不完整')

    apex = d.get('apex_total_formula') or d.get('apex')
    if not apex:
        issues.append(f'C{cycle:02d}R{r} 缺APEX')
    else:
        result = apex.get('result', apex.get('score'))
        sb = apex.get('shortboard_exposed') or apex.get('exposes')
        if not apex.get('inputs') or result is None or not sb:
            issues.append(f'C{cycle:02d}R{r} APEX输入/输出/短板不完整')

    if not d.get('shortboard_source') and not (d.get('shortboard') or {}).get('exposed_from'):
        issues.append(f'C{cycle:02d}R{r} 短板来源步骤不足')

    learning = d.get('external_learning') or {}
    has_read = learning.get('read_snippets') or learning.get('read_excerpt') or learning.get('quote')
    if not (learning.get('url') and has_read and learning.get('extracted_points') and learning.get('behavior_change')):
        issues.append(f'C{cycle:02d}R{r} 外部学习证据不完整')

    evm = d.get('evm') or {}
    if '真实EVM入口已调用' not in str(evm.get('status', '')) and evm.get('real_engine_called') is not True:
        issues.append(f'C{cycle:02d}R{r} EVM真实调用证据不足')
    if not evm.get('before') or not evm.get('after') or not (evm.get('defects_before') or evm.get('defect_mapping')):
        issues.append(f'C{cycle:02d}R{r} EVM前后/缺陷映射不足')

    matrix = d.get('hetu_luoshu_matrix') or d.get('hetu_luoshu') or {}
    if not matrix:
        issues.append(f'C{cycle:02d}R{r} 河图洛书状态缺失')
    gh = d.get('github_factory') or {}
    if not gh:
        issues.append(f'C{cycle:02d}R{r} GitHub工厂状态缺失')
    if not d.get('next_gate') and r < 5:
        issues.append(f'C{cycle:02d}R{r} 下一回合入口门禁缺失')

shortboards = []
sources = []
full = True
for d in evidences:
    apex = d.get('apex_total_formula') or d.get('apex') or {}
    shortboards.append(apex.get('shortboard_exposed') or apex.get('exposes') or '')
    learning = d.get('external_learning') or {}
    sources.append(learning.get('url') or learning.get('source_title') or '')
    gh = d.get('github_factory') or {}
    matrix = d.get('hetu_luoshu_matrix') or d.get('hetu_luoshu') or {}
    matrix_s = str(matrix)
    gh_s = str(gh)
    if '远程多模型' not in matrix_s or '未参与' in matrix_s:
        full = False
    if not (gh.get('run_id') or 'run_id' in gh_s or 'runs' in gh_s):
        full = False

if len(set(shortboards)) == 1:
    issues.append('5个短板完全相同或模板化')
if len(set(sources)) == 1:
    issues.append('外部学习来源全部相同')

hard_fail = any('缺回合证据' in i or '状态不合格' in i or '短板完全相同' in i or '缺两个循环' in i or '下一回合入口门禁' in i for i in issues)
status = '完整真实周期' if not issues and full else ('阻塞' if hard_fail else '部分完成 / 证据不足')

audit = {
    'cycle': cycle,
    'audited_at': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'status': status,
    'rounds_found': len(evidences),
    'issues': issues,
    'shortboard_unique_count': len(set(shortboards)),
    'source_unique_count': len(set(sources)),
    'full_true_cycle_allowed': status == '完整真实周期',
    'boundary': 'GitHub工厂缺失或河图洛书非远程多模型时不能标完整真实周期；缺loops/next_gate等硬证据则审计不通过。'
}

(root / f'cycle_{cycle:02d}_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
st = json.loads(state_path.read_text(encoding='utf-8'))
st['last_cycle_audit'] = str((root / f'cycle_{cycle:02d}_audit.json').relative_to(pathlib.Path('/Users/appleoppa/.hermes/workspace/github-evolution')))
st['last_cycle_audit_status'] = status
if status == '阻塞':
    st['status'] = 'blocked'
    st['blocked_gate'] = '周期总审计未通过'
    st['blocked_at'] = audit['audited_at']
state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(audit, ensure_ascii=False, indent=2))
