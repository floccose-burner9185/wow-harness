"""Check MCP Python/Node tool signature parity.

Compares tool names between Python and Node implementations,
and validates auth_begin behavior contract from shared fixture.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.checks import Finding

# Python: match @mcp.tool() followed by optional decorators then async def
_PY_TOOL_PATTERN = re.compile(
    r'@mcp\.tool\(\)\s*\n(?:@\w+\s*\n)*async def (towow_\w+)\(',
    re.MULTILINE,
)

# Node: match registerTool("tool_name"
_NODE_TOOL_PATTERN = re.compile(
    r'registerTool\(\s*"(\w+)"',
)


def _extract_python_tools(repo_root: Path) -> set[str]:
    server_py = repo_root / "mcp-server" / "towow_mcp" / "server.py"
    if not server_py.exists():
        return set()
    content = server_py.read_text(encoding="utf-8")
    return {m.group(1) for m in _PY_TOOL_PATTERN.finditer(content)}


def _extract_node_tools(repo_root: Path) -> set[str]:
    index_ts = repo_root / "mcp-server-node" / "src" / "index.ts"
    if not index_ts.exists():
        return set()
    content = index_ts.read_text(encoding="utf-8")
    return {m.group(1) for m in _NODE_TOOL_PATTERN.finditer(content)}


def _extract_tool_params(content: str, tool_name: str) -> set[str] | None:
    """Extract parameter names from a Python async def signature."""
    pattern = re.compile(
        rf'async def {re.escape(tool_name)}\(([^)]*)\)',
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return None
    sig = m.group(1)
    params = set()
    for part in sig.split(","):
        part = part.strip()
        if not part:
            continue
        # Extract param name (before : or =)
        name = re.split(r'[:\s=]', part)[0].strip()
        if name and name != "self":
            params.add(name)
    return params


def _check_auth_contract(repo_root: Path) -> list[Finding]:
    """Validate auth_begin against shared behavior contract."""
    findings: list[Finding] = []

    contract_file = repo_root / "tests" / "fixtures" / "mcp_auth_contract.json"
    if not contract_file.exists():
        findings.append(Finding(
            severity="P1",
            message="Shared auth contract file missing: tests/fixtures/mcp_auth_contract.json",
            file="tests/fixtures/mcp_auth_contract.json",
        ))
        return findings

    contract = json.loads(contract_file.read_text(encoding="utf-8"))

    # Extract expected exposed/hidden params from contract
    for case in contract.get("cases", []):
        expected = case.get("expected", {})
        exposed = set(expected.get("exposed_params", []))
        hidden = set(expected.get("hidden_params", []))

        # Check Python MCP auth_begin
        py_server = repo_root / "mcp-server" / "towow_mcp" / "server.py"
        if py_server.exists():
            py_content = py_server.read_text(encoding="utf-8")
            py_params = _extract_tool_params(py_content, "towow_auth_begin")
            if py_params is not None:
                for h in hidden:
                    if h in py_params:
                        findings.append(Finding(
                            severity="P0",
                            message=f"Python MCP auth_begin exposes hidden param '{h}' (contract: {case['id']})",
                            file="mcp-server/towow_mcp/server.py",
                        ))
                for e in exposed:
                    if e not in py_params:
                        findings.append(Finding(
                            severity="P1",
                            message=f"Python MCP auth_begin missing exposed param '{e}' (contract: {case['id']})",
                            file="mcp-server/towow_mcp/server.py",
                        ))

        # Check Node MCP auth_begin schema
        node_index = repo_root / "mcp-server-node" / "src" / "index.ts"
        if node_index.exists():
            node_content = node_index.read_text(encoding="utf-8")
            # Look for schema params in the auth_begin tool registration
            auth_begin_match = re.search(
                r'"towow_auth_begin".*?inputSchema:\s*z\.object\(\{([^}]*)\}',
                node_content, re.DOTALL,
            )
            if auth_begin_match:
                schema_body = auth_begin_match.group(1)
                for h in hidden:
                    if h in schema_body:
                        findings.append(Finding(
                            severity="P0",
                            message=f"Node MCP auth_begin exposes hidden param '{h}' (contract: {case['id']})",
                            file="mcp-server-node/src/index.ts",
                        ))

    return findings


def _find_disabled_tools(content: str, tool_pattern: re.Pattern[str]) -> set[str]:
    """Find tools whose handler body contains a DISABLED status return."""
    matches = list(tool_pattern.finditer(content))
    disabled = set()
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        if '"DISABLED"' in content[start:end]:
            disabled.add(m.group(1))
    return disabled


def _check_disabled_parity(repo_root: Path) -> list[Finding]:
    """Detect tools that return DISABLED in one implementation but are live in the other."""
    findings: list[Finding] = []

    py_file = repo_root / "mcp-server" / "towow_mcp" / "server.py"
    node_file = repo_root / "mcp-server-node" / "src" / "index.ts"

    py_disabled: set[str] = set()
    if py_file.exists():
        py_disabled = _find_disabled_tools(py_file.read_text(encoding="utf-8"), _PY_TOOL_PATTERN)

    node_disabled: set[str] = set()
    if node_file.exists():
        node_disabled = _find_disabled_tools(node_file.read_text(encoding="utf-8"), _NODE_TOOL_PATTERN)

    for tool in sorted(node_disabled - py_disabled):
        findings.append(Finding(
            severity="P1",
            message=f"Tool '{tool}' returns DISABLED in Node but is live in Python",
            file="mcp-server/towow_mcp/server.py",
        ))
    for tool in sorted(py_disabled - node_disabled):
        findings.append(Finding(
            severity="P1",
            message=f"Tool '{tool}' returns DISABLED in Python but is live in Node",
            file="mcp-server-node/src/index.ts",
        ))

    return findings


def run(repo_root: Path, mode: str = "full") -> list[Finding]:
    findings: list[Finding] = []

    py_tools = _extract_python_tools(repo_root)
    node_tools = _extract_node_tools(repo_root)

    if not py_tools:
        findings.append(Finding(
            severity="P0",
            message="Cannot extract Python MCP tools — check regex pattern",
            file="mcp-server/towow_mcp/server.py",
        ))
        return findings

    if not node_tools:
        findings.append(Finding(
            severity="P0",
            message="Cannot extract Node MCP tools",
            file="mcp-server-node/src/index.ts",
        ))
        return findings

    # Check for missing tools
    py_only = py_tools - node_tools
    node_only = node_tools - py_tools

    for tool in sorted(py_only):
        findings.append(Finding(
            severity="P1",
            message=f"Tool '{tool}' in Python but not Node MCP",
            file="mcp-server-node/src/index.ts",
        ))

    for tool in sorted(node_only):
        findings.append(Finding(
            severity="P1",
            message=f"Tool '{tool}' in Node but not Python MCP",
            file="mcp-server/towow_mcp/server.py",
        ))

    # Auth behavior contract
    findings.extend(_check_auth_contract(repo_root))

    # Disabled tool behavior parity
    findings.extend(_check_disabled_parity(repo_root))

    return findings


if __name__ == "__main__":
    results = run(_REPO_ROOT)
    for f in results:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.severity}] {loc}: {f.message}")
    p0 = sum(1 for f in results if f.severity == "P0")
    print(f"\n--- {len(results)} findings ({p0} P0) ---")
    sys.exit(1 if p0 else 0)
