#!/usr/bin/env python3
"""Back up the latest evolution artifacts to the configured GitHub Gist."""
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
GENES = ROOT / 'genes'
GIST_ID = os.getenv('EVOLUTION_GIST_ID') or os.getenv('GIST_ID') or 'a3537d1e1b113bd4ef215463cc80c760'
GH_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
PHI_STEP = float(os.getenv('PHI_RATIO_STEP', '0.05'))


def now() -> str:
    return dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def latest(pattern: str, folder: pathlib.Path) -> pathlib.Path | None:
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_json(path: pathlib.Path | None) -> Any:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def patch_gist(files: dict[str, str]) -> dict[str, Any]:
    if not GH_TOKEN:
        return {'status': 'skipped', 'error': 'missing_GITHUB_TOKEN'}
    body = json.dumps({'files': {name: {'content': content} for name, content in files.items()}}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.github.com/gists/{GIST_ID}',
        data=body,
        headers={
            'Authorization': 'Bearer ' + GH_TOKEN,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'hermes-gist-backup',
        },
        method='PATCH',
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return {'status': 'ok', 'html_url': data.get('html_url'), 'file_count': len(files)}
    except Exception as exc:
        return {'status': 'blocked', 'error_type': type(exc).__name__, 'error': str(exc)[:500]}


def main() -> None:
    inbox_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else latest('evolver_*.json', INBOX)
    if inbox_path is None:
        raise SystemExit('missing inbox')
    if not inbox_path.is_absolute():
        inbox_path = ROOT / inbox_path
    inbox = read_json(inbox_path)
    if not inbox:
        raise SystemExit('missing inbox')
    run_id = inbox.get('run_id') or inbox_path.stem
    analysis_path = RESEARCH / f'{run_id}_gpt55_analysis.json'
    evomap_path = RESEARCH / f'{run_id}_evomap.json'
    genes_path = GENES / f'{run_id}_genes.json'
    analysis = read_json(analysis_path)
    evomap = read_json(evomap_path)
    genes = read_json(genes_path)
    prev_phi = 1.0
    phi_file = RESEARCH / 'phi_ratio_state.json'
    if phi_file.exists():
        try:
            prev_phi = float(json.loads(phi_file.read_text(encoding='utf-8')).get('phi_ratio', 1.0))
        except Exception:
            prev_phi = 1.0
    next_phi = round(prev_phi * (1 + PHI_STEP), 8)
    phi_state = {
        'updated_at': now(),
        'source_run_id': run_id,
        'phi_ratio': next_phi,
        'previous_phi_ratio': prev_phi,
        'step': PHI_STEP,
        'boundary': 'PHI_RATIO 是实验节奏参数，不代表真实能力自动提升；真实提升需评估中心或任务验证。',
    }
    # 不写固定状态文件，避免多路 Actions / 本地 cron 并发时产生 rebase 冲突。
    # 每轮 PHI_RATIO 证据写入独立 gist_backup 结果文件，并同步到 Gist。
    backup = {
        'name': 'hermes-github-evolution-queue',
        'purpose': 'Gist 中转站：轻量任务队列、远程闭环回流索引与最新结果备份',
        'repo': 'https://github.com/appleoppa/hermes-github-evolution',
        'updated_at': now(),
        'latest_run_id': run_id,
        'latest_inbox': str(inbox_path.relative_to(ROOT)),
        'latest_analysis': str(analysis_path.relative_to(ROOT)) if analysis_path.exists() else None,
        'latest_evomap': str(evomap_path.relative_to(ROOT)) if evomap_path.exists() else None,
        'latest_genes': str(genes_path.relative_to(ROOT)) if genes_path.exists() else None,
        'verification': inbox.get('verification'),
        'phi_ratio_state': phi_state,
        'queue': [
            {
                'id': 'seed-001',
                'topic': (analysis or {}).get('gpt55_analysis', {}).get('next_gist_topic') or inbox.get('topic') or 'agent self improvement github actions verification',
                'status': 'ready',
                'source_run_id': run_id,
            }
        ],
        'boundary': 'Gist 备份只保存非密钥摘要、路径索引和下一轮主题；不保存 token 明文。',
    }
    files = {
        'hermes-evolution-gist.json': json.dumps(backup, ensure_ascii=False, indent=2),
        f'{run_id}_summary.json': json.dumps({
            'inbox': inbox,
            'analysis': analysis,
            'evomap': evomap,
            'genes': genes,
            'phi_ratio_state': phi_state,
        }, ensure_ascii=False, indent=2)[:900000],
    }
    result = patch_gist(files)
    log_path = RESEARCH / f'{run_id}_gist_backup.json'
    log_path.write_text(json.dumps({'run_id': run_id, 'generated_at': now(), 'gist_id': GIST_ID, 'result': result, 'phi_ratio_state': phi_state, 'secret_values_printed': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'gist_backup': str(log_path.relative_to(ROOT)), 'status': result.get('status'), 'phi_ratio': next_phi}, ensure_ascii=False))


if __name__ == '__main__':
    main()
