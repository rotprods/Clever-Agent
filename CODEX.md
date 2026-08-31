# Codex entrypoint

`AGENTS.md` is canonical. Do not create a Codex-specific operating system.

Boot:

1. Read `AGENTS.md`.
2. Execute `/empezarproyecto` via `commands/EMPEZARPROYECTO.md`.
3. Run:
   - `python scripts/validate_agentic_state.py`
   - `python scripts/context/validate_context_pack.py`
   - `python scripts/context/build_context_pack.py --check`
4. Load `.agentic/context/CURRENT_CONTEXT.json` and `.agentic/context/COS20D.json`.
5. Reconcile the active wave/claims before writing.
6. Execute `/cos-graph-engineV2`.
7. Regenerate ContextPack, update HANDOFF/ledgers, verify, commit and reconcile before exit.

Hard rules: raw Graphify evidence is not parity; Graphify V2 surfaces are candidates; COS decisions are provisional; destructive convergence requires `MIGRATION_ELIGIBLE`.

If this file conflicts with `AGENTS.md`, `AGENTS.md` wins.
