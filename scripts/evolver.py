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


def build_evomap(genes: list[dict[str, Any]]) -> dict[str, Any]:
    trait_count: dict[str, int] = {}
    for g in genes:
        for t in g['traits']:
            trait_count[t] = trait_count.get(t, 0) + 1
    route = [
        {'node': 'GitHub API', 'function': '获取真实仓库元数据/文件/工作流'},
        {'node': 'Actions container', 'function': '远程容器执行检索与基因抽取'},
        {'node': 'inbox', 'function': '结果回流主机复核'},
        {'node': 'genes', 'function': '可复用规则沉淀'},
        {'node': 'host evolver', 'function': '本地主脑验收、入库、技能更新'}
    ]
    return {
        'version': '1.0',
        'generated_at': now(),
        'topic': TOPIC,
        'route': route,
        'trait_count': trait_count,
        'dominant_traits': sorted(trait_count.items(), key=lambda x: (-x[1], x[0]))[:8],
        'host_reuse_rule': '只有含真实API元数据、采样文件路径、内容hash和边界声明的gene，才允许回流为Hermes进化素材。'
    }


def main() -> None:
    repos = search_repositories(TOPIC + ' stars:>500', limit=8)
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

    evomap = build_evomap(genes)
    report = {
        'run_id': RUN_ID,
        'generated_at': now(),
        'topic': TOPIC,
        'mode': 'github_container_evolver_evomap',
        'status': 'completed' if genes else 'no_genes',
        'verification': {
            'github_api_used': True,
            'repo_count': len(selected),
            'genes_count': len(genes),
            'token_present_in_container': bool(GH_TOKEN),
            'secret_values_printed': False,
            'minimum_gene_gate': all(g['verification']['api_repo_metadata'] and g['verification']['sampled_paths'] for g in genes) if genes else False,
        },
        'evomap': evomap,
        'genes': genes,
        'selected_repositories': selected,
        'boundary': '本次完成远程容器检索、采样、基因抽取和回流；深度代码迁移需后续针对单仓库逐文件审计和测试。'
    }

    gene_file = GENES / f'{RUN_ID}_genes.json'
    inbox_file = INBOX / f'{RUN_ID}.json'
    evomap_file = RESEARCH / f'{RUN_ID}_evomap.json'
    for p, obj in [(gene_file, {'run_id': RUN_ID, 'genes': genes}), (inbox_file, report), (evomap_file, evomap)]:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'run_id': RUN_ID, 'inbox': str(inbox_file.relative_to(ROOT)), 'genes': len(genes)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
