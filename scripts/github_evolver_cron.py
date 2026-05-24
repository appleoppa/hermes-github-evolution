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
    
    # 记录执行前 inbox 文件数
    before = len(list(INBOX.glob("evolver_*.json")))
    
    # 执行 evolver
    result = subprocess.run(
        ["python3", str(EVOLVER_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    # 记录执行后 inbox 文件数
    after = len(list(INBOX.glob("evolver_*.json")))
    new_genes = after - before
    
    # git add + commit + push
    subprocess.run(["git", "add", "."], check=False)
    commit_msg = f"chore: evolver auto cycle {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=False)
    subprocess.run(["git", "push"], check=False)
    
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
