#!/usr/bin/env python3
"""Deploy Guard — Claude Code Bash PreToolUse hook.

Harness-level skeleton. Intercepts Bash commands targeting protected
hosts and forces them through declared update paths. The list of
protected hosts and approved update commands lives in a project-level
YAML file that the harness consumer maintains.

Config schema (`.wow-harness/deploy-allowlist.yaml`):

    # Both lists optional. Missing file or empty lists = fail-closed:
    # no protected hosts are declared, so nothing is blocked — but the
    # guard refuses to silently allow touching a host not in allowlist.
    protected_hosts:
      - host: 203.0.113.42              # IP or hostname
        label: production backend
        reason: |
          Direct mutation breaks systemd-managed deploys.
          Only approved path is: bash scripts/deploy.sh
        approved_commands:
          - pattern: '^bash\\s+scripts/deploy\\.sh(\\s+--(dry-run|yes))*\\s*$'
          - pattern: '^ssh\\s+.*journalctl.*'  # read-only diagnostics
      - host: 198.51.100.7
        label: bridge VPS
        reason: |
          Direct scp/rsync leaves orphan worktrees.
          Only approved path is: git pull via ssh.
        approved_commands:
          - pattern: '^ssh\\s+.*git\\s+(pull|fetch|status).*'

Decision logic:
  1. Parse stdin JSON for Bash command.
  2. For each protected host: does the command reference it?
     - Yes → check against that host's approved_commands patterns.
       - Match → exit 0 (allow).
       - No match → exit 2 (hard block, print host+reason).
     - No → continue.
  3. Command touches no protected host → exit 0 (allow).

**Default behavior (no config file)**: exit 0. The consuming project
has not declared any protected hosts, so the guard has nothing to enforce.
This is opt-in — a brand-new harness install doesn't suddenly start
blocking every SSH command. The fail-closed piece is: once you declare
a host, commands not matching your approved_commands patterns are
blocked, not allowed.

Usage:
    echo '{"tool_name":"Bash","tool_input":{"command":"..."}}' | python3 scripts/deploy-guard.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".wow-harness" / "deploy-allowlist.yaml"


def _load_config() -> dict:
    """Load deploy-allowlist.yaml. Returns empty dict if missing or unparseable."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def get_command() -> str | None:
    """Read Bash command from Claude Code hook stdin JSON."""
    try:
        payload = json.load(sys.stdin)
        return payload.get("tool_input", {}).get("command")
    except (json.JSONDecodeError, EOFError, ValueError):
        return None


def _command_touches(cmd: str, host: str) -> bool:
    """True if the command literally references the host (word-boundary match)."""
    return bool(re.search(rf"(?<![\w.]){re.escape(host)}(?![\w.])", cmd))


def _matches_any(cmd: str, patterns: list[dict]) -> bool:
    """True if cmd matches any of the approved command regex patterns."""
    for p in patterns:
        pat = p.get("pattern", "")
        if not pat:
            continue
        try:
            if re.search(pat, cmd):
                return True
        except re.error:
            continue
    return False


def main() -> int:
    if sys.stdin.isatty():
        return 0

    config = _load_config()
    protected = config.get("protected_hosts", [])

    # Default-off: no config or empty protected list → nothing to enforce
    if not protected:
        return 0

    cmd = get_command()
    if not cmd:
        return 0

    for host_entry in protected:
        host = host_entry.get("host", "")
        if not host:
            continue
        if not _command_touches(cmd, host):
            continue

        approved = host_entry.get("approved_commands", [])
        if _matches_any(cmd, approved):
            return 0

        # Command touches protected host but does NOT match any approved pattern.
        label = host_entry.get("label", host)
        reason = host_entry.get("reason", "no reason declared in allowlist")
        print(
            f"deploy-guard: blocked command touching protected host "
            f"[{label}] ({host}).\n{reason.strip()}",
            file=sys.stderr,
        )
        return 2

    # Touched no protected host
    return 0


if __name__ == "__main__":
    sys.exit(main())
