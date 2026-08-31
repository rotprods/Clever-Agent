# ACTA DE CONSCIENCIA — CLEVER-JARVIS-001

**Versión:** 1.1  
**Fecha:** 2026-08-31  
**Estado actual:** `CP01 / I01.3 / I01-W03`

## North Star

Construir un único JARVIS que pueda percibir, recordar, razonar, aprender, comunicarse y actuar a través de dispositivos y canales, conservando la unión verificable de capacidades de OpenJarvis, OpenClaw, Omi y Clicky; local-first, user-owned, auditable, permissioned y recuperable.

No estamos construyendo cuatro repositorios dentro de una carpeta. Estamos construyendo **una identidad, contratos y control plane comunes sobre runtimes especializados**, convergiendo únicamente aquello cuya equivalencia esté demostrada.

## De dónde venimos

La formulación inicial —“unificar el 100% de cuatro repos”— escondía cinco problemas:

1. no existía un denominador verificable para “100%”;
2. los runtimes/lenguajes son distintos por razones legítimas;
3. nombres similares no demuestran comportamiento equivalente;
4. perception, memory, gateway, lifecycle y embodiment tienen ownership temporal y trust boundaries diferentes;
5. un futuro agente no puede depender del chat que originó el proyecto.

Por eso la arquitectura evolucionó de un merge de código a un **compilador de evidencia → comportamiento → contratos → integración → convergencia**.

## Dónde estamos

### P0 — Source/Evidence: establecido

Tenemos cuatro pins exactos, adquisición reproducible, Graphify raw evidence y una fotografía estructural completa: 50.681 entradas de árbol, 390 manifests, 17.651 tests y 615 runtime boundaries.

### P1 — Semantic/Behavior: siguiente frontera

W03 debe promover evidencia a superficies realmente registradas o ejecutables: routes, commands, registries, provider/plugin contributions, agents, schedulers, state owners, device/capture contracts y tests asociados.

### P2 — COS20D Decision: disponible pero provisional

El engine puede proponer `KEEP_NATIVE / ADAPT / CANONICALIZE / MERGE_STATE / REWRITE_LATER`, pero ninguna decisión se autoautoriza para migración.

### P3 — Agent Context: durable y fail-closed

ContextPack, acta, regresión, implementation plan, task DAG, claims, risks y evidence IDs se validan entre sí. El chat es una superficie de interacción, no la memoria de continuidad.

## Qué aporta cada upstream

### OpenJarvis — cognitive type system

Su mayor valor arquitectónico es el tipado de primitivas: models, engines, agents, memory/fact stores, tools, router policies, benchmarks, channels, learning, skills, speech/TTS, connectors y mining.

### OpenClaw — contribution/lifecycle operating system

Su mayor valor es registrar contribuciones heterogéneas con lifecycle, ownership y rollback: tools, channels, providers, gateway methods, services, commands, session extensions/actions, schedulers, hooks, node commands, trusted-tool policy y security audit.

### Omi — ambient/episodic/device lifecycle

Su valor no es “STT”: integra escucha continua, diarization/speaker identity, conversation finalization, memories/action items, reconciliación durable, desktop/mobile/wearables/firmware y una gran superficie de API.

### Clicky — native desktop embodiment

Su valor es la interacción macOS de baja latencia: PTT, audio, screen/multi-monitor perception, response streaming, TTS, overlay y pointing. Debe permanecer nativa mientras un reemplazo no demuestre parity superior.

## Arquitectura mental canónica

`P0 Source/Evidence → P1 Semantic/Behavior → P2 COS20D Decision → P3 Agent Context`.

- **20L** responde dónde se ejecuta una responsabilidad.
- **20D** responde qué debemos entender/probar antes de cambiarla.

La dirección nunca se invierte: una decisión no reescribe la evidencia que la originó.

## Qué significa “unificar”

- `KEEP_NATIVE`: conservar implementación especializada.
- `ADAPT`: exponerla bajo contrato común.
- `CANONICALIZE`: unificar semántica/interfaz, no necesariamente código.
- `MERGE_STATE`: converger ownership/event/state solo tras prueba de migración.
- `REWRITE_LATER`: reemplazo posible únicamente tras parity + benchmark + recovery proof.

Default: **adapt before rewrite**.

## Línea roja

Ningún comportamiento upstream se elimina, reemplaza o migra hasta `MIGRATION_ELIGIBLE`.

La escalera de promoción es:

`OBSERVED_SOURCE → DISCOVERED_CANDIDATE → BEHAVIOR_MAPPED → CONTRACT_MAPPED → TEST_MAPPED → VERIFIED → MIGRATION_ELIGIBLE`.

## Errores que no repetimos

- README ≠ implementación.
- Símbolo ≠ capability.
- Overlap léxico ≠ equivalencia.
- CI cancelado ≠ fallo lógico.
- Pedir blob sizes en un partial clone sin necesitarlos.
- ContextPack con conocimiento no persistido.
- Chat como continuidad única.
- Kernel final antes del denominator CP01.
- Fusionar estado porque dos módulos se llaman “memory”.
- Reescribir Swift/Flutter/Zephyr/TypeScript/Python maduros por dogma de lenguaje.

## Hacia dónde vamos

1. **W03:** superficie conductual registrada/ejecutable con provenance y evidence strength.
2. **W04:** capability ledger + denominator real + equivalence gauntlet.
3. **W05/W06:** baselines y supply-chain/licenses.
4. **W07:** capability dependency graph + 20D completeness/orphan gauntlet.
5. **W08:** reporte CP01 y requisitos CP02 derivados de evidencia.
6. **CP02:** contratos canónicos; codegen/round-trip tests; solo después kernel Rust.
7. **CP03–CP06:** adapters verticales de los cuatro runtimes.
8. **CP07–CP10:** identity/events/memory/action convergence, cross-device continuity y learning/autonomy.
9. **CP11–CP12:** full parity, upstream drift, hardening y release.

## Ocho preguntas que cualquier agente debe responder antes de escribir

1. ¿Cuál es el goal?
2. ¿Qué checkpoint/wave está activo?
3. ¿Qué pins son la evidencia upstream?
4. ¿Qué está probado y qué sigue provisional?
5. ¿Qué claims/risks están activos?
6. ¿Cuál es la primera acción executable?
7. ¿Qué evidencia la cerrará?
8. ¿Qué no tiene autorización para reescribir/migrar?

Si no puede contestarlas desde Git/state/ledgers/ContextPack, entra en `RECONCILIATION`, no en implementación.

## Frase canónica

> No estamos juntando código. Estamos compilando evidencia en comportamiento, comportamiento en contratos, contratos en integración y únicamente integración verificada en convergencia.

## CP01 cerrado — 2026-09-01

El compilador W01–W08 pasó sobre `6d0bcd2f2b5cbfd7a4b6620c0ce89de5a31a7a74` y produjo un denominador behavior-mapped de `7565` capacidades. Esto **no** significa 100% de parity implementada en Clever-Agent: `VERIFIED=0` al entrar en CP02. La siguiente misión es convertir la presión real del corpus en contratos canónicos antes del kernel Rust.
