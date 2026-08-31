# Codex entrypoint

`AGENTS.md` is the canonical execution contract.

Boot sequence:

1. Read `AGENTS.md`.
2. Execute `/empezarproyecto` via `commands/EMPEZARPROYECTO.md`.
3. Run `python scripts/validate_agentic_state.py`.
4. Resolve the active iteration from `.agentic/CONFIG.yaml` and state files.
5. Claim one coherent wave before editing material surfaces.
6. Implement → verify → gauntlet → evidence → persist → commit → reconcile.
7. Update `HANDOFF.md` and ledgers before exit.

Do not use this file as an alternative source of project truth. If it conflicts with `AGENTS.md`, `AGENTS.md` wins.
