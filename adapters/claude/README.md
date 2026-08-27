# Conector de Claude Code

Claude Code se integra mediante el mismo conector de PragmAI utilizado para Codex: `adapters/pragm_ai_connector.py`. La instalación agrega un hook `Stop`, que procesa localmente el transcript técnico disponible al finalizar una respuesta y envía un único evento agregado por intercambio iniciado por el usuario.

## Índice

- [Alta de un empleado](#alta-de-un-empleado)
- [Captura](#captura)
- [Compactación](#compactación)
- [Datos permitidos](#datos-permitidos)
- [Filtro obligatorio](#filtro-obligatorio)
- [Validación](#validación)
- [Actualización](#actualización)
- [Límites de seguridad](#límites-de-seguridad)

## Alta de un empleado

1. PragmAI entrega un `INSTALL_PROMPT` privado con versión inmutable y SHA-256 separados para `INITIAL_OPTIMIZATION.md` y el conector.
2. Claude descarga ambos archivos, verifica los dos hashes antes de leer o ejecutar, y luego solicita autorización expresa para la telemetría sin contenido y el correo permitido.
3. Claude solicita el correo autorizado y el consentimiento, toma del prompt privado el código de instalación ya incorporado y pasa esos valores al instalador junto con el `company_id` asignado.
4. El instalador guarda sólo configuración y secreto en el equipo, instala el hook y preserva los hooks existentes.
5. Se completa un intercambio de prueba y se comprueba en PragmAI que llegó un único evento sin contenido sensible.

El asistente del empleado no consulta Supabase ni evalúa consumo o comportamiento empresarial. Mauro realiza el análisis central y las optimizaciones desde su Codex.

## Captura

El hook `Stop` lee el último intercambio humano del transcript que Claude Code ya mantiene, agrega sus llamadas y descarta contenido antes del envío. No crea un historial local ni invoca nuevamente al modelo. Esta integración no cubre claude.ai web.

## Compactación

El conector `0.7.3` puede usar `experiment` o `always_on`. En el experimento, ON agrega instrucciones persistentes de checkpoint de hasta 10.000 tokens y configura `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` en 64 % sobre una ventana de referencia de 200.000 tokens; OFF restaura el valor previo y omite las reglas de optimización. `always_on` mantiene permanentemente la configuración ON y queda fuera del A/B. La instalación usa el Python activo y funciona en Windows, macOS y Linux, también cuando Claude Code se ejecuta dentro de Warp.

El usuario cambia el modo pidiéndoselo al modelo en el chat. Tras una solicitud explícita, el modelo ejecuta `set-optimization-mode always-on` o `set-optimization-mode experiment` sobre el conector instalado. El hook `Stop` sigue ejecutándose al finalizar cada intercambio para enviar telemetría y buscar actualizaciones; sólo en modo experimental rota la configuración cuando cambia el bloque UTC de tres días. No es un cron ni una llamada adicional al modelo.

Claude Code no ofrece el mismo alcance explícito `body_after_prefix` de Codex y algunas versiones pueden ignorar el override. Tratar la configuración como tentativa hasta observar `compact_boundary` en la computadora real.

Telemetría v4 usa `compact_boundary` para medir, cuando haya datos suficientes, contexto previo, llamadas posteriores, input posterior y tokens evitados estimados. Un marcador observado no implica automáticamente que exista una medición completa ni que la compactación haya ahorrado créditos.

## Datos permitidos

Cuando Claude Code los expone, el conector reduce y envía:

- tokens de entrada, salida, caché y razonamiento;
- llamadas internas, máximos y llamadas que superan el umbral; los promedios se derivan centralmente;
- duración y una estructura canónica por compactación observada;
- mediciones por compactación, de las que se derivan llamadas posteriores, tokens evitados y economía estimada;
- categorías cerradas de herramientas, incluida la subdivisión local de shell, nunca nombres ni argumentos;
- tamaño agregado de resultados devueltos al contexto, nunca su contenido;
- modelo, perfil y clasificación cerrada de la tarea;
- versión del conector y coincidencia de la configuración gestionada;
- `experiment_id`, flag ON/OFF e identificador HMAC del bloque-usuario;
- una huella HMAC privada para reconocer recurrencia sin enviar el texto.

Los campos no disponibles quedan sin dato. No se agregan datos inventados ni se hace otra llamada al modelo.

## Filtro obligatorio

Antes del envío se descartan:

- prompts y respuestas;
- identificadores de sesión;
- nombres y argumentos de herramientas;
- comandos, archivos, rutas y URLs;
- texto libre y atributos que no figuren en el esquema de `POST /api/events`.

La única identidad personal admitida es el correo que el propio empleado autoriza durante el alta. No se crea un CSV, una cola ni un historial local de telemetría.

## Validación

Una instalación queda aprobada sólo después de reiniciar Claude Code, completar un intercambio humano y confirmar una única fila sin contenido bajo empresa y correo correctos. La captura y la compactación son validaciones separadas: una compactación requiere suficiente contexto para poder observarse.

Confirmar además `telemetry_version=5`, `connector_version=0.7.3`, el estado de configuración, los conteos por familia y `tool_result_characters`. Exigir asignación completa en `experiment`; en `always_on`, confirmar `optimization_enabled=true` y ausencia de identificadores experimentales. La reproducción longitudinal v5 es específica de Codex; Claude conserva las mediciones por compactación disponibles. Las estimaciones económicas se calculan en el servidor y no se aceptan como cargos oficiales informados por Claude Code.

## Actualización

Después de un evento, el conector rota la asignación si cambió el bloque UTC de tres días y comprueba como máximo una vez cada 24 horas de uso si existe una versión superior, sin llamar al modelo ni enviar telemetría adicional. Para una actualización agrega una indicación a su bloque administrado de `CLAUDE.md`; al iniciar la siguiente tarea, Claude informa la novedad en el chat y pide autorización. Si el usuario acepta, el asistente ejecuta el subcomando `update` con el mismo Python y la ruta que imprimió el instalador. Si Codex también está instalado puede usar `pragm-ai-updater`. Desde `0.6.4` se exige una firma válida del manifiesto mediante la clave pública incorporada, el origen HTTPS oficial exacto, rutas inmutables de la versión y SHA-256 de los tres activos; se rechazan modificaciones, downgrades y rutas alternativas, y se preservan empresa, correo, secreto, hooks, línea base y configuración gestionada. Una instalación anterior a `0.6.4` necesita una transición confiable única para incorporar la verificación de firmas.

## Límites de seguridad

La instalación inicial fija por el prompt privado la versión inmutable y los hashes de la guía y el conector. Las actualizaciones posteriores a `0.6.4` requieren además un manifiesto firmado fuera de Vercel y verifican los tres activos. No se ejecuta código descargado desde `latest` ni mediante `curl | sh`. Un compromiso del alojamiento puede impedir descargas, pero no fabricar una actualización aceptada sin la clave privada de firma; un administrador del equipo todavía puede modificar código, configuración o hooks locales, riesgo que requiere controles del dispositivo.
