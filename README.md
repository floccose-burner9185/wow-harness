# wow-harness

A local AI development harness for Claude Code. Turns your repo into a fail-closed development environment where AI agents follow gates, get reviewed, and can't silently skip steps.

Born from 6 months of production use on the [Towow](https://towow.net) project. Everything project-specific has been extracted into structural slots you fill with your own context.

## What it does

**Problem**: Claude Code agents are brilliant but unreliable at process. They skip review gates, claim tests pass when they didn't run them, and drift from plans mid-execution.

**Solution**: A 5-layer governance stack that runs locally, enforced by hooks and skills:

| Layer | What | Examples |
|-------|------|---------|
| L0 | Infrastructure | MANIFEST, sanitize, templates |
| L1 | Hooks | 16 PreToolUse/PostToolUse/Session hooks |
| L2 | Checks | 15 automated validators (API types, doc freshness, security...) |
| L3 | Rules | Path-scoped context injection (backend routes, closure semantics...) |
| L4 | Skills | 16 specialized agent behaviors (architecture, plan-locking, bug triage...) |
| L5 | Decisions | ADR/PLAN/REVIEW document templates |

### The 8-Gate State Machine

Every change flows through 9 gates (0-8). Gates 2/4/6/8 are review gates that **must** use independent-context reviewers (TeamCreate, not Agent). The lead skill enforces this mechanically -- no "this one's simple, let's skip review."

```
Gate 0 (Problem) -> Gate 1 (Design) -> Gate 2* (Review)
  -> Gate 3 (Plan) -> Gate 4* (Review+Lock)
  -> Gate 5 (Task Split) -> Gate 6* (Review)
  -> Gate 7 (Execute+Log) -> Gate 8* (Final Review)

* = TeamCreate mandatory
```

### 16 Skills

| Category | Skills |
|----------|--------|
| Governance | `lead` (state machine), `arch` (architecture), `plan-lock`, `task-arch` |
| Engineering | `harness-dev`, `harness-eng`, `harness-eng-test`, `harness-ops` |
| Domain | `harness-voice` (project expression), `harness-lab` (experiments) |
| Safety | `guardian-fixer` (8-gate bug repair), `crystal-learn` (failure pattern extraction) |
| Automation | `bug-pipeline` (bug->PR), `bug-triage` (structured triage) |
| Meta | `skill-discovery` (finds new skills from your work patterns), `harness-dev-handoff` (AI handoff) |

Skills with `{{PLACEHOLDER}}` structural slots are designed to be filled with your project's worldview, primitives, and constraints during installation.

## Install

### Quick start (drop-in)

```bash
git clone https://github.com/NatureBlueee/wow-harness.git
cd wow-harness
python3 scripts/install/phase2_auto.py /path/to/your/project --tier drop-in
```

### Three tiers

| Tier | What it reads | Best for |
|------|--------------|----------|
| `drop-in` | Nothing beyond the bundle | Try it out, minimal trust |
| `adapt` | Your README + docs (first 50KB) | Customize skills to your project |
| `mine` | Named project transcripts | Deep customization from your work history |

### What gets installed

- `.claude/skills/` -- 16 skill definitions
- `.claude/rules/` -- path-scoped context rules
- `scripts/hooks/` -- Claude Code hook scripts
- `scripts/checks/` -- automated validators
- `.claude/settings.json` -- hook registrations (atomic append, won't clobber)

## Key design decisions

1. **Fail-closed, not fail-open**: Unknown states block progress. An unhelpful gate is safer than a skipped gate.
2. **Schema-level isolation for reviewers**: Review agents physically cannot call Edit/Write/Bash (frontmatter tool whitelist), not just "please don't."
3. **Hooks over instructions**: `CLAUDE.md` compliance is ~20%. PreToolUse hooks are 100%. We enforce at the hook layer.
4. **Soul-writing methodology**: Skills aren't rule lists. They install tension triangles, judgment personas, and bidirectional calibration -- so the agent can navigate situations the skill didn't explicitly cover.
5. **Structural slots over deletion**: Project-specific content becomes `{{PLACEHOLDER}}` with meta-instructions (what to put, why it matters, how to discover it), not blank space.

## Project structure

```
wow-harness/
  .claude/
    skills/          # 16 skill definitions (SKILL.md each)
    rules/           # 6 path-scoped context rules
    settings.json    # Hook registrations
  scripts/
    hooks/           # 16 Claude Code hooks
    checks/          # 15 automated validators
    install/         # 3-tier installer
  schemas/           # MANIFEST + validation
  reference/         # Towow governance snapshot (provenance)
  docs/              # Decision templates
```

## Requirements

- Claude Code CLI (logged in)
- Python 3.9+
- Git

## License

MIT

## Origin

Extracted from the [Towow](https://towow.net) agent collaboration protocol project. The harness layer proved independently valuable -- every AI-assisted project needs governance, not just ours.
