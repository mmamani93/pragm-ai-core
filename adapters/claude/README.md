# Adaptador de Claude Code

Claude Code usa el conector compartido `adapters/pragm_ai_connector.py`. La instalación agrega un hook `Stop` que procesa localmente el último intercambio humano y envía un único evento técnico agregado.

Esta integración cubre Claude Code, incluso cuando se ejecuta dentro de Warp. No cubre claude.ai web.

## Alta

1. Instalar el ejecutable oficial para la plataforma.
2. Ejecutar `pragmai setup`.
3. Confirmar que detectó Claude Code y, si también existe Codex, elegir Claude Code o ambos. Si no detecta ningún cliente compatible, termina sin cambios.
4. Autorizar explícitamente la telemetría sin contenido y el correo normalizado que identificará al empleado.
5. Obtener un código público temporal y confirmarlo desde el enlace de invitación de un solo uso que Mauro compartió por un canal de confianza.
6. Permitir que el ejecutable respalde la configuración, instale el hook `Stop` y agregue el bloque administrado a `~/.claude/CLAUDE.md`.
7. Ejecutar `pragmai doctor`, reiniciar Claude Code y completar la validación.

La credencial individual se entrega directamente al ejecutable y no aparece en el chat, el enlace, el código público ni los argumentos. El asistente del empleado no consulta Supabase ni interpreta métricas empresariales.

## Captura y privacidad

El hook lee el transcript técnico que Claude Code ya mantiene, identifica el último intercambio iniciado por una persona, agrega sus llamadas y descarta contenido antes del envío. No invoca al modelo ni crea un historial, CSV o cola local.

Cuando Claude Code los expone, se envían:

- tokens agregados de entrada, salida, caché y razonamiento;
- llamadas internas, máximo de entrada y llamadas sobre el umbral;
- duración y mediciones canónicas de compactación;
- familias cerradas de herramientas y tamaño agregado de resultados;
- cliente, modelo, esfuerzo, perfil y categorías cerradas de trabajo;
- versión del conector, telemetría y estado de configuración;
- estado ON/OFF e identidad HMAC experimental sólo en `experiment`;
- huella HMAC privada de recurrencia.

Claude Code no expone una unidad de créditos de suscripción equivalente a la publicada para Codex. Por eso `credits_used` queda sin cobertura para Claude en vez de inferirse desde tokens; el equivalente API sí se calcula con la tarifa pública vigente. Cuando la telemetría distingue escritura de caché de una hora, se conserva ese volumen para aplicar su tarifa específica.

Se descartan obligatoriamente prompts, respuestas, transcripciones, identificadores de sesión, nombres y argumentos de herramientas, comandos, archivos, rutas, URLs, resultados y cualquier texto libre fuera del esquema. Los campos ausentes quedan sin dato; no se inventan ni se completan con otra llamada al modelo.

## Optimización y compactación

Modos:

- `experiment`: alterna ON/OFF en bloques UTC de tres días;
- `always_on`: mantiene ON y queda fuera del A/B.

En ON, el conector agrega instrucciones persistentes para un checkpoint objetivo de hasta 10.000 tokens y configura `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=64` sobre una referencia de 200.000 tokens. En OFF restaura el valor previo y retira sólo las reglas de optimización.

Claude Code no ofrece el alcance explícito `body_after_prefix` de Codex y algunas versiones pueden ignorar el override. La configuración es tentativa hasta observar una compactación y continuidad en la computadora real. Un marcador no implica una medición completa ni ahorro de créditos.

Cambiar el modo requiere una solicitud explícita del usuario. El hook puede preparar el bloque siguiente después de un intercambio, pero registra el estado realmente utilizado. No es un cron ni una llamada adicional al modelo.

La reproducción longitudinal v5 y la sensibilidad v6 son específicas de Codex. Claude conserva únicamente las mediciones de compactación que su telemetría permite observar.

## Validación

Después de reiniciar Claude Code:

1. ejecutar `pragmai doctor`;
2. completar un único intercambio humano;
3. confirmar una fila bajo empresa y correo correctos;
4. verificar versión, telemetría, configuración, llamadas, familias y `tool_result_characters`;
5. exigir asignación completa en `experiment`; en `always_on`, exigir ON y ausencia de identificadores experimentales;
6. confirmar que no exista contenido sensible;
7. validar captura y compactación por separado.

No declarar activa la integración hasta realizar esta prueba en el entorno real. Las estimaciones económicas se calculan en el servidor y no son cargos oficiales de Claude Code. La ausencia de créditos de suscripción es una limitación de cobertura, no consumo cero.

## Actualización y recuperación

Como máximo una vez cada 24 horas de uso, el conector puede comprobar un manifiesto oficial sin llamar al modelo ni enviar telemetría adicional. Verifica la firma antes de confiar en versión, ubicaciones o hashes y sólo instala después de autorización explícita.

El actualizador conserva empresa, correo, credencial, modo, hooks y configuración base. Rechaza modificaciones, downgrades y activos que no coincidan con el manifiesto firmado.

Si una instalación se revoca o compromete, Mauro crea una invitación nueva y el empleado repite `pragmai setup`. No se recuperan ni redistribuyen credenciales anteriores. `pragmai uninstall` retira sólo cambios administrados, restaura hooks previos y conserva respaldos recuperables.

## Límite de seguridad

La firma y los hashes protegen la cadena de publicación, pero un compromiso del alojamiento puede impedir descargas y una persona o malware con control administrativo del equipo todavía puede alterar programas o configuración local. Esos riesgos requieren controles del dispositivo y no pueden resolverse sólo desde el conector.
