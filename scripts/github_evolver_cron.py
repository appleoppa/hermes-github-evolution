#!/usr/bin/env python3
"""GitHub Evolver 15分钟自动循环 watchdog.

每15分钟执行一次 evolver.py，将结果提交并推送到远程仓库。
silent watchdog 模式：只在有新基因或错误时输出。

状态纪律：
- 本地生成、本地提交、远端推送必须分开判断。
- push 失败必须 exit 1，不能输出“已推送”。
- 不在 stdout/stderr 中输出 token。
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".hermes/workspace/github-evolution"
EVOLVER_SCRIPT = WORKSPACE / "scripts/evolver.py"
INBOX = WORKSPACE / "inbox"
REMOTE = "origin"
BRANCH = "main"


def _run(cmd, *, env=None, timeout=120):
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=WORKSPACE,
    )


def _redact(text: str) -> str:
    redacted = text or ""
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(key)
        if token:
            redacted = redacted.replace(token, "[REDACTED]")
    return redacted


def _load_github_token(env):
    gh_token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if gh_token:
        return gh_token
    env_file = Path.home() / ".hermes" / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if line.startswith("GH_TOKEN=") or line.startswith("GITHUB_TOKEN="):
            gh_token = line.split("=", 1)[1].strip().strip('"').strip("'")
            env["GH_TOKEN"] = gh_token
            env["GITHUB_TOKEN"] = gh_token
            return gh_token
    return None


def _remote_head():
    result = _run(["git", "ls-remote", REMOTE, f"refs/heads/{BRANCH}"])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split()[0]


def run():
    os.chdir(WORKSPACE)
    env = os.environ.copy()
    gh_token = _load_github_token(env)
    if not gh_token:
        print("❌ 缺少 GITHUB_TOKEN 或 GH_TOKEN 环境变量（已尝试 .env 读取）")
        sys.exit(1)

    before = len(list(INBOX.glob("evolver_*.json")))

    result = _run(["python3", str(EVOLVER_SCRIPT)], env=env, timeout=300)
    after = len(list(INBOX.glob("evolver_*.json")))
    new_genes = after - before

    if result.returncode != 0:
        print(f"❌ Evolver 执行失败 (exit {result.returncode})")
        if result.stderr:
            print(_redact(result.stderr)[-1200:])
        sys.exit(1)

    _run(["git", "add", "."], env=env)
    commit_msg = f"chore: evolver auto cycle {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    commit_result = _run(["git", "commit", "-m", commit_msg], env=env)

    committed = commit_result.returncode == 0
    if not committed:
        # 无新提交时保持 silent；如果 evolver 生成了文件但 commit 失败，则报错。
        combined = (commit_result.stdout or "") + (commit_result.stderr or "")
        if new_genes <= 0 and ("nothing to commit" in combined.lower() or "无文件要提交" in combined):
            return
        print("❌ 本地提交失败，未推送远端")
        print(_redact(combined)[-1200:])
        sys.exit(1)

    fetch_result = _run(["git", "fetch", REMOTE, BRANCH], env=env, timeout=180)
    if fetch_result.returncode != 0:
        print("❌ 推送前 fetch 失败，已阻断远端推送")
        print(_redact(fetch_result.stderr)[-1200:])
        sys.exit(1)

    rebase_result = _run(["git", "rebase", f"{REMOTE}/{BRANCH}"], env=env, timeout=180)
    if rebase_result.returncode != 0:
        _run(["git", "rebase", "--abort"], env=env, timeout=60)
        print("❌ 推送前 rebase 失败，已阻断远端推送")
        print(_redact(rebase_result.stderr)[-1200:])
        sys.exit(1)

    push_result = _run(["git", "push", REMOTE, BRANCH], env=env, timeout=180)
    if push_result.returncode != 0:
        print("❌ 远端推送失败，本地已提交但远端未吸收")
        print(_redact(push_result.stderr)[-1200:])
        sys.exit(1)

    local_head = _run(["git", "rev-parse", "HEAD"], env=env).stdout.strip()
    remote_head = _remote_head()
    if not remote_head or remote_head != local_head:
        print("❌ 远端 HEAD 读回不一致，不能确认推送成功")
        print(f"本地HEAD：{local_head}")
        print(f"远端HEAD：{remote_head or 'UNKNOWN'}")
        sys.exit(1)

    if new_genes > 0:
        print(f"✅ 新增 {new_genes} 条基因；本地已提交；远端已读回一致：{local_head[:12]}")


if __name__ == "__main__":
    run()
