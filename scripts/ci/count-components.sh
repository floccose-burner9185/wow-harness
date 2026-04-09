#!/bin/bash
# count-components.sh — WP-03 AC 1 primary judge.
#
# Emits three lines that WP-SEC-1 CI asserts against MANIFEST.yaml:
#   command_instances=<N>   # count of "command": entries in .claude/settings.json
#   unique_scripts=<N>      # deduped scripts referenced by those commands
#   physical_files=<N>      # hook + root-script files on disk (L1 registry)
#
# Run from repo root. Reads .claude/settings.json, scripts/hooks/, scripts/.

set -e
cd "$(dirname "$0")/../.."

# command_instances: every "command" key in settings.json's hooks[]
# Count the total commands across all hook stages.
if command -v jq >/dev/null 2>&1; then
  CMD_INSTANCES=$(jq '[
    .hooks.PreToolUse[]?.hooks[]?,
    .hooks.PostToolUse[]?.hooks[]?,
    .hooks.PreCompact[]?.hooks[]?,
    .hooks.SessionStart[]?.hooks[]?,
    .hooks.SessionEnd[]?.hooks[]?,
    .hooks.Stop[]?.hooks[]?,
    .hooks.PostToolUseFailure[]?.hooks[]?
  ] | length' .claude/settings.json)
else
  # Fallback: line-grep. Less precise but works without jq.
  CMD_INSTANCES=$(grep -c '"command":' .claude/settings.json || echo 0)
fi

# unique_scripts: distinct scripts referenced by those commands.
# Extract the last `python3 scripts/...` or `bash scripts/...` token and dedupe.
UNIQUE_SCRIPTS=$(grep -oE '(python3|bash) scripts/[^ "]+' .claude/settings.json \
  | awk '{print $2}' | sort -u | wc -l | tr -d ' ')

# physical_files: hooks dir + 2 root scripts
HOOKS_COUNT=$(ls scripts/hooks/*.py scripts/hooks/*.sh scripts/hooks/*.md 2>/dev/null | wc -l | tr -d ' ')
ROOT_COUNT=$(ls scripts/guard-feedback.py scripts/deploy-guard.py 2>/dev/null | wc -l | tr -d ' ')
PHYSICAL=$((HOOKS_COUNT + ROOT_COUNT))

echo "command_instances=${CMD_INSTANCES}"
echo "unique_scripts=${UNIQUE_SCRIPTS}"
echo "physical_files=${PHYSICAL}"
