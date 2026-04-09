#!/usr/bin/env python3
"""Guard: detect protocol concept leakage in scene API outputs (ADR-037).

Scans hackathon routes and adapter for forbidden protocol terms
appearing as API output keys (string literals in quotes).

Exit 0 = clean, Exit 1 = leakage detected.
"""

import re
import sys
from pathlib import Path

FORBIDDEN_KEYS = {"demand_id"}

SCAN_FILES = [
    "backend/product/routes/hackathon.py",
    "backend/product/hackathon/adapter.py",
    "backend/product/hackathon/service.py",
]

# Pattern: "demand_id" or 'demand_id' as a dict key in API output
KEY_PATTERN = re.compile(r'''['"](%s)['"]''' % "|".join(FORBIDDEN_KEYS))

# Whitelist: DB column access contexts where demand_id is legitimate
WHITELIST_PATTERNS = [
    re.compile(r'\.\w+\.demand_id'),           # ORM attribute: e.demand_id
    re.compile(r'row\[.demand_id.\]'),          # Raw SQL row access
    re.compile(r'row\.get\(.demand_id.\)'),     # Dict .get()
    re.compile(r'demand_id\s*=\s*\w'),            # Keyword argument (not dict key assignment)
    re.compile(r'\.c\.demand_id'),              # SQLAlchemy column ref
    re.compile(r'from_scene_input'),            # Reverse mapping context
    re.compile(r'concept_map'),                 # Concept map definition
    re.compile(r'#.*demand_id'),                # Comments
    re.compile(r'result\[.demand_id.\]\s*=\s*result\.pop'),  # Reverse mapping in adapter
    re.compile(r'"demand_id":\s*"challenge_id"'),  # Concept map value pair
]

repo_root = Path(__file__).resolve().parent.parent.parent
violations = []

for rel_path in SCAN_FILES:
    filepath = repo_root / rel_path
    if not filepath.exists():
        continue
    for lineno, line in enumerate(filepath.read_text().splitlines(), 1):
        if KEY_PATTERN.search(line):
            if any(wp.search(line) for wp in WHITELIST_PATTERNS):
                continue
            violations.append(f"  {rel_path}:{lineno}: {line.strip()}")

if violations:
    print("ERROR: Protocol concept leakage detected in scene API output:")
    print("\n".join(violations))
    sys.exit(1)
else:
    print("OK: No protocol concept leakage in scene API outputs.")
    sys.exit(0)
