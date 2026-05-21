#!/usr/bin/env python3
import json, pathlib, urllib.request, re, hashlib
ROOT = pathlib.Path('/Users/appleoppa/.hermes/workspace/github-evolution')
ep = ROOT / 'cron_cycles/real_runs/ten_cycle_state_machine/evidence/C01_R1.json'
sp = ROOT / 'cron_cycles/real_runs/ten_cycle_state_machine/state.json'
report = json.loads(ep.read_text(encoding='utf-8'))
state = json.loads(sp.read_text(encoding='utf-8'))
url = 'https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/using-workflow-run-logs'
req = urllib.request.Request(url, headers={'User-Agent': 'hermes-cron-evolution'})
with urllib.request.urlopen(req, timeout=30) as r:
    html = r.read().decode('utf-8', 'replace')
text = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S | re.I)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
snippets = []
for phrase in ['Workflow run logs', 'diagnose', 'download', 'Viewing logs']:
    i = text.lower().find(phrase.lower())
    if i >= 0:
        snippets.append(text[max(0, i - 120):i + 260])
report['external_learning'] = {
    'source_title': 'GitHub Docs: Using workflow run logs',
    'url': url,
    'access': 'opened_html_content',
    'sha256': hashlib.sha256(html.encode()).hexdigest(),
    'read_excerpt': snippets[:3],
    'extracted_points': [
        '工作流运行日志用于诊断工作流、作业或步骤失败原因。',
        '排查需要进入具体工作流运行、作业和步骤日志，而不是只确认仓库或文件存在。',
        '日志可查看或下载，适合作为远程工厂证据的一部分，但仍只能证明执行轨迹，不能单独证明进化。'
    ],
    'behavior_change': '下一回合入口必须记录GitHub工厂的run/job/step状态或明确不可用；不能把查询失败包装成完整回合。'
}
report['status_grade'] = '部分完成或证据不足'
report['boundary'] = '外部学习门禁已补齐；GitHub远程工厂仍未跑通，多模型为本地路由演练，因此不推进。'
ep.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
state['history'][-1]['status'] = '部分完成或证据不足'
state['blocked_gate'] = 'GitHub工厂/完整真实性门禁未跑通'
sp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
print('updated external learning; still blocked')
