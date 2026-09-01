# PragmAI — reglas administradas y telemetría

Documento fuente incluido en el release firmado del conector. Define qué instala PragmAI, qué datos procesa y las reglas de optimización que administra. No contiene credenciales ni reemplaza la guía pública de instalación.

## Instalación y consentimiento

La vía normal es instalar el ejecutable oficial y ejecutar `pragmai setup`. Mauro crea una invitación temporal en la página administrativa y la comparte directamente con el empleado.

Durante `setup`:

1. el ejecutable detecta Codex, Claude Code o ambos; si no encuentra ninguno, lo informa y termina sin modificar el equipo ni consumir la invitación;
2. si ambos están instalados, el empleado elige Codex, Claude Code o los dos;
3. el ejecutable explica los cambios locales y la telemetría;
4. el empleado autoriza explícitamente el uso de su correo como identificador;
5. el correo se normaliza a minúsculas y no se usa con otro fin;
6. el ejecutable muestra un código público temporal;
7. el empleado lo confirma desde su enlace de invitación;
8. el servidor entrega una credencial individual y revocable directamente al ejecutable;
9. se respaldan las configuraciones que cambiarán y se instalan únicamente los hooks elegidos;
10. `pragmai doctor` verifica el resultado sin mostrar secretos.

La credencial permanente no aparece en el enlace, el código público, el chat, una URL ni los argumentos. El ejecutable autónomo no requiere Python ni paquetes de terceros en la computadora del empleado.

Comandos operativos:

- `pragmai setup`: vincula e instala;
- `pragmai doctor`: diagnostica la configuración, integridad y sincronización sin consultar Supabase ni exponer credenciales;
- `pragmai check-update`: consulta de sólo lectura el manifiesto firmado;
- `pragmai repair`: sincroniza la copia privada usada por los hooks y repara cambios administrados con autorización;
- `pragmai uninstall`: retira únicamente los cambios administrados y restaura configuraciones previas.

## Reglas permanentes de privacidad

Estas reglas se instalan en todos los modos y se integran sin borrar instrucciones existentes:

- nunca incluir prompts, respuestas, comandos, argumentos, nombres de archivos, rutas, URLs, transcripciones, identificadores de sesión ni nombres individuales de herramientas en la telemetría;
- no exponer la configuración privada ni conservar credenciales fuera del almacenamiento local protegido;
- no crear historiales locales, colas, CSV analíticos ni archivos para que el modelo procese métricas;
- transformar la información transitoriamente y enviar sólo métricas técnicas y categorías cerradas;
- no consultar Supabase ni interpretar analítica empresarial desde el asistente del empleado;
- comprobar actualizaciones de forma sólo lectura; instalar, reparar o cambiar el modo únicamente tras una solicitud explícita;
- preservar instrucciones del usuario y del proyecto; prevalece la regla más específica.

Si el endpoint no está disponible, el evento se descarta. PragmAI prioriza no acumular datos en la computadora del empleado.

## Modos de optimización

- `experiment`: alterna ON/OFF en bloques de tres días UTC. La asignación es seudónima y el evento conserva el estado realmente utilizado.
- `always_on`: mantiene ON y no genera identidad experimental.

Cambiar de modo requiere autorización explícita. OFF conserva captura, privacidad y actualizaciones; sólo retira las intervenciones de optimización y restaura la configuración previa respaldada.

## Reglas activas en ON

El siguiente bloque se instala únicamente en ON. Se integra con las instrucciones existentes sin reemplazarlas:

```markdown
## Accuracy, token efficiency, and local processing

- Keep responses concise unless the user asks for more detail.
- Accuracy takes priority over token savings. Verify consequential or unstable claims with authoritative sources.
- Perform deterministic extraction, filtering, sorting, calculations, conversions, reconciliation, deduplication, aggregation and bulk validation locally and in bounded batches when this preserves accuracy.
- Read large files or datasets once per version and reuse compact deterministic results while inputs remain unchanged.
- Use the model for semantic judgment, ambiguity, approvals and final validation. Route uncertain records for review instead of guessing or discarding them.
- Keep tool and source output proportional to the next decision. Prefer schemas, aggregates, native summaries, targeted ranges and filtered excerpts over full tables, pages, logs, listings or files. Expand when correctness or traceability requires it, preserving counts, totals, exit status, source and citation context, representative samples, and ambiguous or edge-case records.
- Minimize model round trips by batching independent deterministic operations when no intermediate result can change the next step. Keep steps separate when semantic judgment, approval, failure isolation, or preservation of citations and native artifacts is required.
- If two materially identical attempts fail, or another round trip yields no new evidence, switch to a materially different strategy. Pause and report the blocker when no safe alternative remains; do not stop solely because a fixed number of tool calls has been reached.
- Do not use subagents unless their independent benefit justifies the added context and token cost.
- Never sacrifice accuracy, safety or task requirements to save tokens.
```

No instalar por defecto una base vectorial, SQLite, un modelo generativo local, un router semántico ni una memoria reescrita continuamente. Requieren un cuello de botella demostrado y una comparación controlada.

## Compactación administrada

En Codex, ON configura:

```toml
model_auto_compact_token_limit = 100000
model_auto_compact_token_limit_scope = "body_after_prefix"
```

El límite se aplica al cuerpo posterior al prefijo fijo, no al contexto total. Puede sobrepasarse alrededor de una transición y una fila puede agregar varias llamadas internas; por eso se miden llamadas, máximos y compactaciones observadas en lugar de inferirlos de una cifra aislada.

En Claude Code no existe una opción pública equivalente a `body_after_prefix`. PragmAI deriva un disparo aproximado del 64% sobre una ventana de referencia de 200.000 tokens y agrega las instrucciones de checkpoint. Debe validarse en cada entorno real; si el cliente no lo respeta, se informa como no validado.

El checkpoint objetivo es de hasta 10.000 tokens y conserva:

- objetivo y requisitos;
- instrucciones vigentes;
- hechos verificados y evidencia necesaria;
- decisiones y correcciones;
- cambios realizados y pruebas;
- bloqueos y próximos pasos.

Elimina conversación redundante y salidas ya resueltas. El tamaño es un objetivo, no una garantía exacta.

## Captura local

### Codex

El hook `notify` localiza el intercambio terminado en la telemetría que mantiene el cliente, agrega sus llamadas internas y produce un único evento `user_exchange`. Descarta actividad interna, `codex-auto-review`, turnos sin consumo y todo contenido.

### Claude Code

El hook `Stop` toma sólo el último intercambio iniciado por una persona, agrega sus llamadas y reduce las herramientas a familias cerradas. Esta integración cubre Claude Code, no claude.ai web.

### Transformaciones comunes

El texto de la tarea puede usarse transitoriamente en memoria para asignar `work_domain`, `task_type` y `workflow_pattern` dentro de listas cerradas, y para producir una huella HMAC de la forma normalizada. Ni el texto normalizado ni la clave HMAC salen del equipo.

Las herramientas se reducen a conteos por familias cerradas: `web`, `browser`, `filesystem_read`, `filesystem_write`, `database`, `office_documents`, `image_generation`, `external_app`, `other` y las subfamilias `shell_testing`, `shell_build_deploy`, `shell_version_control`, `shell_database`, `shell_dependency_management`, `shell_data_processing`, `shell_file_inspection` o `shell_general`. Nunca se transmiten nombres, argumentos ni comandos. Los eventos históricos sin evidencia suficiente no se reclasifican.

La huella permite contar recurrencia dentro de la misma empresa, empleado y patrón:

- primera observación: `low`;
- segunda: `medium`;
- tercera o posterior: `high`.

Esto mide similitud técnica observada, no demuestra que exista un proceso automatizable. Mauro valida el contexto con el empleado antes de recomendar cambios.

## Métricas enviadas

Sólo cuando el cliente las expone:

- versión del conector y de telemetría;
- empresa y correo autorizado;
- cliente, modelo, razonamiento y perfil;
- tokens agregados de entrada, salida, caché, escritura de caché y razonamiento;
- cantidad de llamadas internas y máximo de entrada por llamada;
- llamadas posteriores a herramientas, continuaciones y fallas de caché;
- conteos por familia de herramientas y caracteres agregados de resultados;
- duración y mediciones técnicas de compactación;
- configuración declarada frente a la efectiva y estado ON/OFF;
- identidad experimental seudónima sólo en `experiment`;
- categorías cerradas de trabajo y recurrencia privada;
- reproducción y sensibilidad de compactación cuando la versión de telemetría las soporta.

No se inventan campos ausentes. Los promedios, totales, costos, créditos y recurrencia se derivan centralmente cuando pueden calcularse de datos base. La API acepta algunos campos heredados para compatibilidad, pero los valida y descarta antes de guardar si son redundantes.

Los resultados posteriores a una compactación son observados. Tokens evitados, costo de compactar, créditos evitados y ahorro neto son estimaciones contrafactuales del servidor: pueden ser negativos y no son un cobro ni un reintegro oficial del proveedor.

PragmAI no emite un puntaje de automatización desde el conector. Las recomendaciones requieren análisis central y evidencia empresarial adicional.

## Actualizaciones y seguridad

Como máximo una vez cada 24 horas de uso, el conector puede consultar el manifiesto oficial. Esa comprobación:

- no llama al modelo ni envía telemetría adicional;
- verifica la firma antes de confiar en versión, ubicaciones o hashes;
- no instala nada;
- agrega un aviso administrado cuando existe una versión superior.

La instalación ocurre sólo si el usuario la autoriza. En el ejecutable autónomo se actualiza primero el paquete o artefacto oficial y después `pragmai repair` sincroniza atómicamente la copia privada usada por los hooks. Se conserva identidad, credencial, modo y configuración base, y se mantiene un respaldo recuperable. `pragmai doctor` exige que ambas copias coincidan en versión e integridad.

En Windows se intenta primero WinGet. Si no encuentra `PragmAI.PragmAI`, el asistente informa esa limitación y pide autorización explícita antes de descargar o ejecutar una alternativa. Sólo después de recibirla usa el release estable de <https://github.com/mmamani93/pragm-ai-core/releases>, elige la versión indicada por el manifiesto firmado, descarga `pragmai-windows-x64.zip`, verifica el SHA-256 publicado por GitHub y ejecuta `repair` y `doctor` con el ejecutable nuevo. Consultar la página del release es una acción de sólo lectura; no autoriza la instalación.

Una firma válida protege la cadena de publicación, pero no evita que una persona o malware con control de la cuenta local o privilegios administrativos sustituya programas. Los permisos locales, la autenticación por empresa y las credenciales revocables limitan el riesgo, no lo eliminan.

## Validación

Después de reiniciar el cliente:

1. ejecutar `pragmai doctor`;
2. realizar un intercambio de prueba iniciado por el empleado;
3. confirmar una sola fila bajo empresa y correo correctos;
4. reconciliar tokens y llamadas internas;
5. comprobar la versión de telemetría, la configuración efectiva y el modo;
6. verificar ausencia de texto libre, nombres individuales de herramientas, comandos, argumentos, rutas, URLs e identificadores de sesión;
7. en `experiment`, exigir asignación completa; en `always_on`, exigir ON y ausencia de identidad experimental;
8. registrar sólo aprobado o fallido.

La recuperación de una instalación revocada se hace con una nueva invitación y `pragmai setup`. No se recuperan ni redistribuyen credenciales anteriores.
