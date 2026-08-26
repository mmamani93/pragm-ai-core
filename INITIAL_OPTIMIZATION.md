# PragmAI Initial Optimization

Instalación guiada para Codex y Claude Code. Un prompt independiente del modelo hace que el asistente lea estas instrucciones completas, instala reglas persistentes y activa telemetría agregada sin contenido. El modo se fija en el prompt privado: `experiment` alterna ON y OFF cada tres días UTC; `always_on` mantiene activas las reglas de eficiencia y la compactación inteligente y queda fuera de esa comparación.

## Índice

- [Qué se medirá](#qué-se-medirá-explicado-de-forma-simple)
- [Datos fijados por PragmAI](#datos-fijados-por-pragmai-antes-de-entregar-el-prompt)
- [Instrucciones para el asistente](#instrucciones-para-el-asistente-que-recibe-este-documento)
- [Verificación e instalación](#verificación-e-instalación)
- [Reglas iniciales de optimización](#reglas-iniciales-de-optimización)
- [Compactación inteligente](#compactación-inteligente-de-codex-y-claude-code)
- [Cómo funciona la captura](#cómo-funciona-la-captura)
- [Repetibilidad y automatización](#repetibilidad-y-automatización)
- [Métricas enviadas](#métricas-enviadas)
- [Validación final](#validación-final)
- [Reinstalación y rotación](#reinstalación-y-rotación)
- [Límite de seguridad](#límite-de-seguridad)

## Qué se medirá, explicado de forma simple

PragmAI registra estadísticas técnicas del uso del asistente, no la conversación. Un registro futuro puede verse así:

- empresa: la empresa asignada por PragmAI;
- usuario: el correo que el empleado autorizó;
- tipo de tarea: por ejemplo, análisis de datos;
- consumo total: por ejemplo, 12.450 tokens;
- herramientas utilizadas: por ejemplo, lectura de archivos.

No incluye el pedido real, la respuesta, archivos, comandos, rutas, enlaces ni nombres concretos de herramientas.

La entrega vigente se hace mediante un único prompt privado generado desde la plantilla canónica. Los ZIP antiguos sólo conservan compatibilidad histórica. Intervienen cuatro componentes verificables:

1. `README.md`, guía humana con el prompt de inicio;
2. `INITIAL_OPTIMIZATION.md`, estas instrucciones;
3. `pragm_ai_connector.py`, conector determinístico y autocontenido PragmAI `0.6.6`;
4. `skills/pragm-ai-updater/`, skill que permite comprobar e instalar actualizaciones verificadas después de la instalación.

Separarlos permite revisar, probar y verificar el programa como código. Incrustarlo dentro del Markdown haría más difícil detectar una sustitución maliciosa y no mejoraría la seguridad.

## Datos fijados por PragmAI antes de entregar el prompt

Mauro debe reemplazar este valor en la copia destinada a la empresa:

```text
PRAGMAI_COMPANY_ID="__COMPANY_ID_ASSIGNED_BY_PRAGMAI__"
```

No modificarlo durante el alta. No es una contraseña, pero determina a qué empresa se atribuye el evento. El código de ingesta se incorpora al prompt privado personalizado generado para esa empresa; nunca se pega en este documento canónico, GitHub ni el sitio público.

El conector oficial de esta entrega debe tener este SHA-256:

```text
50a461a80a0e5393622c1fb98b4b1e8fccaa801cf28d507989766726580cbf10
```

Mauro debe comunicar el hash también por un canal confiable independiente. Un archivo y un hash reemplazados juntos por un atacante no prueban integridad.

## Instrucciones para el asistente que recibe este documento

1. Explicar que PragmAI medirá únicamente métricas técnicas y categorías cerradas. No enviar prompts, respuestas, comandos, argumentos, archivos, rutas, URLs, transcripciones, nombres de herramientas individuales ni identificadores de sesión.
2. Pedir autorización explícita para iniciar la medición y preguntar qué correo laboral o personal autoriza el empleado a usar como `employee_id`.
3. No continuar si no hay consentimiento explícito o si el correo no fue autorizado para este fin.
4. Confirmar que `PRAGMAI_COMPANY_ID` ya fue definido por PragmAI y no cambiarlo.
5. Verificar el conector antes de ejecutarlo. Si el hash no coincide, detenerse; no intentar repararlo, descargar otro archivo ni ignorar la advertencia.
6. Tomar del prompt privado el código de instalación ya incluido y pasarlo directamente al conector junto con el correo y el consentimiento, sin pedirle al empleado que lo escriba, repetirlo en la respuesta final ni guardarlo en archivos auxiliares.
7. Explicar que la configuración de optimización alterna entre ON y OFF en bloques de tres días UTC para comparar créditos promedio por intercambio; el empleado no elige el brazo.
8. Instalar sólo el cliente que realmente utiliza el empleado y reiniciarlo.
9. Informar a Mauro el resultado aprobado/fallido sin volver a copiar el código ni otros datos privados.

La autorización debe dejar claro que el correo sí será almacenado como identificador del empleado. Es la única excepción de identidad del piloto y debe ser voluntaria y explícita.

## Verificación e instalación

La vía única es pegar el prompt completado por Mauro a un asistente de programación local con terminal. El prompt descarga por HTTPS este documento y el conector oficial, obliga a leer el documento completo y verifica el conector antes de ejecutarlo. No usar `curl | sh`, un fork ni un archivo copiado desde un mensaje no verificado.

Antes de descargar el conector, el asistente comprueba si existe Python 3.9 o posterior y conserva la ruta exacta del intérprete elegido. PragmAI no necesita `pip` ni paquetes de terceros. Si falta Python, instalarlo es un cambio separado que requiere permiso explícito: el consentimiento para telemetría no autoriza por sí solo a modificar el sistema.

Después de recibir ese permiso, el asistente ejecuta por su cuenta la instalación oficial correspondiente y continúa automáticamente:

- Windows: Python Install Manager distribuido por Python Software Foundation mediante python.org, Microsoft Store o WinGet, seguido de un runtime estable;
- macOS: instalador firmado y notarizado descargado de python.org;
- Linux: paquete `python3` del gestor oficial de la distribución.

El empleado no copia comandos. Sólo confirma personalmente los diálogos de seguridad, credenciales administrativas o controles de cuentas que el sistema operativo no permite delegar. Si una política corporativa bloquea la instalación, el asistente se detiene e informa el bloqueo; no usa una fuente alternativa, un script remoto ni un instalador no oficial. Una vez instalado, localiza el intérprete aunque la terminal todavía no haya actualizado su `PATH`, comprueba su versión y retoma PragmAI en la misma tarea.

Primero verificar con una herramienta confiable del sistema operativo. No ejecutar el conector para que se verifique a sí mismo: si hubiera sido sustituido, eso le daría ejecución antes de comprobar su integridad.

En macOS puede usarse:

```bash
printf '%s  %s\n' \
  '50a461a80a0e5393622c1fb98b4b1e8fccaa801cf28d507989766726580cbf10' \
  'pragm_ai_connector.py' \
  | /usr/bin/shasum -a 256 --check
```

Continuar únicamente si el resultado exacto es `pragm_ai_connector.py: OK`.
Después de verificar, evitar cualquier reemplazo o edición del archivo antes de
ejecutar la instalación.

En Linux usar `sha256sum -c` con la misma huella. En Windows usar `Get-FileHash .\pragm_ai_connector.py -Algorithm SHA256` desde PowerShell y comparar el resultado exacto. El prompt entregado al asistente le exige detectar el sistema y elegir la herramienta correspondiente.

Luego instalar con Python 3. En macOS o Linux suele ser `python3`; en Windows suele ser `py -3` o `python`. El modelo pasa los tres valores ya conversados para completar el alta sin otra interacción. Ejemplo Unix:

```bash
python3 pragm_ai_connector.py install \
  --company-id "__COMPANY_ID_ASSIGNED_BY_PRAGMAI__" \
  --employee-email "<correo autorizado>" \
  --consent-confirmed \
  --ingest-secret-stdin
```

Después de iniciar el proceso interactivamente, el modelo escribe el código ya incluido en el prompt privado únicamente en la entrada estándar y agrega un salto de línea. No debe pedírselo al empleado, incluirlo en el comando, una variable de entorno ni un archivo temporal.

El instalador detecta por sí solo si la computadora usa Codex, Claude Code o ambos. El empleado no elige ni escribe un parámetro de cliente.

El prompt es compatible con cualquier agente de programación que pueda leer archivos y operar la terminal, incluido Claude Code dentro de Warp. Eso no vuelve universal a la captura: si el equipo no tiene Codex ni Claude Code, el asistente debe detenerse porque todavía no existe un hook de telemetría validado para ese cliente.

El instalador:

- copia el conector verificado en el directorio de datos del usuario: `~/.local/share/pragm-ai/` en macOS/Linux o `%LOCALAPPDATA%\PragmAI\` en Windows;
- guarda URL, empresa, correo autorizado, secreto y clave HMAC en una configuración privada: `~/.config/pragm-ai/config.json` en macOS/Linux o `%LOCALAPPDATA%\PragmAI\config.json` en Windows;
- conserva una copia recuperable de cada configuración que modifica;
- integra `notify` en Codex y conserva una notificación previa compatible;
- integra un hook `Stop` en Claude Code sin activar un exportador OpenTelemetry genérico;
- conserva las instrucciones existentes e instala reglas administradas persistentes en el archivo global que cada cliente carga al iniciar;
- asigna un brazo inicial seudónimo y alterna obligatoriamente ON/OFF cada tres días UTC;
- en ON configura `smart_100k` y un checkpoint objetivo de hasta 10.000 tokens; en OFF restaura la configuración previa capturada y omite las reglas de optimización;
- instala `pragm-ai-updater` en Codex para futuras actualizaciones explícitas; el conector exige un manifiesto firmado por la clave pública incorporada, verifica después el SHA-256 de cada archivo y contiene una copia exacta del skill.

El archivo local de configuración contiene credenciales operativas, la configuración base necesaria para restaurar OFF, la asignación experimental activa y el estado del chequeo de actualizaciones; no contiene telemetría histórica. No se crea CSV, cola de métricas, base local ni archivo de análisis. Si el endpoint está temporalmente caído, ese evento no se conserva para reintento: se prioriza no acumular datos en la computadora del empleado.

En Codex las reglas se agregan a `~/.codex/AGENTS.override.md` cuando ya existe un override global activo; en caso contrario se usa `~/.codex/AGENTS.md`. En Claude Code se agregan a `~/.claude/CLAUDE.md`. Los bloques están delimitados, son actualizables y preservan el contenido previo. Hay que reiniciar el cliente: desde la sesión siguiente, el modelo recibe estas reglas automáticamente sin volver a pegar toda esta guía.

## Reglas iniciales de optimización

Este bloque se instala únicamente cuando la asignación experimental está ON. Las reglas de privacidad, secreto, análisis central y actualización permanecen en ambos brazos. OFF no significa desinstalar PragmAI: significa medir el comportamiento sin estas intervenciones.

Leer primero las instrucciones existentes del usuario y del proyecto. Integrar este bloque sin borrar preferencias ni reglas más específicas:

```markdown
## Accuracy, token efficiency, and local processing

- Keep responses concise unless the user asks for more detail.
- Accuracy takes priority over token savings. Verify consequential or unstable claims with authoritative sources.
- When extraction, filtering, sorting, calculations, conversions, reconciliation, deduplication, aggregation or bulk validation can be performed deterministically, do them locally and in bounded batches.
- Read large sources once and reuse deterministic intermediate results while inputs remain unchanged.
- Use the model for semantic judgment, ambiguity, approvals and final validation. Route uncertain records for review instead of guessing or discarding them.
- Minimize model round trips when the next operations need no new judgment. Preserve representative samples, counts, totals and edge-case checks.
- Do not use subagents unless their independent benefit justifies the added context and token cost.
- Never sacrifice accuracy, safety or task requirements to save tokens.
```

No instalar por defecto una base vectorial, SQLite, un modelo generativo local, un router semántico ni una memoria reescrita continuamente. Esas medidas requieren un cuello de botella demostrado y una comparación controlada.

## Compactación inteligente de Codex y Claude Code

Cuando la asignación está ON, el conector instala:

```toml
model_auto_compact_token_limit = 100000
model_auto_compact_token_limit_scope = "body_after_prefix"
```

El checkpoint conserva objetivo, requisitos, instrucciones vigentes, hechos verificados, decisiones, correcciones, cambios, pruebas, bloqueos y próximos pasos; elimina conversación redundante y salidas ya resueltas. El objetivo de 10.000 tokens se refiere al checkpoint, no al total del intercambio y es una instrucción de tamaño, no una garantía exacta.

En Codex, 100.000 tokens es el crecimiento permitido para el cuerpo de la conversación después del prefijo fijo, no el total efectivo. Con el prefijo observado de este entorno, el objetivo total queda aproximadamente entre 125.000 y 130.000 tokens. No es un máximo rígido: una llamada puede sobrepasarlo alrededor de la transición y una fila suma todas las llamadas internas del intercambio. PragmAI registra `model_calls`, promedio y máximo por llamada, llamadas que superaron el umbral y compactaciones observadas para comprobar el comportamiento real.

Telemetría v3 deduplica marcadores equivalentes de una misma compactación y, cuando el cliente brinda datos suficientes, separa contexto previo, checkpoint, primera llamada posterior, cantidad de llamadas posteriores y tokens posteriores. Guarda una sola estructura canónica por compactación; los conteos y totales económicos se derivan centralmente para no duplicar datos.

En Claude Code no existe una opción pública equivalente al alcance `body_after_prefix`. El instalador deriva de la misma política un disparo del 64% sobre una ventana de referencia de 200.000 tokens y agrega las instrucciones de checkpoint a `~/.claude/CLAUDE.md`; esto apunta a unos 127.000 tokens, pero es una aproximación dependiente de la versión y del modelo. La validación real debe confirmar que aparecen límites de compactación en la telemetría; si Claude ignora el override, se informa como no validado en vez de afirmar que funciona.

## Cómo funciona la captura

### Codex

Codex ejecuta el conector al terminar un turno. El conector localiza ese turno en la telemetría que ya mantiene el cliente, suma sus llamadas internas y genera un solo evento `user_exchange`. Descarta `codex-auto-review`, actividad interna, turnos sin consumo y cualquier contenido.

### Claude Code

Claude Code ejecuta el conector mediante el hook `Stop`. El conector toma únicamente el último intercambio iniciado por una persona, agrega sus llamadas y reduce nombres de herramientas a familias cerradas. Esta integración corresponde a Claude Code; no convierte claude.ai web en un cliente con telemetría exacta.

### En ambos casos

El texto del pedido se usa transitoriamente, en memoria, sólo para:

- elegir `work_domain`, `task_type` y `workflow_pattern` dentro de listas cerradas;
- estimar un potencial preliminar de automatización con baja confianza;
- generar una huella HMAC de la forma normalizada de la tarea.

El texto normalizado y la clave HMAC nunca salen de la computadora. Las herramientas se envían en un único mapa de conteos por familia: `web`, `browser`, `filesystem_read`, `filesystem_write`, `shell`, `database`, `office_documents`, `image_generation`, `external_app` u `other`. Si Codex agrupa varias herramientas dentro de una orquestación programática, el conector inspecciona transitoriamente esa estructura y transmite únicamente esos conteos; nunca transmite nombres, argumentos ni comandos. Los eventos anteriores no pueden reclasificarse y aparecen centralmente como históricos sin clasificar.

El backend vuelve a validar el esquema, autentica el secreto contra el `company_id` y calcula costo, recurrencia y agregados del lado del servidor. Supabase es la única persistencia de métricas y Mauro realiza allí el análisis centralizado.

## Repetibilidad y automatización

Cada huella se cuenta dentro de la misma empresa, empleado y patrón de trabajo. No se almacenan ni la etiqueta duplicada `repeatability` ni un contador acumulado de recurrencia; ambos se derivan al consultar:

- primera observación: `low`;
- segunda: `medium`;
- tercera o posterior: `high`.

Esto mide recurrencia observada, no una opinión sobre si la categoría podría repetirse. La huella no revela qué tarea fue ni demuestra que dos intercambios correspondan al mismo proceso de negocio. Mauro entrevista al empleado antes de recomendar una automatización.

## Métricas enviadas

Cuando el cliente las expone:

- cliente, modelo, razonamiento y perfil;
- tokens agregados de entrada, salida, caché, escritura de caché y razonamiento;
- llamadas internas y máximo de entrada por llamada; el promedio se deriva como `tokens_input / model_calls`;
- llamadas posteriores a herramientas, continuaciones y fallas de caché;
- conteos por familia de herramientas;
- duración, mediciones de compactación y llamadas sobre el umbral;
- contexto previo y posterior a cada compactación, llamadas posteriores y tokens evitados estimados;
- versión de telemetría, coincidencia técnica entre el perfil declarado y la configuración efectiva y flag ON/OFF; `experiment_id` e identificador HMAC de bloque-usuario sólo cuando la instalación participa del A/B;
- categorías cerradas de trabajo, recurrencia privada y potencial preliminar de automatización.

No se inventan métricas ausentes. El costo API equivalente y los créditos se calculan en Vercel con el catálogo versionado; una suscripción plana sigue teniendo como costo real su abono, no el equivalente API de cada turno.

No se transmiten ni almacenan por separado categorías y resultados legados, `tokens_total`, listas o totales de herramientas, promedios derivables, contadores de recurrencia, conteos duplicados de compactación, créditos totales ni agregados económicos que ya están dentro de `compaction_measurements`. Los conectores anteriores pueden seguir enviándolos; la API los valida y descarta antes de guardar.

Las llamadas y tokens posteriores a una compactación son observados. Los tokens evitados, el costo de compactar, los créditos evitados y el ahorro neto son estimaciones contrafactuales calculadas en el servidor; pueden ser negativos y no representan un cobro o reintegro oficial del proveedor.

## Validación final

Después de reiniciar el cliente:

1. comprobar `GET https://m-pragm-ai.vercel.app/api/health`;
2. realizar un único intercambio de prueba iniciado por el empleado;
3. confirmar en PragmAI que apareció una sola fila bajo empresa y correo correctos;
4. confirmar que el modelo no sea `codex-auto-review`;
5. comprobar que `tokens_input + tokens_output` coincida con el total derivado y que `model_calls` muestre las llamadas internas;
6. verificar ausencia de texto libre, nombres de herramientas, rutas, URLs e identificadores de sesión;
7. comprobar telemetría v4, `config_status=matched`, familias locales cerradas y `tool_result_characters`; en `experiment`, exigir asignación completa y perfil coherente con ON/OFF; en `always_on`, exigir ON, `smart_100k` y ausencia de identificadores experimentales;
8. registrar solamente aprobado/fallido.

El asistente del empleado no consulta Supabase, no evalúa sus métricas y no decide optimizaciones posteriores. Mauro realiza el análisis con `OPTIMIZATION_EVALUATION.md`.

## Reinstalación y rotación

El conector `0.6.6` puede ejecutarse nuevamente desde su ruta instalada. En modo `experiment`, después de cada intercambio comprueba si cambió el bloque UTC de tres días; si cambió, alterna la asignación y aplica la configuración para el intercambio siguiente. El evento recién terminado conserva el flag de la configuración realmente utilizada. En `always_on` no realiza esa rotación.

El cambio se solicita íntegramente por chat. El modelo ejecuta `set-optimization-mode always-on` para dejar optimización permanente o `set-optimization-mode experiment` para volver al A/B, únicamente tras una solicitud explícita. El comando conserva empresa, correo, secreto y telemetría. Codex lo opera mediante el mismo conector que usa su hook `notify`; Claude Code mediante el que usa su hook `Stop`. Los hooks son procesos locales determinísticos posteriores al intercambio: no son un cron, no abren otra conversación y no llaman al modelo.

También comprueba, como máximo una vez cada 24 horas de uso, si el manifiesto oficial firmado anuncia una versión superior. Verifica la firma antes de confiar en versión, URLs o hashes. Esta consulta no llama al modelo, no envía telemetría adicional y no instala nada; agrega una indicación al bloque persistente administrado una sola vez por versión. Al comenzar la siguiente tarea o sesión, el modelo informa la actualización en el chat y pide autorización. Sólo si el usuario acepta usa `pragm-ai-updater` en Codex o el subcomando `update` en Claude Code; el actualizador vuelve a verificar la firma, descarga artefactos inmutables de esa versión y comprueba cada SHA-256 antes de reemplazar nada. Al finalizar elimina el aviso y continúa el pedido original. El actualizador conserva empresa, correo autorizado, secreto, modo, configuración base y clientes instalados. Si PragmAI rota el secreto de la empresa, Mauro genera y entrega un nuevo prompt privado personalizado; el empleado no vuelve a escribir el código.

La clave puede existir en el prompt privado personalizado que Mauro entrega fuera de Git, y transitar por el contexto del modelo y la entrada estándar del instalador durante el alta o la rotación. Nunca incluirla en el README canónico, telemetría, respuestas o archivos auxiliares. El conector sólo la persiste en su configuración privada.

## Límite de seguridad

La instalación inicial fija por un canal privado la versión inmutable y los hashes tanto de esta guía como del conector, y debe verificarlos antes de leer o ejecutar cualquiera. Después de instalar `0.6.4`, cada actualización exige además un manifiesto firmado por la clave pública incorporada y los hashes de sus tres activos. Un atacante que controle Vercel puede impedir una descarga, pero no producir una actualización aceptada sin la clave privada de release. Los permisos locales reducen cambios accidentales; una persona o malware con control de la cuenta o privilegios de administrador todavía puede sustituir programas locales. El backend limita por separado el daño de una credencial filtrada al vincular cada secreto con una empresa y rechazar campos fuera del esquema.
