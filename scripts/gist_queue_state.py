#!/usr/bin/env python3
"""Gist queue state helper for Hermes GitHub evolution.

Boundary: no secrets printed, no model calls, no repo mutation. It only reads/writes
Gist queue metadata with lease/backoff/quarantine semantics.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
GIST_ID = os.getenv("EVOLUTION_GIST_ID") or os.getenv("GIST_ID") or "a3537d1e1b113bd4ef215463cc80c760"
GH_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
RUN_ID = os.getenv("GITHUB_RUN_ID") or os.getenv("RUN_ID") or "local-" + dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
LEASE_MINUTES = int(os.getenv("EVOLUTION_QUEUE_LEASE_MINUTES", "45"))
MAX_ATTEMPTS = int(os.getenv("EVOLUTION_QUEUE_MAX_ATTEMPTS", "4"))


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(t: dt.datetime) -> str:
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not GH_TOKEN:
        raise RuntimeError("missing_GITHUB_TOKEN")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + GH_TOKEN,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "hermes-gist-queue-state",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_queue() -> tuple[dict[str, Any], str]:
    data = request_json(f"https://api.github.com/gists/{GIST_ID}")
    file_meta = (data.get("files") or {}).get("hermes-evolution-gist.json") or {}
    content = file_meta.get("content")
    if content is None and file_meta.get("raw_url"):
        req = urllib.request.Request(file_meta["raw_url"], headers={"User-Agent": "hermes-gist-queue-state"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    if not content:
        content = "{}"
    try:
        obj = json.loads(content)
    except Exception:
        obj = {"queue": [], "parse_error": True}
    return obj, content


def patch_queue(obj: dict[str, Any]) -> dict[str, Any]:
    obj["queue_state_updated_at"] = iso(now())
    payload = {"files": {"hermes-evolution-gist.json": {"content": json.dumps(obj, ensure_ascii=False, indent=2)}}}
    last_error = None
    for attempt in range(1, 4):
        try:
            return request_json(f"https://api.github.com/gists/{GIST_ID}", method="PATCH", payload=payload)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")[:500]
            last_error = RuntimeError(f"HTTPError {exc.code}: {body}")
            if exc.code in {409, 429, 500, 502, 503, 504}:
                time.sleep(attempt * 2)
                continue
            raise last_error
        except Exception as exc:
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"patch_queue_failed_after_retries: {last_error}")


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def default_queue(obj: dict[str, Any]) -> list[dict[str, Any]]:
    q = obj.get("queue")
    if isinstance(q, list) and q:
        return q
    return [{
        "id": "seed-001",
        "topic": obj.get("latest_topic") or "agent self improvement github actions verification",
        "status": "ready",
        "attempt": 0,
        "priority": 3,
        "created_at": iso(now()),
    }]


def ensure_queue_policy(obj: dict[str, Any]) -> None:
    obj["queue_policy"] = {
        "states": ["ready", "claimed", "running", "completed", "failed", "backoff", "quarantined"],
        "lease_minutes": LEASE_MINUTES,
        "max_attempts": MAX_ATTEMPTS,
        "backoff_minutes": "15 * 2^(attempt-1), capped at 360",
        "boundary": "Gist queue state carries metadata only; no secrets, no full prompts, no trusted DB semantics.",
    }


def claim() -> dict[str, Any]:
    obj, before = fetch_queue()
    q = default_queue(obj)
    current = now()
    selected = None
    for item in q:
        if not isinstance(item, dict):
            continue
        status = item.get("status") or "ready"
        lease_until = parse_time(item.get("lease_until"))
        attempts = int(item.get("attempt", 0) or 0)
        if attempts >= MAX_ATTEMPTS:
            item["status"] = "quarantined"
            item["quarantine_reason"] = "max_attempts_exceeded"
            continue
        if status in {"ready", "pending", "queued", "failed"} or (status in {"claimed", "running"} and lease_until and lease_until < current):
            selected = item
            break
    if selected is None:
        selected = {
            "id": "idle-" + current.strftime("%Y%m%d%H%M%S"),
            "topic": obj.get("latest_topic") or "agent self improvement github actions verification",
            "status": "ready",
            "attempt": 0,
            "priority": 1,
            "created_at": iso(current),
        }
        q.append(selected)
    selected["status"] = "claimed"
    selected["claimed_by"] = RUN_ID
    selected["lease_until"] = iso(current + dt.timedelta(minutes=LEASE_MINUTES))
    selected["attempt"] = int(selected.get("attempt", 0) or 0) + 1
    selected["last_claimed_at"] = iso(current)
    obj["queue"] = q
    ensure_queue_policy(obj)
    patch_queue(obj)
    return {"status": "claimed", "task": selected, "queue_hash_before": str(abs(hash(before)))}


def complete(success: bool) -> dict[str, Any]:
    obj, _ = fetch_queue()
    q = default_queue(obj)
    current = now()
    found = False
    for item in q:
        if not isinstance(item, dict):
            continue
        if item.get("claimed_by") == RUN_ID or item.get("status") in {"claimed", "running"}:
            found = True
            if success:
                item["status"] = "completed"
                item["completed_at"] = iso(current)
            else:
                attempts = int(item.get("attempt", 0) or 0)
                if attempts >= MAX_ATTEMPTS:
                    item["status"] = "quarantined"
                    item["quarantine_reason"] = "max_attempts_exceeded_or_cycle_failed"
                else:
                    item["status"] = "backoff"
                    delay = min(360, 15 * (2 ** max(0, attempts - 1)))
                    item["next_retry_at"] = iso(current + dt.timedelta(minutes=delay))
                    item["last_failure_at"] = iso(current)
            item["lease_until"] = None
            break
    obj["queue"] = q
    ensure_queue_policy(obj)
    patch_queue(obj)
    return {"status": "completed" if success else "failed_recorded", "found": found}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "claim"
    try:
        if mode == "claim":
            result = claim()
        elif mode == "complete":
            result = complete(True)
        elif mode == "fail":
            result = complete(False)
        else:
            raise SystemExit("usage: gist_queue_state.py [claim|complete|fail]")
        log = LOGS / f"queue_state_{RUN_ID}_{mode}.json"
        log.write_text(json.dumps({"mode": mode, "result": result, "secret_values_printed": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"queue_state": mode, "status": result.get("status"), "log": str(log.relative_to(ROOT))}, ensure_ascii=False))
    except Exception as exc:
        log = LOGS / f"queue_state_{RUN_ID}_{mode}_error.json"
        log.write_text(json.dumps({"mode": mode, "error_type": type(exc).__name__, "error": str(exc)[:500], "secret_values_printed": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"queue_state": mode, "status": "error", "error_type": type(exc).__name__, "log": str(log.relative_to(ROOT))}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
