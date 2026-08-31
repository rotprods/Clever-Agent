# `/context` — deterministic future-agent context layer

## Build

```bash
python scripts/context/build_context_pack.py
```

## Validate

```bash
python scripts/context/validate_context_pack.py
python scripts/context/build_context_pack.py --check
```

Products:

```text
.agentic/context/COS20D.json
.agentic/context/CURRENT_CONTEXT.json
.agentic/context/CURRENT_CONTEXT.md
```

`CURRENT_CONTEXT` is a compact derived recovery projection. It stores frontier, exact pins, graph planes, invariants and IDs/pointers for active claims, risks, decisions and evidence. It does not duplicate full ledgers and never outranks canonical Git/state/evidence.

Regenerate after any material frontier/config/claim/risk/decision/evidence mutation.
