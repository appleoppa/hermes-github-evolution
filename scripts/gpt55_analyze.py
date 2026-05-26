#!/usr/bin/env python3
"""Analyze an evolver inbox with GPT-5.5 and write a non-secret report."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
INBOX = ROOT / 'inbox'
RESEARCH = ROOT / 'research'
API_KEY = os.getenv('GPT55_5YUANTOKEN_API_KEY')
BASE_URL = os.getenv('GPT55_BASE_URL', 'https://chuangagent.eu.cc/v1').rstrip('/')
MODEL = os.getenv('GPT55_MODEL', 'gpt-5.5')


def now() -> str:
    return dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def latest_inbox() -> pathlib.Path:
    files = sorted(INBOX.glob('evolver_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit('missing evolver inbox')
    return files[0]


def compact_payload(data: dict[str, Any]) -> dict[str, Any]:
    genes = data.get('genes') or []
    repos = data.get('selected_repositories') or []
    return {
        'run_id': data.get('run_id'),
        'generated_at': data.get('generated_at'),
        'topic': data.get('topic'),
        'requested_topic': data.get('requested_topic'),
        'mode': data.get('mode'),
        'verification': data.get('verification'),
        'evomap_route': [x.get('node') for x in (data.get('evomap') or {}).get('route', [])],
        'dominant_traits': (data.get('evomap') or {}).get('dominant_traits'),
        'repositories': [
            {
                'name': r.get('name'),
                'url': r.get('url'),
                'stars': r.get('stars'),
                'signals': {
                    'languages': (r.get('signals') or {}).get('languages'),
                    'sampled_paths': (r.get('signals') or {}).get('sampled_paths'),
                    'workflow_files': (r.get('signals') or {}).get('workflow_files'),
                },
            }
            for r in repos[:5]
        ],
        'genes': [
            {
                'repo': g.get('repo'),
                'traits': g.get('traits'),
                'verification': g.get('verification'),
                'boundary': g.get('boundary'),
            }
            for g in genes[:5]
        ],
        'boundary': data.get('boundary'),
    }


def call_gpt(payload: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        return {
            'status': 'skipped',
            'reason': 'missing_GPT55_5YUANTOKEN_API_KEY',
            'analysis': '未调用 GPT-5.5：缺少密钥。',
        }
    system = '你是 Hermes GitHub 自进化审查器。只根据输入 JSON 输出严格 JSON，不编造事实，不输出任何密钥。'
    user = {
        'task': '分析本轮 GitHub evolver/evomap 结果，提炼可执行进化基因、风险、下一轮 Gist 任务建议。必须区分已验证事实与未验证假设。',
        'required_schema': {
            'status': 'ok|partial|blocked',
            'verified_facts': ['string'],
            'candidate_genes': [{'name': 'string', 'source_repo': 'string', 'reuse_rule': 'string', 'evidence': ['string'], 'risk': 'string'}],
            'risks': ['string'],
            'next_gist_topic': 'string',
            'phi_ratio_note': 'string',
            'boundary': 'string'
        },
        'payload': payload,
    }
    body = json.dumps({
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)},
        ],
        'temperature': 0.2,
    }).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL + '/chat/completions',
        data=body,
        headers={
            'Authorization': 'Bearer ' + API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'hermes-gpt55-analyzer',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
        content = raw.get('choices', [{}])[0].get('message', {}).get('content', '')
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {'status': 'partial', 'raw_analysis': content[:4000]}
        parsed['provider'] = 'gpt55_5yuantoken'
        parsed['model'] = MODEL
        return parsed
    except Exception as exc:
        return {
            'status': 'blocked',
            'error_type': type(exc).__name__,
            'error': str(exc)[:500],
            'boundary': 'GPT-5.5 调用失败，本轮只保留 evolver 原始结果。',
        }


def main() -> None:
    inbox_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else latest_inbox()
    if not inbox_path.is_absolute():
        inbox_path = ROOT / inbox_path
    data = json.loads(inbox_path.read_text(encoding='utf-8'))
    payload = compact_payload(data)
    analysis = call_gpt(payload)
    run_id = data.get('run_id') or inbox_path.stem
    out = {
        'run_id': run_id,
        'source_inbox': str(inbox_path.relative_to(ROOT)),
        'generated_at': now(),
        'secret_values_printed': False,
        'input_summary': payload,
        'gpt55_analysis': analysis,
    }
    out_path = RESEARCH / f'{run_id}_gpt55_analysis.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'analysis': str(out_path.relative_to(ROOT)), 'status': analysis.get('status')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
