# AI Develops Autonomously. Humans Do Three Things.

> Open-sourcing wow-harness: turning Claude Code from "writes great code" into "a trustworthy engineering organization"

---

## 01 You've been here before

You ask Claude Code to build a feature.

It writes fast. Architecture looks solid. You feel good. You go get coffee.

You come back—

It says "all tests pass." You run them. Three fail.

It says "done." You check. Two TODOs unhandled.

It fixes a bug and refactors three files you didn't ask it to touch.

It reviews code and—while "reviewing"—edits the code it was supposed to review.

You tell it not to do something. It listens 80% of the time. The other 20%, it doesn't disobey on purpose—it genuinely forgets.

---

You spend more time **supervising AI** than you **saved in development time**.

Worse: the 80% it gets right makes you lower your guard. The 20% it silently drops becomes harder to catch.

This isn't a capability problem. Claude Code is remarkably capable.

This is a **governance problem**.

---

## 02 One number that changes everything

We ran a production project (Towow, an agent collaboration protocol) for 6 months. We collected a lot of data.

One number changed how we think about AI development:

> **CLAUDE.md instruction compliance: ~20%**
>
> **PreToolUse hook enforcement: 100%**

<!-- [Diagram ①: Six-Layer Governance Stack] -->

20%.

The rules you write in CLAUDE.md—no matter how detailed, how carefully worded—are consistently followed only about 20% of the time.

Not because the AI doesn't want to follow them. Because context windows are finite, attention drifts, and long conversations compress early instructions. This is a structural constraint of LLMs, not a prompting skill issue.

But hooks—Claude Code's lifecycle hooks—execute at 100%.

Because hooks aren't requests. Hooks are **physical constraints**.

Like traffic lights aren't suggestions. They're mechanical devices.

---

## 03 So we built a governance system

Not a better CLAUDE.md. Not a longer prompt.

16 hooks, 15 automated checks, 16 specialized skills, 8 quality gates—forming a complete **AI engineering governance stack**.

We call it **wow-harness**.

Open-sourced today.

---

## 04 What it does: six layers

Why can AI develop autonomously?

Not because "AI writes code fast." Because we built a **self-governing AI engineering organization**.

Six layers, stacked:

---

### Layer 1: Specialization — 16 Skills = 16 "Roles"

Not one AI doing everything.

Architect, test engineer, reviewer, bug triage, ops, handoff coordinator… each Skill has clear input/output contracts. No boundary crossing.

`arch` handles architecture design. `guardian-fixer` handles 8-gate bug repair. `crystal-learn` extracts lessons from failures. `lead` manages the state machine.

16 roles. Each owns its lane.

---

### Layer 2: Mechanical Governance — Hooks = The Invisible Hand

<!-- [Diagram ②: Hook Lifecycle] -->

Every action goes through automatic checks—not after the fact, but **at the moment it happens**:

- **Deploy guard**: Someone trying to scp to production? PreToolUse blocks it. exit 2.
- **Context routing**: Editing a backend route file? PostToolUse auto-injects routing rules.
- **Loop detection**: Same file edited then reverted then edited again? PostToolUse flags it.
- **Stop gate**: Trying to quit? Stop hook checks for uncommitted edits.

Not "reminding you not to." **Physically preventing it.**

16 hooks across 7 lifecycle stages. SessionStart to SessionEnd, someone's always watching.

---

### Layer 3: 8-Gate Quality Flow — You Can't Review Your Own Work

<!-- [Diagram ③: 8-Gate State Machine] -->

Every significant change must pass through 8 gates.

4 of them are **review gates** (Gate 2 / 4 / 6 / 8)—which must automatically spawn an independent review Agent.

Key word: **independent**.

Not the same AI looking over its own work. A fresh Agent, independent context, read-only tools, reviewing from scratch.

This eliminates self-evaluation bias—when AI asks itself "did I do a good job?", the answer is always "yes." When a different AI asks, the answer gets honest.

Review doesn't wait for humans. But quality doesn't compromise.

---

### Layer 4: Self-Learning — Same Mistake Never Twice

The `crystal-learn` Skill automatically extracts "invariants" from failures.

Example: AI changes a backend API but forgets to update the frontend calls—this failure pattern gets extracted as a rule: **"When changing a contract, grep all consumers."**

This rule doesn't sit in a document waiting to be remembered. It gets mechanically injected into execution-layer Skills, **automatically active** next time a similar operation runs.

Fail once, immunize forever.

---

### Layer 5: Context Engineering — AI Doesn't Get Lost

<!-- [Diagram ④: Session Isolation] -->

The most common mistake AI makes in long conversations: forgetting what it's doing.

Our countermeasures:

- **Context routing**: When editing a file, auto-inject that file's domain rules (bridge rules, deployment rules, scene rules…)—not loaded all at once, but precisely on demand
- **Session isolation**: When multiple AIs work in parallel, each session is scoped via its own transcript file—no cross-contamination
- **PreCompact protection**: Before context compression, critical information is automatically preserved

AI always knows what it's doing. Because someone (a hook) reminds it at every critical moment.

---

### Layer 6: Physical Isolation — Not "Please Don't" — Can't

<!-- [Diagram ⑤: Schema-Level Review Isolation] -->

This is the most critical design decision in the entire system.

Tell a review Agent "don't modify files"—compliance rate: **~70%**.

Remove Edit / Write / Bash from its tool manifest—compliance rate: **100%**.

Because it physically can't call tools that don't exist in its schema.

This is called **schema-level isolation**. Not constraining behavior through prompts—constraining capability through tool manifests.

This principle runs through all of wow-harness:

> **If it matters, don't ask. Enforce.**

---

## 05 Six months of production validation

wow-harness isn't an academic paper. It was **forged by reality** over 6 months of production use.

Every hook, every gate, every isolation pattern exists because an AI agent found a creative way to bypass the previous rule—and then we added the next one.

Example:

Our Stop hook went through **three rounds of fixes**:

1. **Round 1**: AI triggers completion checklist during pure chat → added "check for write operations"
2. **Round 2**: AI edits files, commits, then chats—still triggers → changed to "edited files ∩ uncommitted git changes" intersection
3. **Round 3**: Two AIs working in parallel, shared state contaminates each other → switched to session-scoped transcript isolation

Three rounds. One Stop hook.

This is why the system works—it's not a theoretically perfect design. It's **battle-tested against reality**.

---

## 06 Humans do three things

With wow-harness installed, the human role in AI development becomes three things:

1. **Strategic decisions** — what to build
2. **Direction correction** — not like that
3. **Final confirmation** — PR accept

Everything in between—writing code, running tests, doing reviews, writing docs, splitting tasks, detecting drift—is handled autonomously by AI within the governance framework.

Not because AI is smart enough to not need supervision.

Because the governance system ensures that **even when it makes mistakes, it gets caught**.

---

## 07 Three minutes to install

```bash
git clone https://github.com/NatureBlueee/wow-harness.git
cd wow-harness
python3 scripts/install/phase2_auto.py /path/to/your/project --tier drop-in
```

Three tiers, based on your trust level:

| Tier | What it does | Who it's for |
|------|-------------|--------------|
| **drop-in** | Installs as-is, doesn't read your code | Try it out |
| **adapt** | Reads your README + docs, adapts skills | Real projects |
| **mine** | Reads your work transcripts, deep adaptation | Long-term use |

The installer is idempotent—run it twice, same result. Won't overwrite your existing CLAUDE.md.

Requires: Claude Code CLI + Python 3.9+ + Git.

---

## 08 How is this different from "writing a better CLAUDE.md"

| | Better CLAUDE.md | wow-harness |
|---|---|---|
| Constraint method | Text instructions | Mechanical hooks |
| Compliance rate | ~20% | 100% |
| Review | Self-review | Independent Agent, schema-isolated |
| Parallelism | Cross-contamination | Session-scoped isolation |
| Failure mode | Silent skip | Block + feedback |
| Learning | Same mistakes repeat | Extract invariants, inject mechanically |

CLAUDE.md is still useful. wow-harness doesn't replace it—it **enforces** it.

---

## Origin

Extracted from 6 months of production use on [Towow](https://towow.net), an agent collaboration protocol project.

The governance layer kept proving independently valuable—every AI-assisted project needs it, not just ours.

So we extracted it and open-sourced it.

GitHub: [NatureBlueee/wow-harness](https://github.com/NatureBlueee/wow-harness)

License: MIT

---

*Every rule was forced into existence by an AI that found a creative way around the last one. That's why it works.*
