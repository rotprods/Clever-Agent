# Clever-Agent — investigación materializada de arquitectura, PR, seguridad y QA

Fecha de corte: 2026-09-14  
Repositorio: `rotprods/Clever-Agent`  
Commit de partida: PR #28 en `3885ba717cba450fd7283eb45a9e43b09b26b1a0`  
Commit local de revisión inicial: `8916711`  
Estado de publicación: pendiente de autorización explícita de exportación a GitHub.

## Resumen ejecutivo

La arquitectura tiene una disciplina de evidencia inusualmente fuerte: estado canónico, DAG de tareas, claims, riesgos, decisiones, pruebas y handoffs son validables y el ContextPack es determinista. La implementación G1 revisada es razonable y no se encontró un defecto bloqueante nuevo en su código. Sin embargo, el sistema de release todavía permite una brecha entre **evidencia histórica** y **certificación del candidato exacto**: el HEAD de la PR #28 tiene cero workflows, cero statuses y cero reviews hospedados. Por tanto, el resultado correcto es **CHANGES REQUIRED / Rust no verificado**, no aprobación.

Se repararon tres familias de tests que estaban acopladas al estado temporal o al checkout, se creó un gauntlet E2E de cierre seguro y una prueba transversal de integridad del repositorio. Después se reconcilió una segunda revisión independiente ya publicada, incorporando diez invariantes adicionales y un workflow exact-head con carriles Python, Rust y OpenJarvis nativo. El resultado Python final es **238/238 PASS**. La auditoría Python de dependencias no detecta vulnerabilidades conocidas. La auditoría Rust ejecutable local permanece bloqueada por ausencia de Cargo y se traslada al CI hospedado.

## Topología arquitectónica comprobada

| Capa | Autoridad / ubicación | Función | Estado |
|---|---|---|---|
| North Star | `GOAL_STATE.json`, `GOAL.md` | Checkpoint, iteración, paridad y restricciones | Consistente |
| Ejecución | `EXECUTION_STATE.json`, `iterations/03/waves/CP03-W02/TASK_GRAPH.json` | Frontera y dependencias | `W02-06 READY` |
| Contratos | `contracts/proto`, `contracts/jsonschema`, SDKs | Wire format y generación multilenguaje | G1 listo; inferencia pendiente |
| Kernel | `kernel/crates/clever-kernel` | Supervisión, framing, control, registro, lifecycle | Fuente revisada; gate Rust pendiente |
| Adaptador | `adapters/openjarvis` | Bridge real a OpenJarvis | Correlación corregida |
| Evidencia | `evidence/`, `reports/`, `sessions/` | Recibos reproducibles y límites de claim | Consistente |
| Control agéntico | `.agentic/context`, `ledgers/`, `HANDOFF.md` | Continuidad, claims y auditoría append-only | Validadores PASS |
| CI | 36 workflows GitHub Actions | Prueba y persistencia automatizada | Deuda supply-chain alta |

## Estado canónico que no debe falsearse

- Checkpoint `CP03`, iteración `I03`, wave `CP03-W02`.
- Primera tarea ejecutable: `W02-06 — Contratos tipados de inferencia`.
- `W02-00..W02-05` están completos con evidencia; G1 cubre transporte/lifecycle, no inferencia.
- K=47: 37 capacidades propias + 10 compartidas.
- Denominador global 7.565; obligaciones OpenJarvis 646; VERIFIED 0.
- Ninguna prueba o review de esta investigación promueve paridad.

## Mapa de PR y decisión recomendada

| PR | Estado | Papel real | Decisión |
|---|---|---|---|
| #15 | Draft abierta, antigua | Primera rama de hardening/control con auto-writeback sensible | No mezclar ni fusionar; conservar como histórico hasta retirar/reconciliar explícitamente |
| #28 | Abierta, mergeable | Candidata principal de cleanup/teardown G1 | `CHANGES REQUIRED` hasta certificar Rust/Clippy en SHA exacto |
| #29 | Draft abierta | Donante de reparaciones de planificación, correlación y diagnóstico | Mantener como donante; cinco fixes estrechos ya fueron portados a #28 |

La decisión arquitectónica correcta es preservar #28 como candidata bounded, no hacer un mega-merge entre ramas históricas y no abrir W02-07/08 antes de definir y probar W02-06.

## Revisión de código de la PR #28

- 24 archivos cambiados, 1.964 adiciones y 56 eliminaciones frente a `main`.
- Las respuestas del sidecar ya correlacionan con el `frame_id` activo; el hello inicial queda no solicitado.
- El supervisor usa IDs de frame monotónicos y envenena la sesión ante ambigüedad de protocolo.
- El proceso adaptador entra en un grupo Unix propio; shutdown/drop aplican terminación y waits acotados.
- El cleanup externo exige ejecutable absoluto, limpia el entorno y tiene timeout.
- Los workflows nuevos fijan las siete acciones externas a SHA completo y protegen sus escrituras con CAS y allowlists.
- No se halló un nuevo defecto de corrección o inyección demostrable en el diff. Esta conclusión es estática y no sustituye la ejecución Rust.

## Revisión QA y test E2E

### Defectos reparados

1. Un test de Xcode inspeccionaba accidentalmente manifests del repositorio anfitrión; ahora usa fixture temporal.
2. Tests históricos CP02 ejecutaban un evaluador pre-transición contra estado CP03; ahora verifican el recibo histórico y prueban por separado el rechazo fail-closed actual.
3. Tests del compilador W02 exigían productos generados deliberadamente no versionados; ahora materializan inputs/outputs en raíces temporales.

### Nuevos gates

- `scripts/release_gauntlet.py`: estado, ContextPack, determinismo, next-actions, DAG W02, paridad, evidencia G1, workflows afectados, regresiones Python y lane Rust.
- `tests/test_release_gauntlet.py`: rechaza acción no fijada, `pull_request_target`, escritura sin CAS y falsos PASS cuando falta Cargo.
- `tests/test_repository_integrity.py`: parsea todos los JSON y cada fila JSONL/NDJSON versionada, exige objetos y rechaza marcadores de conflicto.

### Matriz final

| Gate | Resultado |
|---|---|
| Suite Python completa | 238/238 PASS |
| Estado/contexto/plan | PASS |
| ContextPack determinista | PASS |
| Paridad OpenJarvis | PASS, 0 promociones |
| Seguridad workflows #28 | PASS |
| Gauntlet diagnóstico | `PASS_WITH_RUST_BLOCKED` |
| Gauntlet estricto | `BLOCKED` |
| GitHub checks en SHA #28 | 0 |
| Rustfmt/tests/Clippy exact-head | BLOCKED en este runner |

## Revisión de seguridad

### Candidato #28

- 7/7 usos de actions fijados a SHA de 40 caracteres.
- Sin `pull_request_target`, dispatch manual con escritura ni curl-to-shell.
- Escrituras limitadas a rama esperada, con comparación del remoto y allowlist de mutaciones.
- Riesgo residual: workflows capaces de auto-commit. La protección de rama y el mínimo permiso por job siguen siendo controles obligatorios.

### Repositorio completo

| Hallazgo | Severidad | Evidencia | Tratamiento |
|---|---:|---:|---|
| Actions con tags mutables | Remediado | 0 refs tras corregir 51 en 20/36 workflows | SHAs de 40 hex + gate repo-wide de no regresión |
| Superficie `contents: write` | Media | 19/36 workflows | Reducir a job, revisar eventos, CAS y allowlists |
| Checks ausentes en candidato exacto | Alta para release | 0 runs/statuses | Required checks sobre SHA exacto |
| Secretos por patrones conocidos | Sin hallazgo | 0 matches versionados | Mantener secret scanning nativo |
| Dependencia Python | Sin hallazgo conocido | protobuf 7.36.0, pip-audit PASS | Repetir en CI |
| Dependencias Rust | No evaluado dinámicamente | locks con 32 checksums, 0 deps Git | Ejecutar cargo-audit/RustSec en CI |
| Cleanup sobreafirmado | Alta para workloads externos | resultados de kill/cleanup/join descartados antes de `termination_complete=true` | Emitir resultado estructurado y exigir éxito observable |
| Stderr heredado | Media antes de credenciales | `stderr(Stdio::inherit())` sin límite/redacción | Buffer acotado y redacción antes de W02-07 |
| Portabilidad teardown | Media | process groups solo Unix | Declarar constraint o usar Windows Job Objects |
| Protección de `main` | Alta para release | branch protection/rulesets ausentes en la inspección independiente | Required checks y revisión obligatoria |

## Decisiones y gobernanza

El repositorio contiene 11 decisiones, 7 riesgos, 21 evidencias, 34 eventos de claim, 26 eventos de run y 39 eventos de wave antes del cierre de esta investigación. La estructura append-only y los validadores reducen la pérdida de contexto, pero no deben confundirse con ejecución: un receipt histórico válido prueba su SHA, no automáticamente el nuevo HEAD.

Regla propuesta para todas las releases:

1. todo gate declara el SHA validado;
2. solo checks adjuntos a ese SHA autorizan merge;
3. evidencia histórica sirve como regresión, no como sustituto;
4. tooling ausente produce `BLOCKED`, nunca PASS;
5. ninguna automatización con permisos de escritura modifica `main` directamente;
6. los cambios de seguridad repo-wide viven en una wave separada y revisable.

## Plan de avance ejecutable

### P0 — Certificar la candidata

- Publicar la rama de review y abrir PR hija contra `wave/cp03/w02-teardown-cleanup`.
- Ejecutar gauntlet estricto con Cargo.
- Exigir rustfmt, lifecycle legacy, adapter lifecycle, control regressions, Clippy y cargo-audit.
- Adjuntar checks al SHA exacto y solo entonces revaluar #28.

### P1 — CI Security Hardening

- Inventariar las 51 referencias mutables y sustituirlas por SHAs verificadas.
- Reducir los 19 workflows escribibles a permisos por job.
- Añadir un policy test repo-wide que impida nuevas referencias mutables.
- Activar CODEOWNERS/required review para `.github/workflows/**`.

### P1 — W02-06 inferencia tipada

- Definir request, chunk, terminal, error y cancelación con IDs de intento, deadlines e idempotencia.
- Regenerar Python/Rust/TypeScript/Swift.
- Añadir golden round-trips, version skew y secuencias inválidas.
- Mantener VERIFIED=0 hasta ejecutar inferencia real con criterios terminales.

## Airtable operacional

Se creó y publicó `Clever-Agent Control Plane`, con tablas `Actions` y `Reviews`, cuatro acciones priorizadas y el review `CHANGES REQUIRED`. Interfaz: https://airtable.com/app93ubKjsFCe5QVb/pag4OggNkpNvng9TP/edit

## Definition of Done de esta investigación

- [x] Arquitectura y frontera reconstruidas.
- [x] PR abiertas y decisiones reconciliadas.
- [x] Code/security/QA review del candidato.
- [x] Tests defectuosos reparados sin rebajar assertions.
- [x] Gauntlet fail-closed creado.
- [x] Integridad transversal creada.
- [x] Dos líneas de revisión reconciliadas sin sobrescribir historial.
- [x] Escáner supply-chain corregido: 51 referencias reales, no 27.
- [x] 238/238 pruebas Python verdes.
- [x] Dependencia Python y secretos auditados.
- [x] Airtable publicado.
- [x] Rust/Clippy y E2E nativo ejecutados en el HEAD de revisión exacto mediante CI alojada.
- [x] Commit, PR y review publicados en GitHub; PR #30 integrada en la rama de PR #28.
- [x] Las 51 referencias mutables de Actions sustituidas por SHAs auditables.
- [x] Gate repo-wide añadido para impedir regresiones de referencias mutables.

## Avance 2026-09-15 — convergencia y hardening

PR #30 se integró mediante merge commit en la rama de PR #28. El HEAD resultante es
`2ac2ec9512381d297a34e5ae8d0d942f62f93cf8`; `main` permanece sin modificar. Este
nuevo HEAD debe recibir sus propios checks antes de cualquier decisión de release.

En una wave separada se resolvió `SUPPLY-P1-UNPINNED-ACTIONS`: 51 referencias
mutables fueron reemplazadas por los commits que resolvían sus aliases auditados
(`checkout@v4`, `setup-python@v5`, `setup-node@v4`, `upload-artifact@v4`,
`download-artifact@v4` y `buf-setup-action@v1`). El escáner dedicado cubre tanto
`- uses:` como el `uses:` anidado bajo pasos con nombre y falla ante cualquier ref
externa que no sea un SHA hexadecimal de 40 caracteres.

El HEAD convergido posterior a la integración es
`1988d56d1d948422c2b27cc57259d4ac910cee93` y pasó 11/11 workflows alojados.
También se materializaron `D-0012`–`D-0019` y `RISK-0006`–`RISK-0011`, cerrando
la deriva de gobernanza sin alterar K=47, el denominador 7.565 ni VERIFIED=0.
