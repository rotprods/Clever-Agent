# CP01 Capability Report

- Candidate SHA: `6d0bcd2f2b5cbfd7a4b6620c0ce89de5a31a7a74`
- W03 total semantic surfaces: `76283`
- W03 behavior-mapped / denominator-eligible: `7565`
- W03 candidate-only definitions retained outside denominator: `68718`
- W04 capability denominator: `7565`
- Clever VERIFIED at CP01: `0`
- Denominator status: `GENERATED_UNVERIFIED`
- W07 graph nodes/edges: `84688` / `118927`

## Capability denominator by upstream

| Upstream | Capabilities |
|---|---:|
| clicky | 80 |
| omi | 3790 |
| openclaw | 3049 |
| openjarvis | 646 |

## Capability families

| Family | Count |
|---|---:|
| agent | 103 |
| api_protocol | 655 |
| capture_perception | 142 |
| channel_gateway | 710 |
| device_wearable | 126 |
| embodiment | 846 |
| inference | 437 |
| learning_evaluation | 31 |
| memory_persistence | 851 |
| plugin_extension | 1283 |
| scheduler_automation | 232 |
| security_policy | 279 |
| session_identity | 771 |
| speech_audio | 268 |
| tool | 736 |
| worker_service | 95 |

## Baseline status

Upstream commands were discovered and gated. CP01 does **not** execute untrusted upstream code without a hardened hermetic sandbox; `NOT_RUN` is never PASS.

- `clicky`: 1 candidates · {'PLATFORM_GATED': 1}
- `omi`: 121 candidates · {'CREDENTIAL_GATED': 3, 'HARDWARE_GATED': 14, 'NETWORK_GATED': 17, 'PLATFORM_GATED': 13, 'UNTRUSTED_EXECUTION_GATED': 74}
- `openclaw`: 376 candidates · {'CREDENTIAL_GATED': 9, 'HARDWARE_GATED': 8, 'NETWORK_GATED': 112, 'PLATFORM_GATED': 9, 'UNTRUSTED_EXECUTION_GATED': 238}
- `openjarvis`: 24 candidates · {'UNTRUSTED_EXECUTION_GATED': 24}

## Supply-chain status

- `clicky`: license `MIT` → `VERIFIED_DECLARATION_MATCH`; 2 lockfiles; 4 manifests
- `omi`: license `MIT` → `VERIFIED_DECLARATION_MATCH`; 24 lockfiles; 141 manifests
- `openclaw`: license `MIT` → `VERIFIED_DECLARATION_MATCH`; 8 lockfiles; 213 manifests
- `openjarvis`: license `Apache-2.0` → `VERIFIED_DECLARATION_MATCH`; 6 lockfiles; 32 manifests

## Release interpretation

CP01 proves a reproducible behavior-mapped capability denominator and retains candidate-only symbol evidence outside that denominator. It does **not** claim Clever-Agent adapter parity is complete. Candidate definitions remain available for future gauntlets; they are not silently discarded. No capability may be removed from the denominator because it is inconvenient to integrate.
