#!/usr/bin/env python3
"""Guard Feedback — Claude Code PostToolUse/PreToolUse hook entry point.

Harness-level skeleton. In Towow this is a ~270-line orchestrator that
routes file edits to ADR-030 context fragments and runs guards. In
wow-harness it ships as a minimal default-noop that reads project
configuration from `.wow-harness/issue-adapter.yaml` and only acts
when the consuming project has declared something to do.

Config schema (`.wow-harness/issue-adapter.yaml`):

    # All fields optional. Missing file = pure noop.
    enabled: true                    # master switch, default false
    fragments_dir: scripts/fragments # where to load context fragments from
    routes:
      - pattern: "backend/**/*.py"   # glob
        fragment: "backend-rules.md" # file under fragments_dir
    guards:
      - path_pattern: "backend/**"
        script: scripts/checks/check_api_types.py  # must exit 0 on pass
    metrics_file: .wow-harness/state/metrics/guard-events.jsonl

Default behavior (no config / enabled: false):
    - Read stdin JSON, drop it, exit 0 silently.

This design follows ADR-043 §4 L1 default-opt-in-off rule: harness hooks
never fail a third-party project that hasn't consented to them.

Usage:
    # Normal PostToolUse
    echo '{...}' | python3 scripts/guard-feedback.py

    # PreToolUse read-only
    echo '{...}' | python3 scripts/guard-feedback.py --check-only --once

    # CLI dry-run (debugging)
    python3 scripts/guard-feedback.py --dry-run path/to/file.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from fnmatch import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".wow-harness" / "issue-adapter.yaml"
DEFAULT_METRICS_FILE = REPO_ROOT / ".wow-harness" / "state" / "metrics" / "guard-events.jsonl"


def _load_config() -> dict:
    """Load issue-adapter.yaml. Returns empty dict if missing or unparseable."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml  # optional dep; missing → treat as no config
    except ImportError:
        return {}
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def emit_metric(event: str, metrics_file: Path, **data) -> None:
    """Append JSONL metric line. Never raises — observability must not break hooks."""
    try:
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session_pid": os.getppid(),
            "event": event,
            **data,
        }
        with open(metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_stdin_payload() -> dict:
    """Read Claude Code hook stdin JSON. Returns {} if no input."""
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _extract_file_path(payload: dict) -> str | None:
    """Extract file path from CC hook payload, handling Edit/Write/Read shapes."""
    tool_input = payload.get("tool_input", {})
    for key in ("file_path", "notebook_path", "path"):
        if key in tool_input:
            return tool_input[key]
    return None


def _run_guards_for(file_path: str, guards: list[dict], check_only: bool) -> list[str]:
    """Run each matching guard; return list of blocking failure messages."""
    failures: list[str] = []
    for guard in guards:
        pattern = guard.get("path_pattern", "")
        if not pattern or not fnmatch(file_path, pattern):
            continue
        script = guard.get("script")
        if not script:
            continue
        try:
            result = subprocess.run(
                ["python3", str(REPO_ROOT / script)],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0:
                msg = result.stderr.strip() or result.stdout.strip() or f"{script} exit={result.returncode}"
                failures.append(f"[{script}] {msg}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            if not check_only:
                failures.append(f"[{script}] {exc}")
    return failures


def _inject_fragments_for(file_path: str, config: dict) -> list[str]:
    """Return list of fragment file contents to inject as hook output."""
    fragments_dir = REPO_ROOT / config.get("fragments_dir", "scripts/fragments")
    out: list[str] = []
    for route in config.get("routes", []):
        pattern = route.get("pattern", "")
        if not pattern or not fnmatch(file_path, pattern):
            continue
        frag_file = fragments_dir / route.get("fragment", "")
        if frag_file.exists():
            out.append(frag_file.read_text(encoding="utf-8"))
    return out


def main() -> int:
    argv = sys.argv[1:]
    check_only = "--check-only" in argv
    dry_run = "--dry-run" in argv

    config = _load_config()

    # Default-off: missing config or enabled != true → silent noop
    if not config or not config.get("enabled", False):
        return 0

    metrics_file = Path(config.get("metrics_file", str(DEFAULT_METRICS_FILE)))
    if not metrics_file.is_absolute():
        metrics_file = REPO_ROOT / metrics_file

    if dry_run:
        idx = argv.index("--dry-run")
        file_path = argv[idx + 1] if idx + 1 < len(argv) else None
    else:
        payload = _read_stdin_payload()
        file_path = _extract_file_path(payload)

    if not file_path:
        return 0

    emit_metric("guard_invoked", metrics_file, file=file_path, mode="check" if check_only else "post")

    # Run guards; surface blocking failures via stderr + nonzero exit
    failures = _run_guards_for(file_path, config.get("guards", []), check_only)
    if failures and not check_only:
        for f in failures:
            print(f, file=sys.stderr)
        emit_metric("guard_blocked", metrics_file, file=file_path, count=len(failures))
        return 2

    # Inject fragments as stdout (CC hook injects this into context)
    for frag in _inject_fragments_for(file_path, config):
        print(frag)

    return 0


if __name__ == "__main__":
    sys.exit(main())
