#!/usr/bin/env python3
"""Hermes GitHub Evolver.

Remote-container evolution worker:
- search real GitHub projects through API;
- fetch repository metadata / top files / workflow signals;
- extract reusable engineering genes;
- write structured inbox result and gene files for host回流.

No secrets are printed or stored.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import pathlib
import textwrap
import urllib.parse
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
INBOX = ROOT / 'inbox'
GENES = ROOT / 'genes'
RESEARCH = ROOT / 'research'
TASKS = ROOT / 'tasks'
for d in (INBOX, GENES, RESEARCH, TASKS):
    d.mkdir(exist_ok=True)

TOPIC = os.getenv('EVOLUTION_TOPIC', 'ai agent eval harness autonomous coding workflows')
GIST_ID = os.getenv('EVOLUTION_GIST_ID') or os.getenv('GIST_ID') or 'a3537d1e1b113bd4ef215463cc80c760'
RUN_ID = 'evolver_' + dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
GH_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')


def now() -> str:
    return dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def request_json(url: str) -> dict[str, Any]:
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'hermes-evolver'}
    if GH_TOKEN:
        headers['Authorization'] = 'Bearer ' + GH_TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def request_text(url: str) -> str:
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'hermes-evolver'}
    if GH_TOKEN:
        headers['Authorization'] = 'Bearer ' + GH_TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def load_gist_queue(gist_id: str) -> dict[str, Any]:
    if not gist_id:
        return {'enabled': False, 'queue': [], 'error': 'missing_gist_id'}
    try:
        data = request_json(f'https://api.github.com/gists/{gist_id}')
        files = data.get('files') or {}
        parsed_files = []
        queue_items = []
        for name, meta in files.items():
            content = meta.get('content')
            if content is None and meta.get('raw_url'):
                content = request_text(meta['raw_url'])
            content = content or ''
            parsed_files.append({'name': name, 'sha256': hashlib.sha256(content.encode()).hexdigest()})
            json_start = content.find('{')
            if json_start >= 0:
                try:
                    obj = json.loads(content[json_start:])
                    if isinstance(obj, dict):
                        queue_items.extend(obj.get('queue') or [])
                except Exception:
                    pass
        return {
            'enabled': True,
            'gist_id': gist_id,
            'html_url': data.get('html_url'),
            'files': parsed_files,
            'queue': queue_items,
            'queue_count': len(queue_items),
            'fetched_at': now(),
        }
    except Exception as exc:
        return {'enabled': True, 'gist_id': gist_id, 'queue': [], 'error': type(exc).__name__ + ': ' + str(exc)[:240]}


def topic_from_gist(default_topic: str, gist_queue: dict[str, Any]) -> str:
    for item in gist_queue.get('queue') or []:
        if isinstance(item, dict) and item.get('status') in {'ready', 'pending', 'queued'} and item.get('topic'):
            return str(item['topic'])
    return default_topic

def search_repositories(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = urllib.parse.quote(query)
    url = f'https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={limit}'
    data = request_json(url)
    return data.get('items', [])[:limit]


def repo_languages(full_name: str) -> dict[str, int]:
    try:
        return request_json(f'https://api.github.com/repos/{full_name}/languages')
    except Exception:
        return {}


def repo_contents(full_name: str, path: str = '') -> list[dict[str, Any]]:
    try:
        data = request_json(f'https://api.github.com/repos/{full_name}/contents/{urllib.parse.quote(path)}')
        return data if isinstance(data, list) else []
    except Exception:
        return []


def fetch_small_text(full_name: str, path: str, max_chars: int = 12000) -> str:
    try:
        data = request_json(f'https://api.github.com/repos/{full_name}/contents/{urllib.parse.quote(path)}')
        if data.get('encoding') == 'base64' and data.get('content'):
            raw = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
            return raw[:max_chars]
    except Exception:
        return ''
    return ''


def discover_signals(repo: dict[str, Any]) -> dict[str, Any]:
    full_name = repo['full_name']
    root = repo_contents(full_name)
    root_names = {x.get('name') for x in root if x.get('name')}
    signal_paths = []
    for candidate in ['README.md', 'pyproject.toml', 'package.json', 'AGENTS.md', 'CLAUDE.md', 'CONTRIBUTING.md']:
        if candidate in root_names:
            signal_paths.append(candidate)
    workflow_files = []
    for wf in repo_contents(full_name, '.github/workflows'):
        name = wf.get('name') or ''
        if name.endswith(('.yml', '.yaml')):
            workflow_files.append('.github/workflows/' + name)
            if len(workflow_files) >= 3:
                break
    signal_paths.extend(workflow_files[:2])

    texts = {}
    for p in signal_paths[:5]:
        t = fetch_small_text(full_name, p)
        if t:
            texts[p] = t[:4000]
    return {
        'languages': repo_languages(full_name),
        'root_signal_files': sorted(root_names)[:60],
        'sampled_paths': list(texts.keys()),
        'sampled_text_hashes': {p: hashlib.sha256(t.encode()).hexdigest() for p, t in texts.items()},
        'sampled_text_excerpt': {p: t[:900] for p, t in texts.items()},
    }


def extract_gene(repo: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    full = repo['full_name']
    sampled = ' '.join((signals.get('sampled_text_excerpt') or {}).values()).lower()
    workflows = [p for p in signals.get('sampled_paths', []) if p.startswith('.github/workflows/')]
    traits = []
    if 'eval' in sampled or 'benchmark' in sampled:
        traits.append('evaluation_gate')
    if 'pytest' in sampled or 'test' in sampled or workflows:
        traits.append('automated_test_gate')
    if 'agent' in sampled or 'tool' in sampled:
        traits.append('agent_tooling_pattern')
    if 'docker' in sampled or 'container' in sampled:
        traits.append('container_reproducibility')
    if not traits:
        traits.append('high_signal_reference')
    rule = '；'.join([
        f'参考 {full} 的公开工程信号',
        '先抽取可验证文件/工作流/测试门禁，再沉淀为本地基因',
        '没有读到真实文件内容时不得声称吸收代码能力'
    ])
    return {
        'repo': full,
        'url': repo.get('html_url'),
        'stars': repo.get('stargazers_count'),
        'language': repo.get('language'),
        'traits': traits,
        'mechanism': rule,
        'verification': {
            'api_repo_metadata': True,
            'languages_fetched': bool(signals.get('languages')),
            'sampled_paths': signals.get('sampled_paths'),
            'workflow_files_seen': workflows,
            'text_hashes': signals.get('sampled_text_hashes'),
        },
        'boundary': '公开仓库信号吸收；未复制密钥、未声称已完整理解全仓库。'
    }


def build_evomap(genes: list[dict[str, Any]], topic: str) -> dict[str, Any]:
    trait_count: dict[str, int] = {}
    for g in genes:
        for t in g['traits']:
            trait_count[t] = trait_count.get(t, 0) + 1
    route = [
        {'node': 'Gist queue', 'function': '读取轻量任务队列/主题中转'},
        {'node': 'GitHub Actions container', 'function': '远程容器执行检索与基因抽取'},
        {'node': 'GitHub API', 'function': '获取真实仓库元数据/文件/工作流'},
        {'node': 'repository inbox', 'function': '结果提交回仓库，供主机拉取复核'},
        {'node': 'genes', 'function': '可复用规则沉淀'},
        {'node': 'host evolver', 'function': '本地主脑验收、入库、技能更新'}
    ]
    return {
        'version': '1.1',
        'generated_at': now(),
        'topic': topic,
        'route': route,
        'schedule': '*/15 * * * *',
        'analysis_node': 'GPT-5.5 analysis',
        'gist_backup_node': 'Gist backup',
        'phi_ratio_rule': 'PHI_RATIO 每轮按实验参数增加 5%，仅作节奏字段，不代表能力自动提升。',
        'trait_count': trait_count,
        'dominant_traits': sorted(trait_count.items(), key=lambda x: (-x[1], x[0]))[:8],
        'host_reuse_rule': '只有含Gist任务证据、真实API元数据、采样文件路径、内容hash和边界声明的gene，才允许回流为Hermes进化素材。'
    }


def main() -> None:
    gist_queue = load_gist_queue(GIST_ID)
    active_topic = topic_from_gist(TOPIC, gist_queue)
    repos = search_repositories(active_topic + ' stars:>500', limit=8)
    if len(repos) < 3:
        repos = search_repositories('ai agent evaluation framework stars:>500', limit=8)
    selected = []
    genes = []
    for repo in repos[:6]:
        signals = discover_signals(repo)
        gene = extract_gene(repo, signals)
        selected.append({
            'name': repo.get('full_name'),
            'url': repo.get('html_url'),
            'stars': repo.get('stargazers_count'),
            'description': repo.get('description'),
            'updated_at': repo.get('updated_at'),
            'signals': signals,
        })
        genes.append(gene)

    evomap = build_evomap(genes, active_topic)
    report = {
        'run_id': RUN_ID,
        'generated_at': now(),
        'topic': active_topic,
        'requested_topic': TOPIC,
        'mode': 'gist_to_github_actions_evolver_evomap',
        'status': 'completed' if genes else 'no_genes',
        'verification': {
            'gist_queue_used': bool(gist_queue.get('enabled')),
            'gist_queue_count': gist_queue.get('queue_count', 0),
            'gist_error': gist_queue.get('error'),
            'github_api_used': True,
            'repo_count': len(selected),
            'genes_count': len(genes),
            'token_present_in_container': bool(GH_TOKEN),
            'secret_values_printed': False,
            'minimum_gene_gate': all(g['verification']['api_repo_metadata'] and g['verification']['sampled_paths'] for g in genes) if genes else False,
        },
        'gist_queue': gist_queue,
        'evomap': evomap,
        'genes': genes,
        'selected_repositories': selected,
        'boundary': '本次完成 Gist 队列读取、GitHub Actions/本地容器等价检索、GitHub API采样、基因抽取和回流；深度代码迁移需后续针对单仓库逐文件审计和测试。'
    }

    gene_file = GENES / f'{RUN_ID}_genes.json'
    inbox_file = INBOX / f'{RUN_ID}.json'
    evomap_file = RESEARCH / f'{RUN_ID}_evomap.json'
    for p, obj in [(gene_file, {'run_id': RUN_ID, 'genes': genes}), (inbox_file, report), (evomap_file, evomap)]:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'run_id': RUN_ID, 'inbox': str(inbox_file.relative_to(ROOT)), 'genes': len(genes)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
