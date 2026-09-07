# CP03-W02 — Plan de implementación, gates y Definition of Done

Estado: PLANNED_NOT_IMPLEMENTED. Goal CLEVER-JARVIS-001 / I03 / tarea padre CP03-002. Base examinada: d3499fac7e098273d39244570b3f66fe8d529f56. Preparado: 2026-09-07; la evidencia histórica W01 examinada es del 2026-09-02. OpenJarvis permanece fijado en 72033b8ec288aa067ce4530ff9d96bf231e9c4e5.

## Decisión

Construir la primera inferencia real a través de Rust → contrato canónico → sidecar Python → engine nativo OpenJarvis → modelo real → resultado correlacionado. Antes del streaming, endurecer transporte, lifecycle y harness. No volver a inventariar todo, no reescribir upstream, no construir UI ni ejecutar tools en W02.

Separar dos hitos: M1 = primera inferencia real demostrada; M2 = cierre completo W02 con streaming, cancelación, recovery, seguridad, paridad y release. M1 NO autoriza W03.

## Estado base

W00/W01 completos; CP03-002 READY; 7.565 obligaciones globales, 646 OpenJarvis, cero VERIFIED. Las 230 entradas del registry W01 entran UNAVAILABLE: no equivalen a obligaciones ni a capacidad operativa. K, el número de obligaciones W02, debe compilarse desde las 646 existentes. No inventarlo, reducirlo ni identificarlo con las 230 registrations.

## Revisión estática y bloqueantes

Estos hallazgos NO son nuevos exploits reproducidos ni fixes implementados. La evidencia W01 mantiene su alcance histórico de transporte/discovery.

| ID | Observación en la base | Acción |
|---|---|---|
| F01 | `AdapterSupervisor::start` usa `mpsc::channel()` sin presupuesto agregado de cola. | W02-03: acotar mensajes/bytes y preservar vía de control. |
| F02 | `write_all`, `shutdown.wait()` y `Drop.reader.join()` carecen de deadline propio. | W02-03/04: escrituras, teardown, pipes heredados y cleanup real acotados. |
| F03 | Snapshot valida correlation_id; `extract_health` no vincula request/attempt. | W02-05: correlación/replay en todas las respuestas. |
| F04 | Tests hacen return cuando falta CLEVER_TEST_PYTHON. | W02-02: preflight obligatorio, casos realmente ejecutados y rechazo de resultados vacíos. No implica que el run W01 los omitiera. |
| F05 | Cancel es explícitamente no-op en el alcance W01. | W02-12: ACK no equivale a detener inferencia. |
| F06 | El registry se modifica entrada a entrada antes de validar todo el snapshot. | W02-05: stage/validate/commit atómico. |
| F07 | Health del proceso no certifica que un engine/modelo sirva. | W02-08: REGISTERED, LOADABLE, HEALTHY y SERVING separados. |
| F08 | API de branch main consultada indica protected=false. | W02-00/18: revisar rulesets y administración; no confundir YAML con protección. |
| F09 | Kill del launcher/SHA declarado no prueban cleanup ni artefacto cargado. | W02-04/09: process group/container ID y source/image/model digests. Riesgo de diseño, no escape observado. |
| F10 | Inferencia cloud produce egress y coste aunque no ejecute tools. | W02-07/12/14: autorización, presupuesto y efectos remotos UNKNOWN cuando no se conocen. |

## Arquitectura y decisiones

Rust conserva admisión, principal, policy, budget, correlación y supervisión. Python traduce el contrato nativo sin duplicar la autoridad T0. Mantener runtimes especializados y SDK compatibles.

Single-flight inicial por worker es aceptable con BUSY explícito. No anunciar multiplexación hasta probar que cancelar A no afecta B. El control loop debe atender cancel/shutdown mientras otro worker infiere.

Extender contratos solo tras revisar los existentes. Request/chunk/terminal/error/cancel requieren campos tipados para principal, intento, secuencia, modelo/engine, deadline, uso y finish reason. Versionar mediante ADR; regenerar y comprobar Python/Rust/TypeScript/Swift. No esconder semántica crítica en metadata.

Backpressure requiere límites de bytes/mensajes además de frames y un mecanismo de cierre que desbloquee productores/consumidores. Sustituir channel por una cola bloqueante sin tratar cancel/teardown no cierra F01/F02.

Cancel solicitado, ACK y terminación comprobada son hechos distintos. Un timeout local no demuestra ausencia de efectos ni cese de facturación remota. No tokens tras el terminal. Un fallback crea attempt ID nuevo, acumula presupuesto y nunca concatena streams de engines distintos como un único éxito.

Tool-call del modelo = datos; cero ejecución de shell/MCP/browser/tools en W02. Egress remoto requiere grant/configuración confiable, secretos opacos, allowlist de destinos, presupuesto y logs redactados. No migrar memoria upstream.

## Cronograma relativo

Orden por gates, no fechas de entrega ni promesas asíncronas. La disponibilidad de equipo/runners/modelos no está reservada. Cada bloque termina al demostrar su salida.

| Bloque | Tareas | Salida |
|---|---|---|
| B0/G0 | W02-00..02 | Estado/entornos, obligaciones e integridad del harness. |
| B1/G1 | W02-03..05 | I/O, lifecycle, correlación y registry endurecidos. |
| B2/G2 | W02-06..09 | Contratos, egress/budget, engines y lane real. |
| B3/G3 | W02-10 | M1: primera inferencia real por el kernel. |
| B4/G4 | W02-11..14 | Streaming, cancelación, salidas tipadas y fallback. |
| B5/G5 | W02-15..16 | Seguridad, retest, recovery y rendimiento. |
| B6/G6 | W02-17 | Paridad y grafo de pruebas para K obligaciones. |
| B7/G7 | W02-18..19 | M2: release, post-merge, persistencia y handoff. |

`TASK_GRAPH.json` contiene 20 tareas con responsables, dependencias, entregables, tests, evidencia y rollback. Es una descomposición subordinada de CP03-002, no un reemplazo de la DAG global.

Camino crítico: 00→02→03→05→06→07→08→10→11→12→14→15→16→17→18→19. También cumplir el resto de prerequisitos del JSON. La preparación del modelo W02-09 puede solaparse con endurecimiento. Solo paralelizar superficies sin claims compartidos y después de congelar sus interfaces.

## Lanes de prueba

L0 unit/contract: fakes válidos para protocolo y fallos; no prueban modelo real. L1 upstream real + backend simulado: acredita adaptación pero sigue SIMULATED_BACKEND. L2 modelo real y pesos fijados: condición obligatoria de M1. L3 hardware/proveedor real: condición para VERIFIED de obligaciones dependientes de esa plataforma.

Si L2 no cabe/no está disponible, M1 queda BLOCKED. Si una obligación W02 requiere hardware no probado, M2 sigue abierto. No retirar silenciosamente esa obligación. Waivers solo mediante autorización de alcance explícita y separados de VERIFIED.

## Resolución, test, retest y refactor

Defecto→reproducción mínima→causa raíz→test RED→fix mínimo→GREEN→regresión de familias afectadas→gauntlet→retest limpio→evidencia→persistencia.

Cada defecto registra ID, severidad, SHA, entorno, seed, requisito y test. Distinguir hallazgo estático de reproducción. Conservar fallos: elegir el mejor rerun no arregla flakiness. Propuesta inicial: 20 repeticiones del conjunto crítico cancel/flood/restart, con seeds; no es una garantía estadística. Fijar presupuestos de rendimiento antes de medir y comparar same-host.

Refactorizar solo si el fix mínimo deja I/O no cancelable, estados ambiguos, política duplicada, atomicidad imposible o acoplamiento que impide pruebas. Characterization tests primero; separar cambios semánticos y formato; reejecutar test original, contratos, integración nativa, seguridad, recovery, performance y rebuild limpio. No agregar frameworks/dependencias sin necesidad demostrada.

P0: privilegios/secretos/cross-user/efectos descontrolados/espera ilimitada en ruta expuesta; detener y reparar antes de habilitar. P1: pérdida de chunks, correlación, falsos PASS, procesos huérfanos o intentos duplicados; bloquean gate/release. P2: deuda no crítica registrada si no afecta DoD.

Rollback: revertir slice o desactivar ruta por configuración confiable, preservando ledgers, evidencias y estado nativo. Validar el padre seguro y declarar UNAVAILABLE lo que se haya retirado.

## Definition of Done W02

G0–G7 respaldados por ejecución; inferencia real unary/stream; cancel y cleanup reales; structured/tool fragments conservados como datos; fallos/reintentos sin mezclar intentos ni relajar privacidad; K obligaciones justificadas y verificadas; 7.565/646 intactas; cero P0/P1 en ruta publicada; cero omisiones silenciosas de tests obligatorios; evidence con source/runtime/model hashes; validadores y gates sobre SHA exacto; protección/checks de main comprobados antes del release; post-merge validado; claims liberados y handoff recuperable. Si falta una condición, W02 permanece abierto.

## Graphify / COS V2 / 20D

Actualizar subgrafo de inferencia: obligación→símbolo nativo→contrato→adapter→test→resultado→evidence→gate, con ownership, autorización y fallos. P0→P1→P2→P3; ninguna proyección reescribe source truth. Las 20 dimensiones oficiales se asignan en COS20D_REVIEW.json y empiezan REVIEW_REQUIRED. D08 protege prompts/sesiones sin migrar memoria; D17 define progreso/cancel sin UI nueva. No volver a estampar 20D sobre cada raw node.

## Después

W03 agents/tools/MCP; W04 memoria; W05 trazas/evals/learning propuestas; W06 scheduler; W07 seguridad; W08 646 obligaciones; W09 gauntlet; W10 release CP03. Después CP04 OpenClaw, CP05 Omi, CP06 Clicky y CP07–CP12 según gates canónicos.

## Primera acción

Ejecutar boot y validadores de estado/contexto/DAG; `python scripts/cp03/validate_w02_plan.py`; claim de implementación; W02-00. No empezar por generate(). El plan no modifica el checkpoint ni el parity ledger.

## Fuentes

AGENTS, ContextPack, NEXT_ACTIONS, COS20D, I03, adapter.rs, adapter_supervisor.rs y sidecar.py en el SHA base. Documentación primaria: https://doc.rust-lang.org/std/sync/mpsc/fn.channel.html ; https://doc.rust-lang.org/std/process/struct.Child.html ; https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow .
