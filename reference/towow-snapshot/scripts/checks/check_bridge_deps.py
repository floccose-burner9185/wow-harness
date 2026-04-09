"""Check bridge local-test infrastructure and deploy-time dependencies.

Mechanises ADR-026 Rule 4: "生产不能是第一个集成环境。
本地必须能用 fake CLI + 真实 HTTP backend 跑完整链。"

Also validates that bridge_contract/ (top-level package) exists and provides
the modules imported by backend/product/bridge/, preventing deploy-time
ModuleNotFoundError (guard-20260404-0800).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.checks import Finding

_BRIDGE_DIR = "bridge_agent"
_TEST_FILE = f"{_BRIDGE_DIR}/test_progress.py"
_CONFIG_FILE = f"{_BRIDGE_DIR}/config.yaml"

_CATEGORY = "bridge_boundary"
_SKILLS = ["towow-bridge", "towow-ops"]


def _staged_files() -> list[str]:
    """Return list of staged file paths (relative to repo root)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=_REPO_ROOT,
        )
        return result.stdout.strip().splitlines() if result.returncode == 0 else []
    except FileNotFoundError:
        return []


def _has_bridge_changes(files: list[str]) -> bool:
    return any(f.startswith(f"{_BRIDGE_DIR}/") for f in files)


def _has_config_change(files: list[str]) -> bool:
    return _CONFIG_FILE in files


def _check_test_exists(repo_root: Path) -> list[Finding]:
    """Check that bridge_agent/test_progress.py exists and is non-empty."""
    test_path = repo_root / _TEST_FILE
    if not test_path.exists():
        return [Finding(
            severity="P1",
            message="Bridge 代码变更但缺少本地测试: test_progress.py 不存在",
            file=_TEST_FILE,
            blocking=True,
            category=_CATEGORY,
            problem_class="missing_test_infra",
            required_skills=_SKILLS,
            required_reads=[f"{_BRIDGE_DIR}/"],
        )]
    if test_path.stat().st_size == 0:
        return [Finding(
            severity="P1",
            message="Bridge 本地测试文件为空: test_progress.py 存在但无内容",
            file=_TEST_FILE,
            blocking=True,
            category=_CATEGORY,
            problem_class="missing_test_infra",
            required_skills=_SKILLS,
            required_reads=[_TEST_FILE],
        )]
    return []


def _check_config_sync(files: list[str]) -> list[Finding]:
    """Warn when config.yaml changes — server side may need sync."""
    if not _has_config_change(files):
        return []
    return [Finding(
        severity="P2",
        message="bridge config.yaml 已变更，检查 server 端配置是否需要同步",
        file=_CONFIG_FILE,
        blocking=False,
        category=_CATEGORY,
        problem_class="config_drift",
        required_skills=_SKILLS,
        required_reads=[_CONFIG_FILE, "backend/product/bridge/"],
    )]


def _check_bridge_contract_package(repo_root: Path) -> list[Finding]:
    """Verify bridge_contract/ package exists and provides all imported modules.

    Scans backend/product/bridge/*.py for 'from bridge_contract.X import ...'
    and checks that bridge_contract/X.py exists. Prevents deploy-time
    ModuleNotFoundError when deploy.sh syncs to production.
    """
    findings: list[Finding] = []
    contract_dir = repo_root / "bridge_contract"

    # 1. Package directory must exist
    if not contract_dir.is_dir():
        findings.append(Finding(
            severity="P0",
            message="bridge_contract/ 顶层包目录不存在 — 部署后 bridge 路由将 500",
            file="bridge_contract/",
            blocking=True,
            category=_CATEGORY,
            problem_class="missing_deploy_dep",
            required_skills=_SKILLS,
            required_reads=["bridge_contract/", "scripts/deploy.sh"],
        ))
        return findings

    # 2. Scan imports from backend/product/bridge/
    bridge_service_dir = repo_root / "backend" / "product" / "bridge"
    if not bridge_service_dir.is_dir():
        return findings

    import_pattern = re.compile(r"^from\s+bridge_contract\.(\w+)\s+import", re.MULTILINE)
    required_modules: set[str] = set()

    for py_file in bridge_service_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        for match in import_pattern.finditer(content):
            required_modules.add(match.group(1))

    # 3. Check each required module exists as bridge_contract/<module>.py
    for mod_name in sorted(required_modules):
        mod_path = contract_dir / f"{mod_name}.py"
        if not mod_path.exists():
            rel_file = f"bridge_contract/{mod_name}.py"
            findings.append(Finding(
                severity="P0",
                message=f"bridge_contract/{mod_name}.py 不存在但被 backend/product/bridge/ 导入",
                file=rel_file,
                blocking=True,
                category=_CATEGORY,
                problem_class="missing_deploy_dep",
                required_skills=_SKILLS,
                required_reads=[rel_file, "backend/product/bridge/"],
            ))

    return findings


def run(repo_root: Path, mode: str = "full") -> list[Finding]:
    findings: list[Finding] = []

    if mode == "full":
        # Always check test file existence regardless of changes
        findings.extend(_check_test_exists(repo_root))
        # Always check bridge_contract package integrity
        findings.extend(_check_bridge_contract_package(repo_root))
        return findings

    # mode="staged" or mode="ci": only check when bridge files are touched
    staged = _staged_files()
    if not _has_bridge_changes(staged):
        return findings

    findings.extend(_check_test_exists(repo_root))
    findings.extend(_check_config_sync(staged))
    # Also verify bridge_contract when bridge code changes
    findings.extend(_check_bridge_contract_package(repo_root))
    return findings


if __name__ == "__main__":
    results = run(_REPO_ROOT)
    for f in results:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.severity}] {loc}: {f.message}")
    print(f"\n--- {len(results)} findings ---")
    sys.exit(1 if any(f.blocking for f in results) else 0)
