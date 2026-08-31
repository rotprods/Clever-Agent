# Claude Code entrypoint

Do not create a Claude-specific operating system for this repository.

1. Read `AGENTS.md` first.
2. Invoke `/empezarproyecto`; its canonical implementation is `commands/EMPEZARPROYECTO.md`.
3. Run state + context validators and `ContextPack --check`.
4. Load `.agentic/context/CURRENT_CONTEXT.json` and the exact COS-20D registry.
5. Every material mutation requires a claimed wave/support subwave.
6. Execute the shared `/cos-graph-engineV2` loop.
7. Treat Graphify V2 outputs as candidates and COS decisions as provisional until promotion evidence exists.
8. Persist run/wave/evidence/state/HANDOFF, regenerate ContextPack and validate before ending.
9. If this file conflicts with `AGENTS.md`, `AGENTS.md` wins.

Never assume the frontier from this shim; derive it from canonical state/context validation.
