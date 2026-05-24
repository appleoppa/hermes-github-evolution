#!/usr/bin/env python3
"""GitHub Evolver 15分钟自动循环 watchdog.

每15分钟执行一次 evolver.py，将结果推送到远程仓库。
silent watchdog 模式：只在有新基因或错误时输出。
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path.home() / ".hermes/workspace/github-evolution"
EVOLVER_SCRIPT = WORKSPACE / "scripts/evolver.py"
INBOX = WORKSPACE / "inbox"

def run():
    os.chdir(WORKSPACE)
    
    # 设置 GitHub token 环境变量用于 git push
    env = os.environ.copy()
    gh_token = env.get('GITHUB_TOKEN') or env.get('GH_TOKEN')
    if not gh_token:
        print("❌ 缺少 GITHUB_TOKEN 或 GH_TOKEN 环境变量")
        sys.exit(1)
    
    # 记录执行前 inbox 文件数
    before = len(list(INBOX.glob("evolver_*.json")))
    
    # 执行 evolver
    result = subprocess.run(
        ["python3", str(EVOLVER_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=300,
        env=env
    )
    
    # 记录执行后 inbox 文件数
    after = len(list(INBOX.glob("evolver_*.json")))
    new_genes = after - before
    
    # git add + commit
    subprocess.run(["git", "add", "."], check=False)
    commit_msg = f"chore: evolver auto cycle {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    commit_result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
    
    # 只在有新提交时才 push
    if commit_result.returncode == 0:
        # 使用 gh CLI 推送（自动使用 GH_TOKEN）
        push_result = subprocess.run(
            ["bash", "-c", f"source ~/.hermes/.env && export GH_TOKEN && git push https://${{GH_TOKEN}}@github.com/appleoppa/hermes-github-evolution.git main"],
            capture_output=True,
            text=True,
            env=env
        )
        if push_result.returncode != 0:
            print(f"⚠️  推送失败: {push_result.stderr}")
    
    # silent watchdog: 只在有新基因或错误时输出
    if result.returncode != 0:
        print(f"❌ Evolver 执行失败 (exit {result.returncode})")
        print(result.stderr)
        sys.exit(1)
    elif new_genes > 0:
        print(f"✅ 新增 {new_genes} 条基因，已推送到远程仓库")
    # 否则静默（无输出 = 无通知）

if __name__ == "__main__":
    run()
