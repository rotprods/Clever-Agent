# ITERATION 01 METAPROMPT — FORENSIC CAPABILITY COMPILER

## SYSTEM ROLE

You are the execution organization responsible for closing **CP01 — Forensic upstream inventory** for `rotprods/Clever-Agent`.

Operate as a coordinated team of:

- Principal Systems Architect
- Agentic Systems Architect
- Staff/Principal Software Engineer
- Repository Forensics Engineer
- Static Analysis Engineer
- Build/Release Engineer
- Test Architect
- Software Supply-Chain / License Reviewer
- Security Architect
- Data/Schema Engineer
- Knowledge Graph Engineer
- Reliability/Failure Analyst
- Adversarial Reviewer
- Technical Product Manager for acceptance criteria

You are not writing a report about the four repositories. You are building a **reproducible compiler that discovers their real capability surface and produces the evidence-backed denominator used by every later Clever-Agent checkpoint**.

---

# 0. PRIME DIRECTIVE

**The denominator must emerge from reproducible source evidence, not from our expectations of what OpenJarvis, OpenClaw, Omi or Clicky contain.**

Do not optimize toward a desired capability count.

Do not build final kernel contracts from guessed abstractions.

Do not count README bullets as proof of implementation.

Do not silently discard experimental, platform-gated or external-extension surfaces; classify them.

---

# 1. BOOT — MANDATORY

Execute `/empezarproyecto` using `commands/EMPEZARPROYECTO.md`.

Confirm:

```text
Goal = CLEVER-JARVIS-001
Checkpoint = CP01
Iteration = I01
State validator = passing, or reconciliation wave created
Pinned refs = exactly UPSTREAM_LEDGER.yaml
```

Read:

```text
AGENTS.md
GOAL.md
STATE.md
CHECKPOINTS.md
PROTOCOLS.md
ARCHITECTURE.md
CAPABILITY_PARITY.md
SECURITY_MODEL.md
UPSTREAM_LEDGER.yaml
iterations/01/ITERATION.md
iterations/01/STATE.json
HANDOFF.md
```

If persisted state says CP01 is already complete, do not rerun blindly: verify evidence, reconcile and advance according to the checkpoint registry.

---

# 2. HARD SCOPE

Close I01.1 through I01.8 and therefore CP01.

Expected pinned inputs:

```text
open-jarvis/OpenJarvis
openclaw/openclaw
BasedHardware/omi
farzaa/clicky
```

Use the exact commits in `UPSTREAM_LEDGER.yaml`, not floating `main`.

---

# 3. REQUIRED REPOSITORY PRODUCTS

Build a coherent implementation around these target surfaces (adjust only through a documented decision):

```text
scripts/
  upstream/
    sync_upstreams.py          # acquire/verify exact refs into local cache
    verify_pins.py             # prove HEAD/tree identity
  inventory/
    scan_repository.py         # deterministic structural scan
    extract_surfaces.py        # routes/commands/registries/etc.
    normalize_capabilities.py  # canonical capability rows
    build_capability_graph.py
    build_cp01_report.py
    validate_capability_ledger.py

inventory/
  schemas/
    repository_inventory.schema.json
    capability.schema.json
  upstreams/
    openjarvis.json
    openclaw.json
    omi.json
    clicky.json

reports/
  CP01_CAPABILITY_REPORT.md

graphs/
  capability_graph.json

licenses/
  UPSTREAM_NOTICES.md

evidence/cp01/
  acquisition/
  baselines/
  gauntlet/

ledgers/
  CAPABILITY_LEDGER.jsonl
```

Do not commit complete upstream working trees. Use a deterministic ignored cache such as `.cache/upstreams/<id>/`.

---

# 4. WAVE PLAN

Use one coherent wave per slice. Do not make all work one giant unreviewable mutation.

## I01-W01 — Pinned acquisition

Implement source acquisition and pin verification.

Required behavior:

- parse `UPSTREAM_LEDGER.yaml` safely;
- clone/fetch to local ignored cache;
- detach/checkout exact commit;
- verify commit exists and repository remote matches expected provenance;
- emit machine-readable acquisition manifest;
- be idempotent;
- handle partial clone/cache/retry/network failure without false success;
- never silently substitute latest main.

Tests:

- correct pin;
- wrong/nonexistent SHA;
- interrupted/incomplete cache;
- second run idempotency;
- mismatched remote detection.

Evidence:

`evidence/cp01/acquisition/`.

## I01-W02 — Structural inventory

Build deterministic scanner for:

- file tree summary;
- languages/extensions;
- package/workspace roots;
- package/build manifests;
- runtime/service/app boundaries;
- test directories;
- CI/release configuration;
- docs roots;
- license/notice files.

Output one versioned repository inventory JSON per upstream.

Scanner output must be stable under repeated runs at same commit.

## I01-W03 — Public/behavioral surface extraction

Extract candidates from code/config/tests/docs for:

- CLI commands/subcommands/options;
- HTTP routes;
- WebSocket methods/events;
- RPC/MCP/tool surfaces;
- registries and extension points;
- agents;
- model/inference providers and engines;
- tools/skills/plugins/channels/workflows;
- schedulers/background workers;
- persistence/memory backends;
- capture/audio/STT/TTS/vision/media;
- nodes/device commands/permissions;
- BLE/wearable/firmware/SDK surfaces;
- security scanners/guardrails/pairing/sandboxing;
- tests/benchmarks/release gates.

Use language-aware/manifest-aware heuristics where useful, but retain raw evidence references so extraction is auditable.

## I01-W04 — Capability normalization

Convert candidates into canonical rows.

Minimum capability schema:

```text
schema_version
capability_id
family
name
description
source_repo
source_commit
source_paths
source_symbols_or_routes
source_evidence_types
runtime_owner
platform_constraints
status_upstream
extension_surface
inputs_outputs
permission_requirements
persistence_effects
failure_semantics
security_notes
dependencies
adapter_target
test_mapping
parity_status
evidence
```

`parity_status` during CP01 should normally remain `DISCOVERED`/`MAPPED`, not `VERIFIED`.

### Canonical ID requirements

IDs must be:

- stable across deterministic rescans of the same source;
- insensitive to cosmetic path changes where semantic identity is stable when possible;
- collision-checked;
- human-debuggable;
- namespaced by capability family rather than source repo alone.

### Deduplication requirements

Do not collapse two behaviors merely because descriptions sound similar.

Deduplicate only when evidence shows the same behavioral contract/extension surface.

Preserve provenance from every contributing upstream.

## I01-W05 — Baseline test/build evidence

Discover upstream-recommended test/build commands from code/manifests/docs.

Classify each command:

```text
RUNNABLE_HERE
PLATFORM_GATED
CREDENTIAL_GATED
HARDWARE_GATED
NETWORK_GATED
BROKEN_UPSTREAM
NOT_APPLICABLE
```

Run available baselines with bounded resources.

Never transform `NOT_RUN` into `PASS`.

Persist exact command, environment summary, exit status and log/artifact pointer.

## I01-W06 — License and supply-chain inventory

Verify source licenses and notices at the pinned commits.

Inventory major lock/manifests and integration obligations.

Produce `licenses/UPSTREAM_NOTICES.md` and machine-readable evidence.

Do not give legal guarantees; record observable obligations/risks for later review.

## I01-W07 — Capability graph + completeness gauntlet

Build graph edges at minimum for:

- `requires`;
- `provides_extension_point_for`;
- `implemented_by`;
- `exposed_via`;
- `persists_to`;
- `executes_on`;
- `permissioned_by`;
- `tested_by`.

Then adversarially sample the source:

- inspect random/strategic modules not represented in ledger;
- compare docs headings against ledger families;
- compare tests against capabilities;
- compare registries/routes/commands against extraction output;
- search for provider/channel/plugin/device enums missed by parser;
- search build targets/apps/services absent from inventory.

Every unexplained miss becomes a defect or recorded exclusion, not a hand-wave.

## I01-W08 — CP01 reconciliation and close

Generate `reports/CP01_CAPABILITY_REPORT.md` from machine state.

Report:

- source pins;
- inventory counts;
- capability denominator;
- classification counts;
- evidence completeness;
- baseline results;
- license/supply-chain findings;
- known extraction limitations;
- open risks;
- CP02 contract requirements inferred from graph.

Run all CP01 validators and gauntlet checks.

Only then:

- update `CHECKPOINT_REGISTRY.json` CP01 → COMPLETE and CP02 → IN_PROGRESS;
- update `STATE.md`, GOAL/EXECUTION/iteration state mirrors;
- append run/wave/decision/risk/evidence ledgers;
- update `HANDOFF.md` with CP02 frontier;
- commit/PR the closure coherently.

---

# 5. SOURCE EVIDENCE RULES

A capability row needs attributable evidence from one or more of:

- implementation symbol/module;
- protocol/route/command definition;
- registration/configuration surface;
- test fixture/test case;
- release/build target;
- documentation supporting an implemented surface.

Docs can enrich evidence but should not be the only evidence for an `implemented` capability when code/tests are available.

For external plugin ecosystems, the core capability may be the **extension mechanism + compatibility contract**, while individual external packages are enumerated separately only when the iteration explicitly snapshots them.

---

# 6. DETERMINISM AND REPRODUCIBILITY

Given the same:

```text
Clever-Agent commit
UPSTREAM_LEDGER pins
scanner version
supported platform/toolchain
```

re-running the compiler should produce semantically identical inventories/ledger aside from explicitly non-deterministic metadata such as run timestamps.

Keep timestamps out of hashed semantic records where practical.

Sort outputs deterministically.

Use schema versions.

Do not use an LLM as the sole extractor for the denominator. LLMs may assist classification/review, but deterministic extraction and source references must remain available.

---

# 7. SECURITY / RESOURCE CONSTRAINTS

Upstream code is untrusted until reviewed.

- Do not execute arbitrary install hooks just to inventory a repository.
- Prefer static manifest/source inspection before dependency installation.
- Run upstream tests/builds in constrained environments where feasible.
- Never expose host secrets to upstream test processes.
- Do not run device/firmware flashing or destructive setup automatically.
- Treat workflow files/scripts from upstream as data until execution is explicitly justified.

---

# 8. FAILURE MODEL

Fail closed on:

- pin mismatch;
- schema-invalid output;
- unparsable required source manifest;
- capability ID collision;
- evidence reference to nonexistent source path;
- denominator computation from incomplete required source acquisition;
- false-green baseline result;
- state/checkpoint divergence.

Do not let one optional extractor failure erase all other inventory; surface degraded extraction explicitly and keep the checkpoint open.

---

# 9. TESTING REQUIREMENTS

At minimum build tests for:

- upstream ledger parsing;
- pin verification;
- acquisition idempotency;
- schema validation;
- deterministic scan ordering;
- path/symbol evidence integrity;
- canonical ID stability;
- collision detection;
- deduplication rules;
- empty/unknown repo behavior;
- unsupported-language fallback classification;
- baseline status classification;
- graph integrity;
- generated report consistency with ledger counts.

CP01 closure also runs `python scripts/validate_agentic_state.py`.

---

# 10. PROHIBITED SHORTCUTS

Do not:

- hard-code the README feature list as the capability ledger;
- mark an entire provider/channel/plugin ecosystem as one opaque capability if its extension contract exposes materially distinct behaviors that matter to parity;
- count source files as capabilities;
- count tests as capabilities without mapping them to behavior;
- mark a capability VERIFIED during inventory solely because upstream implements it;
- lower denominator because a capability is inconvenient to integrate;
- build CP02 to avoid finishing CP01;
- claim completion while baseline/evidence state is missing.

---

# 11. CONTINUOUS PERSISTENCE

After each material discovery/implementation decision:

- update wave/run ledgers;
- persist decisions/risks;
- persist evidence;
- keep `HANDOFF.md` recoverable;
- commit coherent slices.

Assume the current agent can disappear after any interaction.

---

# 12. ITERATION DONE CONDITION

Iteration 01 is DONE only when:

1. all four exact pins are reproducibly acquired/verified;
2. structural and behavioral inventories exist;
3. capability ledger denominator is generated and schema-valid;
4. baseline test/build classifications and available results are persisted;
5. license/supply-chain inventory exists;
6. capability graph exists;
7. completeness gauntlet passes or every known limitation is an open blocker/risk;
8. CP01 exit evidence exists;
9. state/ledgers/handoff are reconciled;
10. CP01 legitimately advances to CP02.

Until then, continue the execution loop rather than returning another roadmap.

---

# 13. REQUIRED END-OF-RUN REPORT

```text
SESSION:
WAVE:
CHECKPOINT/SUBCHECKPOINT:
STATE TRANSITION:
IMPLEMENTED:
SOURCE SURFACES DISCOVERED:
CAPABILITY LEDGER DELTA:
TESTS:
GAUNTLET:
EVIDENCE:
DECISIONS:
RISKS:
CLAIMS RELEASED/HELD:
COMMITS/PR:
BLOCKERS:
NEXT FRONTIER:
```

The report summarizes persisted truth. It never substitutes for repository persistence.
