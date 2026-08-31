# Security Model

## Security objective

Clever-Agent is a high-privilege personal system with microphone, screen, device, messaging, browser and execution access. Security is therefore an architectural plane, not a prompt instruction.

## Trust zones

1. **T0 — kernel/policy core**: identity, policy, permissions, audit, signing material handles.
2. **T1 — trusted local adapters**: reviewed OpenJarvis/OpenClaw/Omi/Clicky bridges.
3. **T2 — sandboxed tools/skills**: code execution, browser tasks, third-party plugins.
4. **T3 — user-authorized remote services**: model/STT/TTS/search providers.
5. **T4 — untrusted input**: messages, websites, documents, screenshots, retrieved text, webhook payloads, unknown devices.

T4 content can influence reasoning but cannot mutate policy or grant privileges.

## Action risk classes

| Class | Examples | Default authorization |
|---|---|---|
| R0 | read local non-sensitive state, reason, search allowed memory | automatic |
| R1 | reversible UI navigation, draft content, non-destructive local action | policy-controlled automatic |
| R2 | send message, create calendar/task, modify normal files, external API mutation | explicit scoped grant or pre-approved automation |
| R3 | delete/overwrite, purchase, publish, credential/account change, broad shell action | just-in-time confirmation + narrow capability token |
| R4 | security controls, secret export, irreversible/high-impact financial or identity actions | deny by default; dedicated hardened flow required |

The model never decides its own authorization class.

## Ambient perception rules

- Microphone, screen, camera and location require OS permission and Clever policy permission.
- Always-on capture must have a visible kill switch and per-device state.
- Raw capture uses short retention by default.
- Derived memories preserve provenance without implying raw data must be retained forever.
- Capture from third parties/shared environments must support exclusion/redaction policy.

## Secret handling

- Secrets live in OS keychain/secret manager/provider auth stores, not Markdown/config committed to Git.
- Models receive opaque credential handles whenever possible.
- Provider tokens are scoped and short-lived where supported.
- Logs, traces and evidence redact secrets and sensitive provider payloads.
- Clicky-style server-side proxying is preserved where it reduces client secret exposure, but the proxy itself is policy/audit scoped.

## Device identity and pairing

- Remote clients/nodes require cryptographic device identity and explicit pairing.
- Pairing produces revocable device grants.
- Device capability declarations are validated against policy; a node cannot self-assert privileged commands into existence.
- Local loopback optimizations must not become remote trust bypasses.

## Tool / plugin security

- Third-party skills and plugins are untrusted until reviewed.
- Execution defaults to sandbox/container or constrained runtime.
- Mount/network/secret scopes are declared explicitly.
- Tool results are untrusted input when returned to the model.
- Side-effecting calls require idempotency and action policy checks.

## Prompt-injection boundary

Content may request actions but cannot:

- alter system policy,
- expose secrets,
- disable audit,
- expand tool scopes,
- pair a device,
- mark evidence as valid,
- bypass confirmation requirements.

## Memory security

Every memory record carries:

- owner/scope
- provenance
- classification
- retention policy
- creation/derivation time
- source IDs

Retrieval enforces scope before ranking. Sensitive memory is not merely hidden by prompt wording.

## Supply-chain security

- Pin upstream commits.
- Record licenses and required notices.
- Verify dependency lockfiles/checksums where available.
- Run upstream tests before and after integration.
- Generate SBOM for releases.
- Scan new plugin/skill packages and isolate install hooks.
- Upstream sync never auto-merges privileged changes solely because tests are green.

## Audit requirements

Persist at minimum:

- policy decisions
- device pairing/revocation
- privileged tool calls
- external sends/mutations
- secret-handle use metadata (not secret value)
- security scan/block events
- learning/prompt/skill promotions
- upstream updates

Audit records are append-only and correlation-ID linked to traces/actions.

## Required adversarial tests

- prompt injection from webpage/document/channel
- malicious plugin/tool output
- unauthorized node connect
- replayed side-effect request
- secret exfiltration attempt
- path traversal / unsafe mount
- SSRF/network-scope violation
- raw microphone/screen capture after permission revocation
- privilege escalation through learned prompt/skill update
- cross-user/group memory leakage
- provider failure that would otherwise drop data silently
