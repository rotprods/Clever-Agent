# ACTA DE CONSCIENCIA — CLEVER-JARVIS-001

**Versión:** 1.0  
**Fecha:** 2026-08-31  
**Estado:** CP01 / Iteration 01 / forensic capability compiler

## North Star

Construir un único JARVIS operativo que pueda percibir, recordar, razonar, aprender, comunicarse y actuar a través de dispositivos/canales, conservando la unión verificable de capacidades de OpenJarvis, OpenClaw, Omi y Clicky; local-first, user-owned, auditable y permissioned.

No estamos construyendo cuatro repos dentro de una carpeta. Estamos construyendo **una identidad y un control plane comunes sobre cuatro runtimes maduros**, convergiendo únicamente aquello cuya equivalencia esté demostrada.

## De dónde venimos

Partíamos de una formulación intuitiva: “unificar el 100% de cuatro repositorios en Clever-Agent”.

La regresión reveló que esa frase escondía varios problemas:

1. “100%” no tenía denominador verificable.
2. Los repos usan lenguajes/runtimes distintos por razones legítimas.
3. Nombres similares no significan comportamiento equivalente.
4. Memoria, percepción, gateway, lifecycle y embodiment tienen temporalidades/trust boundaries distintos.
5. Un agente futuro no puede depender de recordar esta conversación.

Por eso la misión evolucionó hacia un sistema de evidencia, promoción y convergencia gobernada.

## Dónde estamos

### P0 — Evidence truth existe

Tenemos pins exactos y un pipeline reproducible de adquisición. El source graph de los cuatro upstreams ya ha ejecutado en CI con provenance no destructiva.

### P1 — Semantic truth todavía está en construcción

Graphify puede encontrar enormes cantidades de evidencia/candidatos, pero W03 debe transformar eso en **surfaces registradas o ejecutables**: routes, registries, commands, providers, plugins, channels, agents, schedulers, persistence owners, capture/device contracts, etc.

### P2 — Decision truth es provisional

COS Graph Engine V2 puede proponer `KEEP_NATIVE / ADAPT / CANONICALIZE / MERGE_STATE / REWRITE_LATER`, pero no puede autorizar su propia migración.

### P3 — Agent context existe pero debe ser fail-closed

Tenemos un ContextPack compacto, pero la regresión encontró IDs fantasma. La consciencia del proyecto no es útil si puede inventar continuidad. Su próximo estado debe ser **determinístico, ledger-backed y CI-enforced**.

## Qué hemos aprendido de cada upstream

### OpenJarvis

Es nuestra referencia más fuerte para **tipado cognitivo**: engine/model/agent/memory/tool/router/learning/benchmark/speech/TTS/connectors como primitivas explícitas. Debemos preservar esta claridad semántica.

### OpenClaw

Es nuestra referencia más fuerte para **contribution lifecycle**: plugins registran tools/channels/providers/gateway methods/services/commands/session extensions/schedulers/hooks y además existen semantics de rollback/cleanup. Debemos absorber esta disciplina operacional.

### Omi

Es nuestra referencia más fuerte para **ambient perception + episodic lifecycle**: audio continuo, STT, diarization, speaker identity, conversation finalization, memories, background reconciliation, mobile/wearable/device/backend surfaces. No debe reducirse a “otro STT”.

### Clicky

Es nuestra referencia más fuerte para **desktop embodiment inmediato**: PTT, screen capture, multi-monitor UI, streaming response, TTS y pointing. No debe reescribirse por similitud nominal con otras capas.

## Arquitectura mental canónica

La unificación correcta tiene cuatro planos:

`P0 Source/Evidence → P1 Semantic/Behavior → P2 COS20D Decision → P3 Agent Context`.

Y dos ejes diferentes:

- **COS-20L:** dónde vive/ejecuta la responsabilidad.
- **COS-20D:** qué debemos entender/probar antes de integrarla o cambiarla.

Nunca se invierte la dirección. Una decisión no modifica la evidencia que la originó.

## Qué significa “unificar” a partir de ahora

Unificar puede significar cinco cosas distintas:

- `KEEP_NATIVE`: la implementación especializada sigue siendo nativa.
- `ADAPT`: se expone bajo un contrato común.
- `CANONICALIZE`: se unifican semántica/interfaz, no necesariamente código.
- `MERGE_STATE`: se converge ownership/event/state tras prueba de migración.
- `REWRITE_LATER`: se considera reemplazo solo después de parity + benchmark + recovery proof.

Por defecto, **adaptar antes que reescribir**.

## Línea roja de seguridad arquitectónica

No se elimina, reemplaza o migra comportamiento upstream hasta alcanzar:

`MIGRATION_ELIGIBLE`.

Eso exige provenance + behavior mapping + contract mapping + test mapping + verification + migration/recovery proof según la superficie.

## Lo que no debemos volver a hacer

- Confundir README con implementación.
- Confundir símbolos con capabilities.
- Confundir overlap léxico con equivalencia.
- Confundir CI cancelado con fallo lógico.
- Pedir tamaños de blobs en un partial clone si no son necesarios.
- Crear un ContextPack que contenga decisiones no persistidas.
- Permitir que el chat sea la única memoria del proyecto.
- Diseñar CP02 final antes de cerrar el denominator de CP01.
- Fusionar estado porque dos repos usan la palabra “memory”.
- Reescribir Swift/Flutter/Zephyr/TypeScript/Python maduros por dogma de lenguaje.

## Hacia dónde vamos

### Horizonte 1 — terminar CP01

Construir el denominator real de capabilities y demostrar exhaustividad suficiente mediante code/tests/docs/registries/protocols + gauntlet.

### Horizonte 2 — CP02

Compilar contratos canónicos a partir del graph real: identity, events, capability contribution, policy/action, memory, goals, traces, lifecycle/health/rollback.

### Horizonte 3 — CP03–CP06

Integrar verticalmente los cuatro runtimes sin pérdida conductual.

### Horizonte 4 — CP07–CP10

Converger identity/events/memory/action plane; cross-device continuity; learning/promotions; proactive autonomy.

### Horizonte 5 — CP11–CP12

100% parity verificable, upstream drift compiler, hardening, recovery, offline/degradation, performance, release/SBOM.

## Acta operacional

A partir de esta versión, un agente que entra al repo debe ser capaz de responder sin chat previo:

1. cuál es el goal;
2. qué checkpoint/wave está activo;
3. qué pins upstream son fuente de evidencia;
4. qué está probado y qué es provisional;
5. qué claims y riesgos están abiertos;
6. cuál es la primera acción ejecutable;
7. qué evidencia cerrará esa acción;
8. qué no tiene autorización para reescribir/migrar.

Si no puede responder a esas ocho preguntas desde Git, estado, ledgers y ContextPack, el sistema de continuidad está roto y debe entrar en `RECONCILIATION`, no en implementación.

## Frase canónica

> No estamos juntando código. Estamos compilando evidencia en contratos, contratos en integración y únicamente integración verificada en convergencia.
