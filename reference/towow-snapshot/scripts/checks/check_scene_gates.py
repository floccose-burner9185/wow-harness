"""Check scene component existence and documentation fidelity.

For live/demo scenes: landing, onboarding, dashboard components must exist.
For demo scenes: docs must not claim "real protocol" capabilities.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.checks import Finding

# Parse scene-config.ts for scene IDs and status
_STATUS_PATTERN = re.compile(r'status:\s*["\'](\w[\w-]*)["\']')
_SCENE_BLOCK = re.compile(r'"([\w-]+)":\s*\{')

# Component directories
_COMPONENT_DIRS = {
    "landings": "website/components/scene/landings",
    "onboardings": "website/components/scene/onboardings",
    "dashboards": "website/components/scene/dashboards",
}

# Over-promise patterns for demo scenes
_OVER_PROMISE_PATTERNS = [
    re.compile(r'真实.{0,4}(?:协议|发现|协商|调用)', re.IGNORECASE),
    re.compile(r'\*\*真实\*\*', re.IGNORECASE),
    re.compile(r'real\s+(?:protocol|matching|negotiation)', re.IGNORECASE),
]


def _parse_scenes(repo_root: Path) -> dict[str, str]:
    """Parse scene-config.ts to extract {sceneId: status}."""
    config_path = repo_root / "website" / "lib" / "scene-config.ts"
    if not config_path.exists():
        return {}

    content = config_path.read_text(encoding="utf-8")
    scenes: dict[str, str] = {}
    current_scene = None

    for line in content.splitlines():
        block_m = _SCENE_BLOCK.search(line)
        if block_m:
            current_scene = block_m.group(1)

        if current_scene:
            status_m = _STATUS_PATTERN.search(line)
            if status_m:
                scenes[current_scene] = status_m.group(1)
                current_scene = None

    return scenes


def _check_components(scene_id: str, status: str, repo_root: Path) -> list[Finding]:
    """Check component existence for live/demo scenes."""
    if status == "coming-soon":
        return []

    findings: list[Finding] = []
    # Convert scene-id to PascalCase for component name
    pascal = "".join(w.capitalize() for w in scene_id.split("-"))

    for kind, dir_path in _COMPONENT_DIRS.items():
        comp_dir = repo_root / dir_path
        if not comp_dir.is_dir():
            continue
        # Look for a file matching the scene
        matches = list(comp_dir.glob(f"{pascal}*"))
        if not matches:
            findings.append(Finding(
                severity="P1",
                message=f"Scene '{scene_id}' (status={status}) missing {kind} component in {dir_path}/",
                file=dir_path,
            ))

    return findings


def _check_doc_promises(scene_id: str, status: str, repo_root: Path) -> list[Finding]:
    """Check that demo scene docs don't over-promise."""
    if status != "demo":
        return []

    findings: list[Finding] = []
    # Check scenes/<scene-id>/ directory
    scene_dir = repo_root / "scenes" / scene_id
    if not scene_dir.is_dir():
        return findings

    for md in scene_dir.rglob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
        except OSError:
            continue

        rel = str(md.relative_to(repo_root))
        for line_num, line in enumerate(content.splitlines(), 1):
            if "~~" in line:
                continue
            for pattern in _OVER_PROMISE_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(
                        severity="P1",
                        message=f"Demo scene '{scene_id}' doc claims real protocol: {line.strip()[:80]}",
                        file=rel,
                        line=line_num,
                    ))

    return findings


def run(repo_root: Path, mode: str = "full") -> list[Finding]:
    findings: list[Finding] = []

    scenes = _parse_scenes(repo_root)
    if not scenes:
        findings.append(Finding(
            severity="P0",
            message="Cannot parse scene-config.ts — no scenes found",
            file="website/lib/scene-config.ts",
        ))
        return findings

    for scene_id, status in scenes.items():
        findings.extend(_check_components(scene_id, status, repo_root))
        findings.extend(_check_doc_promises(scene_id, status, repo_root))

    return findings


if __name__ == "__main__":
    results = run(_REPO_ROOT)
    for f in results:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.severity}] {loc}: {f.message}")
    print(f"\n--- {len(results)} findings ---")
    sys.exit(1 if any(f.severity == "P0" for f in results) else 0)
