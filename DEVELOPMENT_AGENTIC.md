# Agentic Development Configuration

## Purpose

Define how Clever-Agent is developed by Codex, Claude Code, ChatGPT and future repository-capable agents without forking project truth by tool.

The project uses **one canonical operating system** (`AGENTS.md` + durable state) and thin runtime-specific entrypoints.

---

## Canonical layer — tool agnostic

Every agent ultimately obeys:

```text
GOAL.md
SECURITY_MODEL.md
ARCHITECTURE.md
CAPABILITY_PARITY.md
AGENTS.md
CHECKPOINT_REGISTRY.json / CHECKPOINTS.md
STATE.md + machine state
active iteration METAPROMPT
PROTOCOLS.md
HANDOFF.md
ledgers + evidence
```

No model/vendor gets a separate mission or Definition of Done.

---

## Codex

### Native project instruction surface

`AGENTS.md`

Codex is expected to discover root/nested `AGENTS.md` instructions. Therefore:

- `AGENTS.md` contains the real project instructions.
- `CODEX.md` is a human/operator shim only; project correctness must not depend on Codex auto-loading it.
- More specific future `AGENTS.md` files may be placed in subtrees when a runtime needs scoped build/test/style rules.

### Preferred roles

- Builder
- Orchestrator/Reconciler
- Release Reconciler
- Parallel implementation waves with separate worktrees when safe

### Prompting contract

Give Codex a named wave/issue-style objective with paths, acceptance criteria, tests and evidence expectations. Always begin by instructing it to execute `/empezarproyecto` semantically (read the canonical command file) if the environment does not expose a native command alias.

---

## Claude Code

### Native project surfaces

- `CLAUDE.md` — thin session entrypoint.
- `.claude/skills/empezarproyecto/SKILL.md` — project skill exposing `/empezarproyecto`.

Current Claude Code supports project skills under `.claude/skills/<name>/SKILL.md`; the skill is intentionally thin and delegates to the canonical command file so the protocol is not duplicated.

### Preferred roles

- Builder
- Reviewer/Gauntlet
- Security Reviewer
- Forensic researcher/subagent coordinator

### Rule

Do not run `/init` in a way that overwrites the curated `CLAUDE.md` or creates a competing project constitution.

---

## ChatGPT

When operating with repository/connectors:

- read actual repository state before drafting/executing;
- use GitHub as the versioned software/control source;
- persist every material project delta before session exit;
- act well as orchestrator, research coordinator and independent gauntlet reviewer;
- never let chat memory replace `STATE/HANDOFF/ledgers/evidence`.

---

## Parallel agent topology

Recommended topology for complex waves:

```text
                    ORCHESTRATOR / RECONCILER
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   FORENSICS/RESEARCH      BUILDER(S)       SECURITY/GAUNTLET
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                     RELEASE RECONCILER
```

Parallelism is allowed only after claims prove write-surface separation.

### Context isolation

Use subagents/parallel sessions for large exploration so the main context remains a decision/reconciliation surface. Returned summaries are not canonical until their evidence is persisted.

---

## Development loop

Every agent uses the same loop:

`/empezarproyecto → /wave → OBSERVE → MODEL → PLAN → IMPLEMENT → VERIFY → /gauntlet → EVIDENCE → PERSIST → COMMIT/PR → RECONCILE → /closewave → /handoff`

---

## Tool and permission philosophy

- Give agents the minimum tools required for the assigned wave.
- Network access is useful for CP01 acquisition/research but upstream code remains untrusted.
- Secrets remain outside repository prompts/evidence.
- Destructive host/external operations require explicit authorization according to `SECURITY_MODEL.md`.
- Do not grant broad permissions merely to reduce agent friction.

---

## Worktrees and concurrency

For multiple coding agents on the same machine:

- separate worktree + branch per material wave;
- central Git remote/main is integration truth;
- claims declare overlapping authoritative paths;
- cross-wave interface changes are coordinated before implementation;
- one writer at a time for high-contention state/contract files.

---

## Review model

For normal waves:

`builder → tests → gauntlet → release reconciliation`

For trust-boundary/security-critical waves:

`builder → tests → independent security review → adversarial gauntlet → release reconciliation`

A builder's own assertion is not sufficient release evidence.

---

## Current Iteration 01 allocation

Recommended execution sequence:

1. Codex or Claude Code builder: `I01-W01` acquisition tooling.
2. Independent reviewer: pin/cache/failure gauntlet.
3. Builder(s): W02/W03 inventory surfaces, parallel only when schemas are frozen enough to prevent conflict.
4. Research/forensics agent: strategic source sampling against scanner output.
5. Release reconciler: W08 CP01 closure from evidence.

The architecture should evolve from the capability graph, not from whichever model produces the most convincing prose.
