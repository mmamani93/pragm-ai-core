#!/usr/bin/env python3
"""PragmAI privacy-safe direct connector for Codex and Claude Code."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

VERSION = "0.6.6"
TELEMETRY_VERSION = 4
EXPERIMENT_ID = "optimization_3day_crossover_v1"
EXPERIMENT_BLOCK_SECONDS = 3 * 24 * 60 * 60
OPTIMIZATION_MODES = {"experiment", "always_on"}
DEFAULT_ENDPOINT = "https://m-pragm-ai.vercel.app/api/events"
DEFAULT_UPDATE_MANIFEST = "https://m-pragm-ai.vercel.app/pragm-ai-update.json"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
RELEASE_SIGNATURE_ALGORITHM = "rsa-pkcs1v15-sha256"
RELEASE_SIGNING_KEY_ID = "5627b3c1dd7b622a"
RELEASE_PUBLIC_EXPONENT = 65537
RELEASE_PUBLIC_MODULUS = int(
    "BECD72A1BC302803C12D5B6F7164F95C2472BBE9AA481576429C833353E35AFFF3A9E3BC6F2EA10CD2563C36"
    "FFC742B1749E75B0C399E9D0B5BAEE3CF8DFD3553D3973E8D01FE2D3F108BA008C91A2042C7A55E916466363"
    "567AE7EC23712E4BCCA8CE19EEBABAF8CB69B3656A675ED927ADC5E7D1FC1989DB02CB11DC716867EFFB1978E8"
    "FE88D8ED1A1E7482BA7C8C3FFB26F69F4FB3B7AC39427C2C7D9BAB9FC9204D6B9D4C8D089B9B2BA024118433"
    "EAB96A1C5E29FAD83E44DB45F2F73BED006F4BBDDC32757E04B4F9C51E2EDE76F2FF6FB8BC092B6A42B3D50F"
    "BAD106C86C3F2FD665117C24D5B3ECC58E043FC80F21792D2ED8A9EDEF385FDCCB0082E5ECD0C20BA0D9A864"
    "E970CEA837A78D646A832B153D5F2161586C43E6A1238E88FE49274CA0E87DA739DB9EC93159D9D91229408286"
    "BFB6E9D9366CC6CD062407B18CBB756C34DDC387B4C13CEC1028AE9E841181F735C0B1C345B31C020066D4BB46"
    "29780535B75249159ECD1F299A4C68422FC41E0ABA76F636C92E19FD4D",
    16,
)
SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
def platform_data_dir(platform_name: str | None = None) -> Path:
    if (platform_name or os.name) == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        return (Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local") / "PragmAI"
    return Path.home() / ".local" / "share" / "pragm-ai"


CONFIG_DIR = platform_data_dir() if os.name == "nt" else Path.home() / ".config" / "pragm-ai"
CONFIG_FILE = CONFIG_DIR / "config.json"
INSTALL_DIR = platform_data_dir()
STANDALONE = bool(getattr(sys, "frozen", False))
INSTALL_FILE = INSTALL_DIR / (
    ("pragmai.exe" if os.name == "nt" else "pragmai") if STANDALONE else "pragm_ai_connector.py"
)
UPDATER_SKILL_DIR = Path.home() / ".codex" / "skills" / "pragm-ai-updater"
PACKAGED_SKILL_DIR = Path(__file__).resolve().parent / "skills" / "pragm-ai-updater"
COMPACTION_POLICY = {
    "profile": "smart_100k",
    "checkpoint_target_tokens": 10_000,
    "effective_total_target_tokens": 127_000,
    "telemetry_scope": "total",
    "codex_growth_threshold_tokens": 100_000,
    "codex_scope": "body_after_prefix",
    "claude_reference_context_tokens": 200_000,
}
COMPACTION_POLICY["claude_trigger_percent"] = round(
    100
    * COMPACTION_POLICY["effective_total_target_tokens"]
    / COMPACTION_POLICY["claude_reference_context_tokens"]
)
CONFIG_PROFILE = COMPACTION_POLICY["profile"]
INTERNAL_MODELS = {"codex-auto-review"}

COMPACT_PROMPT = """Create a dense, accurate continuation checkpoint for this task. Preserve everything needed to continue correctly, while removing conversational bulk.

Always preserve:
- The user's current objective, exact requirements, priorities, constraints, and explicit preferences.
- Applicable instructions and project-specific rules that remain relevant.
- Verified facts, exact numbers, dates, source links, file paths, identifiers, and explicit uncertainty.
- Decisions already made, completed work, material changes, validation, tests, approvals, and current operational state.
- Corrections to earlier statements, open questions, blockers, unresolved risks, and concrete next actions.
- Tool results as concise conclusions with evidence pointers; retain raw output only when exact data is necessary.

Discard greetings, repetition, superseded plans, resolved detours, and verbose output that no longer affects the task. Do not invent facts or hide uncertainty. Use compact structured Markdown. Aim for no more than 10,000 tokens, but never omit critical context merely to meet that target."""

CLAUDE_COMPACT_BLOCK_START = "<!-- PRAGMAI_COMPACTION_START -->"
CLAUDE_COMPACT_BLOCK_END = "<!-- PRAGMAI_COMPACTION_END -->"
CODEX_RULES_BLOCK_START = "<!-- PRAGMAI_RULES_START -->"
CODEX_RULES_BLOCK_END = "<!-- PRAGMAI_RULES_END -->"
PRAGMAI_CORE_RULES = """## PragmAI managed instructions

- Never include prompts, responses, commands, arguments, file names, paths, URLs, transcripts, session identifiers or individual tool names in PragmAI telemetry.
- Never expose the private PragmAI configuration. A private personalized installation prompt may contain the company installation code; pass it directly to the installer, never ask the employee to retype it, never repeat it in the response, and never include it in telemetry, versioned documentation or auxiliary files.
- The employee assistant must not query Supabase or interpret company analytics; Mauro performs that analysis centrally.
- Checking for a PragmAI update is read-only. Install an update only after the user explicitly requests it.
- Preserve existing user and project instructions; more specific instructions continue to apply."""

PRAGMAI_OPTIMIZATION_RULES = """### PragmAI optimization instructions

- Keep responses concise unless the user asks for more detail.
- Accuracy takes priority over token savings. Verify consequential or unstable claims with authoritative sources when necessary.
- Perform deterministic extraction, filtering, sorting, calculations, conversions, reconciliation and bulk validation locally and in bounded batches when this preserves accuracy.
- Read large files or datasets once per version and reuse compact deterministic results instead of repeatedly sending bulky raw data to the model.
- Minimize model round trips when the next operations do not require semantic judgment."""


def managed_instructions(optimization_enabled: bool, target_version: str | None = None) -> str:
    rules = PRAGMAI_CORE_RULES
    if optimization_enabled:
        rules = f"{rules}\n\n{PRAGMAI_OPTIMIZATION_RULES}"
    if not target_version:
        return rules
    version_tuple(target_version)
    return f"""{rules}

### PragmAI update available

- PragmAI {target_version} is available. At the beginning of this task, tell the user in chat that an update exists and ask whether they authorize installing it.
- Do not install it, interrupt unrelated work, or treat this notice as authorization until the user explicitly agrees.
- If authorized, use the installed PragmAI updater. Preserve the company, authorized employee, secret and existing client configuration; never request or expose the secret in chat.
- After the updater succeeds, continue the user's original task. The updater will remove this notice when it reapplies the managed instructions."""


def codex_rules_block(optimization_enabled: bool = True, target_version: str | None = None) -> str:
    return f"""{CODEX_RULES_BLOCK_START}
{managed_instructions(optimization_enabled, target_version)}
{CODEX_RULES_BLOCK_END}"""


def claude_compact_block(optimization_enabled: bool = True, target_version: str | None = None) -> str:
    compact_rules = f"""

### PragmAI compact instructions

{COMPACT_PROMPT}""" if optimization_enabled else ""
    return f"""{CLAUDE_COMPACT_BLOCK_START}
{managed_instructions(optimization_enabled, target_version)}{compact_rules}
{CLAUDE_COMPACT_BLOCK_END}"""


CODEX_RULES_BLOCK = codex_rules_block()
CLAUDE_COMPACT_BLOCK = claude_compact_block()

COMPANY_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.I)


def current_artifact_path() -> Path:
    """Return the executable in a frozen build and the source file otherwise."""
    return Path(sys.executable if STANDALONE else __file__).resolve()


def installed_command(command: str) -> list[str]:
    """Build a hook command that does not require Python for standalone releases."""
    if STANDALONE:
        return [str(INSTALL_FILE), command]
    return [sys.executable, str(INSTALL_FILE), command]


def is_pragmai_command(value, command: str) -> bool:
    """Recognize current and legacy PragmAI hook commands without executing them."""
    serialized = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return command in serialized and (
        str(INSTALL_FILE) in serialized
        or "pragm_ai_connector.py" in serialized
        or re.search(r"(?:^|[\\/\s\"'])pragmai(?:\.exe)?(?:[\s\"']|$)", serialized) is not None
    )

EMBEDDED_UPDATER_SKILL = b'''---
name: pragm-ai-updater
description: Update, repair, check, or change the optimization mode of an installed PragmAI connector when the user explicitly asks. Preserve the existing company identity, authorized employee, secret, and client configuration.
---

# PragmAI updater

Use the installed connector as the only update entrypoint. Run it with the same Python interpreter used during installation. On macOS and Linux the usual command is `python3`; on Windows it is commonly `py -3` or `python`.

To check the official manifest without installing anything, run the installed connector with:

```sh
<python> <installed-connector-path> check-update
```

To install an available update, run:

```sh
<python> <installed-connector-path> update
```

To leave the A/B experiment and keep optimization enabled all the time, run:

```sh
<python> <installed-connector-path> set-optimization-mode always-on
```

To participate again in the three-day crossover A/B experiment, run:

```sh
<python> <installed-connector-path> set-optimization-mode experiment
```

Run `update` only after the user explicitly asks to install or repair PragmAI, or explicitly authorizes it in response to the managed chat notice. The notice itself and a request to check do not authorize installation. Use `check-update` to compare against the official release; use `--version` only when the user asks for the locally installed version.

Change the optimization mode only after an explicit request from the user. `always-on` keeps telemetry active, applies the optimized managed configuration immediately and omits experiment identifiers from later events. `experiment` immediately applies the current deterministic assignment and alternates ON/OFF every three UTC days; later changes are performed by the existing Codex notification hook or Claude Code Stop hook after an exchange. Neither command needs the email or installation code again.

The installer prints the exact connector path. Do not guess it or inspect the private configuration to find it. The updater accepts only the exact official HTTPS origin, requires a release manifest signed by the embedded PragmAI public key, verifies semantic version and every asset SHA-256, rejects unsigned or modified manifests and downgrades, replaces the connector atomically, keeps the existing company identity, authorized employee, secret and installed clients, reapplies only the managed Codex or Claude Code settings, and updates this skill. It does not update silently. Do not read, display, copy, or transmit the private PragmAI configuration file.

For a check, report whether an update exists and do not install it. For an authorized update, report the previous and installed connector versions from the command output, then continue the user's original task. If the installed connector does not support these subcommands, explain that this is a legacy installation and use the latest private installation prompt supplied by the PragmAI administrator once; subsequent updates can use this skill.
'''

def install_privacy_notice(mode: str) -> str:
    mode_notice = (
        "Ese empleado alternará de forma seudónima entre optimización ON y OFF en bloques de tres días UTC; "
        "el evento informará la asignación y si la configuración coincidió."
        if mode == "experiment"
        else "La optimización permanecerá activada y esta instalación no participará del experimento ON/OFF."
    )
    return f"""PragmAI enviará únicamente métricas técnicas agregadas y categorías cerradas.
No enviará prompts, respuestas, comandos, argumentos, archivos, rutas, URLs ni transcripciones.
El correo autorizado se guardará como identificador del empleado dentro de la empresa configurada.
{mode_notice}"""


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(mode)
    temporary.replace(path)


def atomic_write_bytes(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    temporary.chmod(mode)
    temporary.replace(path)


def load_config(path: Path | None = None) -> dict:
    path = path or CONFIG_FILE
    if not path.exists():
        raise RuntimeError("PragmAI is not configured. Run the installer first.")
    config = json.loads(path.read_text(encoding="utf-8"))
    required = ("endpoint", "ingest_secret", "company_id", "employee_id", "fingerprint_key")
    if any(not config.get(key) for key in required):
        raise RuntimeError("PragmAI configuration is incomplete.")
    return config


def normalize_task_shape(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    normalized = re.sub(r"https?://\S+|www\.\S+", " <url> ", normalized)
    normalized = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", " <email> ", normalized)
    normalized = re.sub(r"(?:^|\s)(?:[/~]|[a-z]:[\\/])\S+", " <path> ", normalized)
    normalized = re.sub(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", " <id> ", normalized)
    normalized = re.sub(r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b", " <date> ", normalized)
    normalized = re.sub(r"\b\d+(?:[.,]\d+)?\b", " <number> ", normalized)
    return " ".join(re.findall(r"[a-z]+|<[a-z]+>", normalized)[:60])


def private_digest(prefix: str, value: str, key_hex: str, length: int = 32) -> str:
    digest = hmac.new(bytes.fromhex(key_hex), value.encode("utf-8"), hashlib.sha256).hexdigest()[:length]
    return prefix + digest


def recurrence_key(text: str, key_hex: str) -> str | None:
    shape = normalize_task_shape(text)
    return private_digest("rt_", shape, key_hex) if shape else None


def experiment_assignment(config: dict, moment: datetime | None = None) -> dict:
    """Return a private assignment that alternates ON/OFF every three UTC days."""
    current = (moment or datetime.now(timezone.utc)).astimezone(timezone.utc)
    block = int(current.timestamp()) // EXPERIMENT_BLOCK_SECONDS
    period = f"B{block}"
    participant = f"{EXPERIMENT_ID}:{config['company_id']}:{config['employee_id']}"
    digest = hmac.new(
        bytes.fromhex(config["fingerprint_key"]), participant.encode("utf-8"), hashlib.sha256
    ).digest()
    unit_digest = hmac.new(
        bytes.fromhex(config["fingerprint_key"]), f"{participant}:{period}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return {
        "experiment_id": EXPERIMENT_ID,
        "experiment_unit_id": "eu_" + unit_digest[:32],
        "experiment_period": period,
        "optimization_enabled": bool((digest[0] & 1) ^ (block & 1)),
    }


def weekly_experiment_assignment(config: dict, moment: datetime | None = None) -> dict:
    """Backward-compatible alias retained for integrations using the old helper name."""
    return experiment_assignment(config, moment)


def optimization_mode(config: dict) -> str:
    mode = config.get("optimization_mode", "experiment")
    return mode if mode in OPTIMIZATION_MODES else "experiment"


def active_optimization_state(config: dict) -> dict:
    if optimization_mode(config) == "always_on":
        return {"optimization_enabled": True}
    experiment = config.get("active_experiment")
    if (
        not isinstance(experiment, dict)
        or experiment.get("experiment_id") != EXPERIMENT_ID
        or not re.fullmatch(r"eu_[a-f0-9]{32}", str(experiment.get("experiment_unit_id", "")))
        or not isinstance(experiment.get("optimization_enabled"), bool)
    ):
        experiment = experiment_assignment(config)
    return {
        "experiment_id": experiment.get("experiment_id", EXPERIMENT_ID),
        "experiment_unit_id": experiment.get("experiment_unit_id"),
        "optimization_enabled": bool(experiment.get("optimization_enabled")),
    }


def active_experiment(config: dict) -> dict:
    """Backward-compatible alias for callers using the 0.6.1 helper name."""
    return active_optimization_state(config)


def text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") in {"text", "input_text"}:
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return ""


def classify(text: str, tool_categories: list[str]) -> dict:
    lowered = (text or "").lower()
    rules = [
        (r"\b(excel|xlsx|planilla|spreadsheet|sheets?)\b", "data", "analyze", "spreadsheet_analysis"),
        (r"\b(document|documento|docx|word|pdf|contrato|informe)\b", "documents", "edit", "document_drafting"),
        (r"\b(research|investig|busc|fuentes?|web)\w*", "research", "research", "web_research"),
        (r"\b(code|codigo|program|repo|api|bug|test|deploy|configur)\w*", "software", "edit", "code_change"),
        (r"\b(email|correo|mensaje|comunic)\w*", "communications", "communicate", "email_drafting"),
        (r"\b(presentacion|presentation|slides?|pptx)\b", "documents", "create", "presentation_creation"),
        (r"\b(imagen|image|video|logo|dise[nñ])\w*", "creative", "create", "image_video_creation"),
        (r"\b(error|falla|problema|troubleshoot|diagnost)\w*", "operations", "troubleshoot", "troubleshooting"),
        (r"\b(plan|estrateg|roadmap)\w*", "operations", "plan", "planning"),
    ]
    domain, task_type, workflow = "other", "other", "general_assistance"
    for pattern, matched_domain, matched_type, matched_workflow in rules:
        if re.search(pattern, lowered):
            domain = matched_domain
            task_type = matched_type
            workflow = matched_workflow
            break
    return {
        "work_domain": domain,
        "task_type": task_type,
        "workflow_pattern": workflow,
        "classification_version": "connector-v1",
    }


def serialized_arguments(arguments) -> str:
    if isinstance(arguments, str):
        return arguments
    if arguments is None:
        return ""
    try:
        return json.dumps(arguments, separators=(",", ":"))
    except (TypeError, ValueError):
        return ""


def shell_category(arguments=None) -> str:
    """Classify a shell invocation transiently without retaining its command."""
    text = serialized_arguments(arguments).lower()
    rules = [
        (r"\b(pytest|unittest|node\s+--test|npm\s+(run\s+)?test|pnpm\s+(run\s+)?test|yarn\s+test|cargo\s+test|go\s+test|git\s+diff\s+--check|py_compile|tsc\b|eslint\b|mypy\b)", "shell_testing"),
        (r"\b(vercel|netlify|docker\s+(build|push)|terraform\s+(apply|plan)|npm\s+run\s+build|pnpm\s+(run\s+)?build|yarn\s+build|cargo\s+build)\b", "shell_build_deploy"),
        (r"\b(git|gh)\b", "shell_version_control"),
        (r"\b(psql|sqlite3|supabase|mysql|mongosh)\b", "shell_database"),
        (r"\b(npm|pnpm|yarn|pip|pip3|uv|poetry|bundle|gem|brew|apt|apt-get|dnf|yum|choco|winget)\s+(install|add|remove|update|upgrade|sync)\b", "shell_dependency_management"),
        (r"\b(jq|awk|sort|uniq|cut|tr|xargs|csvkit|mlr)\b", "shell_data_processing"),
        (r"\b(rg|grep|sed|head|tail|find|ls|pwd|wc|cat|stat|file|which)\b", "shell_file_inspection"),
    ]
    for pattern, category in rules:
        if re.search(pattern, text):
            return category
    return "shell_general"


def tool_category(name: str, arguments=None) -> str:
    lowered = (name or "").lower()
    if any(value in lowered for value in ("search", "web", "fetch")):
        return "web"
    if any(value in lowered for value in ("browser", "playwright", "screenshot")):
        return "browser"
    if any(value in lowered for value in ("sql", "supabase", "database", "postgres")):
        return "database"
    if any(value in lowered for value in ("imagegen", "image_gen", "generate_image", "video", "audio")):
        return "image_generation"
    if any(value in lowered for value in ("docx", "pdf", "spreadsheet", "slides", "excel")):
        return "office_documents"
    if any(value in lowered for value in ("apply_patch", "write", "edit", "delete", "move")):
        return "filesystem_write"
    if any(value in lowered for value in ("read", "list", "find", "glob", "view")):
        return "filesystem_read"
    if any(value in lowered for value in ("exec", "shell", "command", "bash", "terminal")):
        return shell_category(arguments)
    if any(value in lowered for value in ("mcp", "app", "connector")):
        return "external_app"
    return "other"


def categorized_tool_calls(name: str, arguments=None) -> list[str]:
    """Resolve programmatic orchestration without retaining tool arguments."""
    lowered = (name or "").lower()
    if lowered not in {"functions.exec", "function.exec", "exec"}:
        return [tool_category(name, arguments)]
    serialized = serialized_arguments(arguments)
    nested = re.findall(r"\btools\.([A-Za-z0-9_]+)\s*\(", serialized)
    return [tool_category(value, serialized) for value in nested] or [shell_category(serialized)]


def aggregate_character_count(value) -> int:
    """Count returned characters without retaining or emitting their content."""
    if isinstance(value, str):
        return len(value)
    if isinstance(value, list):
        return sum(aggregate_character_count(item) for item in value)
    if isinstance(value, dict):
        return sum(aggregate_character_count(item) for item in value.values())
    return 0


def codex_usage(record: dict) -> dict | None:
    item = record.get("payload") or {}
    if record.get("type") != "event_msg" or item.get("type") != "token_count":
        return None
    return ((item.get("info") or {}).get("last_token_usage") or {})


def real_usage(usage: dict | None) -> bool:
    return bool(usage and any(integer(usage.get(key)) for key in ("input_tokens", "output_tokens")))


def is_compaction(record: dict) -> bool:
    item = record.get("payload") or {}
    return record.get("type") == "compacted" or (
        record.get("type") == "event_msg" and item.get("type") == "context_compacted"
    )


def compaction_markers(records: list[dict], start: int, end: int) -> list[int]:
    """Collapse duplicate compacted/context_compacted records for one operation."""
    markers = []
    since_marker_has_usage = True
    for index in range(max(0, start), min(len(records), end + 1)):
        usage = codex_usage(records[index])
        if real_usage(usage):
            since_marker_has_usage = True
        if not is_compaction(records[index]):
            continue
        if not markers or since_marker_has_usage:
            markers.append(index)
        since_marker_has_usage = False
    return markers


def compaction_measurements_for_codex(
    records: list[dict], turn_start: int, turn_end: int, window_start: int
) -> list[dict]:
    markers = compaction_markers(records, window_start, turn_end)
    measurements = []
    for position, marker in enumerate(markers, 1):
        next_marker = markers[position] if position < len(markers) else turn_end + 1
        pre_usage = None
        for index in range(marker - 1, -1, -1):
            candidate = codex_usage(records[index])
            if real_usage(candidate):
                pre_usage = candidate
                break
        compacted_context = None
        post_calls = []
        for index in range(marker + 1, min(next_marker, turn_end + 1)):
            candidate = codex_usage(records[index])
            if not candidate:
                continue
            if real_usage(candidate):
                if index >= turn_start:
                    post_calls.append(candidate)
            elif compacted_context is None and integer(candidate.get("total_tokens")):
                compacted_context = integer(candidate.get("total_tokens"))
        pre_input = integer((pre_usage or {}).get("input_tokens")) or None
        pre_cached = integer((pre_usage or {}).get("cached_input_tokens")) or None
        post_inputs = [integer(call.get("input_tokens")) for call in post_calls]
        first_post = post_inputs[0] if post_inputs else None
        saved_per_call = max((pre_input or 0) - (first_post or 0), 0)
        measurement = {
            "position": position,
            "before_exchange": marker < turn_start,
            "pre_input_tokens": pre_input,
            "pre_cached_tokens": min(pre_cached or 0, pre_input or 0) if pre_input else None,
            "compacted_context_tokens": compacted_context,
            "first_post_input_tokens": first_post,
            "model_calls_after": len(post_calls),
            "post_input_tokens": sum(post_inputs),
            "tokens_avoided_estimated": saved_per_call * len(post_calls),
            "measurement_basis": "codex_context_delta_v1" if pre_input and first_post else "unavailable",
        }
        measurements.append({key: value for key, value in measurement.items() if value is not None})
    return measurements


def codex_configuration_status(optimization_enabled: bool, config: dict) -> dict:
    try:
        text = (Path.home() / ".codex" / "config.toml").read_text(encoding="utf-8")
        threshold = top_level_json_value(text, "model_auto_compact_token_limit")
        scope = top_level_json_value(text, "model_auto_compact_token_limit_scope")
        compact_prompt = top_level_json_value(text, "compact_prompt")
        actual = {
            "model_auto_compact_token_limit": threshold,
            "model_auto_compact_token_limit_scope": scope,
            "compact_prompt": compact_prompt,
        }
        matched = actual == codex_optimization_values(config, optimization_enabled)
        return {
            "configured_compaction_threshold_tokens": integer(threshold),
            "config_status": "matched" if matched else "drift",
        }
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return {"config_status": "unavailable"}


def claude_configuration_status(optimization_enabled: bool, config: dict) -> dict:
    try:
        settings = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
        instructions = (Path.home() / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        configured_raw = (settings.get("env") or {}).get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
        configured = integer(configured_raw)
        expected = claude_optimization_values(config, optimization_enabled)
        matched = (
            configured_raw == expected.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
            and claude_compact_block(optimization_enabled) in instructions
        )
        return {
            "configured_compaction_threshold_tokens": (
                round(configured * COMPACTION_POLICY["claude_reference_context_tokens"] / 100)
                if configured else None
            ),
            "config_status": "matched" if matched else "drift",
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {"config_status": "unavailable"}


def integer(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def iso_duration_ms(first: str | None, last: str | None) -> int | None:
    try:
        start = datetime.fromisoformat(first.replace("Z", "+00:00"))
        end = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() * 1000))
    except (AttributeError, TypeError, ValueError):
        return None


def aggregate_usage(
    usages: list[dict],
    cache_write_in_input: bool = True,
    compaction_threshold: int | None = None,
) -> dict:
    compaction_threshold = compaction_threshold or COMPACTION_POLICY["codex_growth_threshold_tokens"]
    calls = []
    for usage in usages:
        fresh = integer(usage.get("input_tokens"))
        cached = integer(usage.get("cached_input_tokens", usage.get("cache_read_input_tokens")))
        written = integer(usage.get("cache_write_input_tokens", usage.get("cache_creation_input_tokens")))
        if cache_write_in_input:
            input_total = max(fresh, cached + written)
        else:
            input_total = fresh + cached + written
        output = integer(usage.get("output_tokens"))
        reasoning = integer(usage.get("reasoning_output_tokens"))
        total = integer(usage.get("total_tokens")) or input_total + output
        if input_total or output or total:
            calls.append({
                "input": input_total,
                "cached": cached,
                "written": written,
                "output": output,
                "reasoning": reasoning,
                "total": total,
            })
    inputs = [call["input"] for call in calls]
    return {
        "tokens_input": sum(inputs),
        "tokens_output": sum(call["output"] for call in calls),
        "tokens_cache_read": sum(call["cached"] for call in calls),
        "tokens_cache_write": sum(call["written"] for call in calls),
        "tokens_reasoning": sum(call["reasoning"] for call in calls),
        "model_calls": len(calls),
        "max_input_tokens_per_call": max(inputs, default=0),
        "calls_over_compaction_threshold": sum(call["total"] > compaction_threshold for call in calls),
        "cache_miss_calls": sum(call["input"] > 0 and call["cached"] == 0 for call in calls),
    }


def codex_session_file(thread_id: str, sessions_root: Path | None = None) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", thread_id or ""):
        raise RuntimeError("Invalid Codex thread identifier.")
    root = sessions_root or (Path.home() / ".codex" / "sessions")
    candidates = list(root.rglob(f"*{thread_id}*.jsonl"))
    if not candidates:
        raise RuntimeError("Codex session record was not found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def codex_event(payload: dict, config: dict, sessions_root: Path | None = None) -> dict | None:
    thread_id = str(payload.get("thread-id", ""))
    turn_id = str(payload.get("turn-id", ""))
    if not turn_id:
        return None
    path = codex_session_file(thread_id, sessions_root)
    records = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    turn_start = next((
        index for index, record in enumerate(records)
        if record.get("type") == "turn_context"
        and (record.get("payload") or {}).get("turn_id") == turn_id
    ), None)
    if turn_start is None:
        return None
    turn_end = next((
        index for index in range(turn_start + 1, len(records))
        if records[index].get("type") == "event_msg"
        and (records[index].get("payload") or {}).get("type") == "task_complete"
        and (records[index].get("payload") or {}).get("turn_id") == turn_id
    ), len(records) - 1)
    previous_complete = next((
        index for index in range(turn_start - 1, -1, -1)
        if records[index].get("type") == "event_msg"
        and (records[index].get("payload") or {}).get("type") == "task_complete"
    ), None)
    window_start = (previous_complete + 1) if previous_complete is not None else turn_start

    usages = []
    category_counts = Counter()
    tool_result_characters = 0
    post_tool_calls = continuation_calls = 0
    tool_since_usage = False
    previous_was_usage = False
    context = records[turn_start].get("payload") or {}
    model, effort = context.get("model"), context.get("effort")
    first_timestamp = records[turn_start].get("timestamp")
    last_timestamp = records[turn_end].get("timestamp") or first_timestamp
    for record in records[turn_start + 1:turn_end + 1]:
        record_type = record.get("type")
        item = record.get("payload") or {}
        if record_type == "response_item" and item.get("type") in {"function_call", "custom_tool_call"}:
            category_counts.update(categorized_tool_calls(str(item.get("name", "")), item.get("arguments")))
            tool_since_usage = True
            previous_was_usage = False
        elif record_type == "response_item" and item.get("type") in {"function_call_output", "custom_tool_call_output"}:
            tool_result_characters += aggregate_character_count(item.get("output"))
        else:
            usage = codex_usage(record)
            if real_usage(usage):
                usages.append(usage)
                if tool_since_usage:
                    post_tool_calls += 1
                elif previous_was_usage:
                    continuation_calls += 1
                tool_since_usage = False
                previous_was_usage = True

    compaction_measurements = compaction_measurements_for_codex(
        records, turn_start, turn_end, window_start
    )

    model = str(model or "unknown")[:100]
    if model.lower() in INTERNAL_MODELS or "auto-review" in model.lower() or not usages:
        return None
    input_text = "\n".join(str(value) for value in payload.get("input-messages", []) if isinstance(value, str))
    optimization = active_optimization_state(config)
    optimization_enabled = optimization["optimization_enabled"]
    configuration = codex_configuration_status(optimization_enabled, config)
    expected = codex_optimization_values(config, optimization_enabled)
    expected_scope = expected.get("model_auto_compact_token_limit_scope")
    event = {
        "event_id": private_digest("codex_", f"{thread_id}:{turn_id}", config["fingerprint_key"]),
        "occurred_at": last_timestamp or datetime.now(timezone.utc).isoformat(),
        "company_id": config["company_id"],
        "employee_id": config["employee_id"],
        "client": "codex",
        "model": model,
        "reasoning_effort": str(effort or "unknown")[:30],
        **classify(input_text, list(category_counts)),
        "duration_ms": iso_duration_ms(first_timestamp, last_timestamp),
        **aggregate_usage(
            usages,
            cache_write_in_input=True,
            compaction_threshold=COMPACTION_POLICY["effective_total_target_tokens"],
        ),
        "tool_category_counts": dict(sorted(category_counts.items())),
        "tool_result_characters": tool_result_characters,
        "post_tool_model_calls": post_tool_calls,
        "continuation_model_calls": continuation_calls,
        "compaction_measurements": compaction_measurements,
        "config_profile": CONFIG_PROFILE if optimization_enabled else "baseline",
        "compaction_threshold_tokens": (
            COMPACTION_POLICY["effective_total_target_tokens"]
            if optimization_enabled else expected.get("model_auto_compact_token_limit")
        ),
        "compaction_scope": expected_scope if expected_scope in {"total", "input", "body_after_prefix"} else "unavailable",
        "billing_mode": config.get("billing_mode", "subscription"),
        "connector_version": VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        **optimization,
        **configuration,
    }
    fingerprint = recurrence_key(input_text, config["fingerprint_key"])
    if fingerprint:
        event["recurrence_key"] = fingerprint
    return {key: value for key, value in event.items() if value is not None}


def claude_input_tokens(usage: dict) -> int:
    return sum(integer(usage.get(key)) for key in (
        "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"
    ))


def compaction_measurements_for_claude(records: list[dict]) -> list[dict]:
    markers = [
        index for index, record in enumerate(records)
        if record.get("type") == "system" and record.get("subtype") == "compact_boundary"
    ]
    measurements = []
    for position, marker in enumerate(markers, 1):
        next_marker = markers[position] if position < len(markers) else len(records)
        metadata = records[marker].get("compactMetadata") or {}
        pre_input = integer(metadata.get("preTokens")) or None
        pre_cached = None
        for index in range(marker - 1, -1, -1):
            message = records[index].get("message") or {}
            usage = message.get("usage") or {}
            if claude_input_tokens(usage):
                pre_cached = integer(usage.get("cache_read_input_tokens")) or None
                break
        post_usages = []
        for record in records[marker + 1:next_marker]:
            usage = (record.get("message") or {}).get("usage") or {}
            if claude_input_tokens(usage) or integer(usage.get("output_tokens")):
                post_usages.append(usage)
        post_inputs = [claude_input_tokens(usage) for usage in post_usages]
        first_post = post_inputs[0] if post_inputs else None
        saved_per_call = max((pre_input or 0) - (first_post or 0), 0)
        measurement = {
            "position": position,
            "before_exchange": False,
            "pre_input_tokens": pre_input,
            "pre_cached_tokens": min(pre_cached or 0, pre_input or 0) if pre_input else None,
            "compacted_context_tokens": first_post,
            "first_post_input_tokens": first_post,
            "model_calls_after": len(post_usages),
            "post_input_tokens": sum(post_inputs),
            "tokens_avoided_estimated": saved_per_call * len(post_usages),
            "measurement_basis": "claude_context_delta_v1" if pre_input and first_post else "unavailable",
        }
        measurements.append({key: value for key, value in measurement.items() if value is not None})
    return measurements


def claude_event(payload: dict, config: dict) -> dict | None:
    transcript = Path(str(payload.get("transcript_path", ""))).expanduser()
    if not transcript.is_file():
        return None
    records = []
    with transcript.open(encoding="utf-8") as handle:
        for raw in handle:
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    last_user = None
    for index, record in enumerate(records):
        if record.get("type") != "user":
            continue
        content = (record.get("message") or {}).get("content")
        if isinstance(content, list) and content and all(isinstance(item, dict) and item.get("type") == "tool_result" for item in content):
            continue
        if text_from_content(content).strip():
            last_user = index
    if last_user is None:
        return None
    user_record = records[last_user]
    user_text = text_from_content((user_record.get("message") or {}).get("content"))
    usages = []
    category_counts = Counter()
    tool_result_characters = 0
    post_tool_calls = continuation_calls = 0
    tool_since_usage = previous_was_usage = False
    model = "unknown"
    first_timestamp = user_record.get("timestamp")
    last_timestamp = first_timestamp
    exchange_records = records[last_user + 1:]
    for record in exchange_records:
        last_timestamp = record.get("timestamp") or last_timestamp
        if record.get("type") == "user":
            for item in (record.get("message") or {}).get("content") or []:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    tool_result_characters += aggregate_character_count(item.get("content"))
        if record.get("type") != "assistant":
            continue
        message = record.get("message") or {}
        model = str(message.get("model") or model)
        usage = message.get("usage") or {}
        if any(integer(usage.get(key)) for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")):
            usages.append(usage)
            if tool_since_usage:
                post_tool_calls += 1
            elif previous_was_usage:
                continuation_calls += 1
            tool_since_usage = False
            previous_was_usage = True
        for item in message.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                category_counts.update(categorized_tool_calls(str(item.get("name", "")), item.get("input")))
                tool_since_usage = True
                previous_was_usage = False
    if not usages:
        return None
    session_id = str(payload.get("session_id", "session"))
    exchange_marker = str(user_record.get("uuid") or first_timestamp or last_user)
    compaction_measurements = compaction_measurements_for_claude(exchange_records)
    optimization = active_optimization_state(config)
    optimization_enabled = optimization["optimization_enabled"]
    configuration = claude_configuration_status(optimization_enabled, config)
    event = {
        "event_id": private_digest("claude_", f"{session_id}:{exchange_marker}", config["fingerprint_key"]),
        "occurred_at": last_timestamp or datetime.now(timezone.utc).isoformat(),
        "company_id": config["company_id"],
        "employee_id": config["employee_id"],
        "client": "claude-code",
        "model": model[:100],
        "reasoning_effort": "unknown",
        **classify(user_text, list(category_counts)),
        "duration_ms": iso_duration_ms(first_timestamp, last_timestamp),
        **aggregate_usage(
            usages,
            cache_write_in_input=False,
            compaction_threshold=COMPACTION_POLICY["effective_total_target_tokens"],
        ),
        "tool_category_counts": dict(sorted(category_counts.items())),
        "tool_result_characters": tool_result_characters,
        "post_tool_model_calls": post_tool_calls,
        "continuation_model_calls": continuation_calls,
        "compaction_measurements": compaction_measurements,
        "config_profile": CONFIG_PROFILE if optimization_enabled else "baseline",
        "compaction_threshold_tokens": (
            COMPACTION_POLICY["effective_total_target_tokens"] if optimization_enabled else configuration.get("configured_compaction_threshold_tokens")
        ),
        "compaction_scope": "approximate_total" if optimization_enabled else "unavailable",
        "billing_mode": config.get("billing_mode", "subscription"),
        "connector_version": VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        **optimization,
        **configuration,
    }
    fingerprint = recurrence_key(user_text, config["fingerprint_key"])
    if fingerprint:
        event["recurrence_key"] = fingerprint
    return {key: value for key, value in event.items() if value is not None}


def send_event(event: dict, config: dict) -> None:
    data = json.dumps(event, separators=(",", ":")).encode("utf-8")
    request = Request(config["endpoint"], data=data, method="POST", headers={
        "Authorization": f"Bearer {config['ingest_secret']}",
        "Content-Type": "application/json",
        "User-Agent": f"PragmAI-Connector/{VERSION}",
    })
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in (200, 202):
                raise RuntimeError(f"PragmAI rejected the event ({response.status}).")
    except HTTPError as error:
        raise RuntimeError(f"PragmAI rejected the event ({error.code}).") from error
    except URLError as error:
        raise RuntimeError("PragmAI endpoint is unavailable.") from error


def run_chained_notify(payload_json: str, config: dict) -> None:
    command = config.get("chained_notify")
    if not isinstance(command, list) or not command:
        return
    try:
        subprocess.run([*command, payload_json], timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def codex_notify(payload_json: str) -> int:
    config = None
    try:
        config = load_config()
        payload = json.loads(payload_json)
        if payload.get("type") != "agent-turn-complete":
            return 0
        event = codex_event(payload, config)
        if event:
            send_event(event, config)
        periodic_experiment_check(config)
        periodic_update_check(config)
        return 0
    except Exception as error:
        print(f"PragmAI Codex connector: {error}", file=sys.stderr)
        return 1
    finally:
        if config:
            run_chained_notify(payload_json, config)


def claude_stop() -> int:
    try:
        config = load_config()
        payload = json.load(sys.stdin)
        if payload.get("stop_hook_active"):
            return 0
        event = claude_event(payload, config)
        if event:
            send_event(event, config)
        periodic_experiment_check(config)
        periodic_update_check(config)
        return 0
    except Exception as error:
        print(f"PragmAI Claude connector: {error}", file=sys.stderr)
        return 1


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    destination = path.with_name(f"{path.name}.pragm-ai-backup-{int(time.time())}")
    shutil.copy2(path, destination)
    return destination


def set_toml_values(text: str, values: dict[str, object]) -> str:
    lines = text.splitlines()
    pending = dict(values)
    output = []
    in_top_level = True
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^\s*\[", line):
            in_top_level = False
        match = re.match(r"^([A-Za-z0-9_]+)\s*=", line)
        key = match.group(1) if match and in_top_level else None
        if key in pending:
            replacement = pending.pop(key)
            if replacement is not None:
                output.append(f"{key} = {json.dumps(replacement, ensure_ascii=False)}")
            value = line.split("=", 1)[1].lstrip()
            triple_quote = next((quote for quote in ('"""', "'''") if value.startswith(quote)), None)
            if triple_quote and value.count(triple_quote) % 2 == 1:
                index += 1
                while index < len(lines):
                    if lines[index].count(triple_quote) % 2 == 1:
                        break
                    index += 1
        else:
            output.append(line)
        index += 1
    additions = [
        f"{key} = {json.dumps(value, ensure_ascii=False)}"
        for key, value in pending.items() if value is not None
    ]
    return "\n".join([*additions, *output]).rstrip() + "\n"


def top_level_json_value(text: str, key: str):
    """Read the JSON-compatible subset Codex uses for top-level arrays."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^\s*\[", line):
            break
        match = re.match(rf"^{re.escape(key)}\s*=\s*(.*)$", line)
        if not match:
            continue
        candidate = match.group(1).strip()
        for continuation in range(index + 1, len(lines) + 1):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as error:
                if continuation >= len(lines) or re.match(r"^\s*\[", lines[continuation]):
                    raise RuntimeError(f"Existing Codex {key} value cannot be read safely.") from error
                candidate += "\n" + lines[continuation]
    return None


CODEX_OPTIMIZATION_KEYS = (
    "model_auto_compact_token_limit",
    "model_auto_compact_token_limit_scope",
    "compact_prompt",
)


def codex_optimization_values(config: dict, optimization_enabled: bool) -> dict:
    if optimization_enabled:
        return {
            "model_auto_compact_token_limit": COMPACTION_POLICY["codex_growth_threshold_tokens"],
            "model_auto_compact_token_limit_scope": COMPACTION_POLICY["codex_scope"],
            "compact_prompt": COMPACT_PROMPT,
        }
    baseline = config.get("baseline_codex")
    baseline = baseline if isinstance(baseline, dict) else {}
    return {key: baseline.get(key) for key in CODEX_OPTIMIZATION_KEYS}


def capture_codex_baseline(config: dict, text: str) -> None:
    if "baseline_codex" in config:
        return
    if config.get("previous_pragmai_version"):
        config["baseline_codex"] = {key: None for key in CODEX_OPTIMIZATION_KEYS}
        return
    config["baseline_codex"] = {key: top_level_json_value(text, key) for key in CODEX_OPTIMIZATION_KEYS}


def managed_target_version(config: dict) -> str | None:
    candidate = config.get("last_update_notice_version")
    try:
        return candidate if isinstance(candidate, str) and version_tuple(candidate) > version_tuple(VERSION) else None
    except RuntimeError:
        return None


def install_codex(config: dict, optimization_enabled: bool = True, make_backup: bool = True) -> list[str]:
    codex_config = Path.home() / ".codex" / "config.toml"
    original = codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
    capture_codex_baseline(config, original)
    previous = top_level_json_value(original, "notify")
    if "baseline_codex_notify" not in config:
        config["baseline_codex_notify"] = (
            config.get("chained_notify")
            if config.get("previous_pragmai_version") and is_pragmai_command(previous, "codex-notify")
            else previous
        )
    connector_command = installed_command("codex-notify")
    notify = connector_command
    if isinstance(previous, list) and previous:
        if "--previous-notify" in previous:
            notify = list(previous)
            position = notify.index("--previous-notify") + 1
            if position >= len(notify):
                raise RuntimeError("Existing Codex notify wrapper is malformed.")
            notify[position] = json.dumps(connector_command)
        elif previous != connector_command and not is_pragmai_command(previous, "codex-notify"):
            config["chained_notify"] = previous
    backup_path = backup(codex_config) if make_backup else None
    updated = set_toml_values(original, {"notify": notify, **codex_optimization_values(config, optimization_enabled)})
    atomic_write(codex_config, updated)
    codex_dir = Path.home() / ".codex"
    override_instructions = codex_dir / "AGENTS.override.md"
    global_instructions = codex_dir / "AGENTS.md"
    if override_instructions.exists() and override_instructions.read_text(encoding="utf-8").strip():
        global_instructions = override_instructions
    instructions_original = (
        global_instructions.read_text(encoding="utf-8") if global_instructions.exists() else ""
    )
    instructions_backup = backup(global_instructions) if make_backup else None
    instructions_updated = replace_managed_block(
        instructions_original,
        codex_rules_block(optimization_enabled, managed_target_version(config)),
        CODEX_RULES_BLOCK_START,
        CODEX_RULES_BLOCK_END,
    )
    atomic_write(global_instructions, instructions_updated)
    return [
        str(codex_config),
        str(global_instructions),
        *( [str(backup_path)] if backup_path else [] ),
        *( [str(instructions_backup)] if instructions_backup else [] ),
    ]


def replace_managed_block(text: str, block: str, start: str, end: str) -> str:
    pattern = re.compile(rf"\n?{re.escape(start)}.*?{re.escape(end)}\n?", re.S)
    cleaned = pattern.sub("\n", text).rstrip()
    return f"{cleaned}\n\n{block}\n" if cleaned else f"{block}\n"


def remove_managed_block(text: str, start: str, end: str) -> str:
    pattern = re.compile(rf"\n?{re.escape(start)}.*?{re.escape(end)}\n?", re.S)
    cleaned = pattern.sub("\n", text).strip("\n")
    return f"{cleaned}\n" if cleaned else ""


def claude_optimization_values(config: dict, optimization_enabled: bool) -> dict:
    if optimization_enabled:
        return {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": str(COMPACTION_POLICY["claude_trigger_percent"])}
    baseline = config.get("baseline_claude")
    baseline = baseline if isinstance(baseline, dict) else {}
    return {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": baseline.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")}


def capture_claude_baseline(config: dict, environment: dict) -> None:
    if "baseline_claude" in config:
        return
    previous = bool(config.get("previous_pragmai_version"))
    config["baseline_claude"] = {
        "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": (
            None if previous else environment.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
        ),
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": (
            None if previous else environment.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
        ),
    }


def install_claude(config: dict | None = None, optimization_enabled: bool = True, make_backup: bool = True) -> list[str]:
    config = config if isinstance(config, dict) else {}
    settings = Path.home() / ".claude" / "settings.json"
    original = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
    if not isinstance(original, dict):
        raise RuntimeError("Claude settings.json must contain an object.")
    backup_path = backup(settings) if make_backup else None
    hooks = original.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError("Claude settings hooks must contain an object.")
    stop_hooks = hooks.setdefault("Stop", [])
    if not isinstance(stop_hooks, list):
        raise RuntimeError("Claude Stop hooks must contain a list.")
    environment = original.setdefault("env", {})
    if not isinstance(environment, dict):
        raise RuntimeError("Claude settings env must contain an object.")
    capture_claude_baseline(config, environment)
    environment.pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
    for key, value in claude_optimization_values(config, optimization_enabled).items():
        if value is None:
            environment.pop(key, None)
        else:
            environment[key] = value
    command_parts = installed_command("claude-stop")
    command = subprocess.list2cmdline(command_parts) if os.name == "nt" else shlex.join(command_parts)
    existing_pragmai = [
        index for index, entry in enumerate(stop_hooks) if is_pragmai_command(entry, "claude-stop")
    ]
    if existing_pragmai:
        first = existing_pragmai[0]
        stop_hooks[first] = {"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": 30}]}
        for index in reversed(existing_pragmai[1:]):
            del stop_hooks[index]
    else:
        stop_hooks.append({"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": 30}]})
    atomic_write(settings, json.dumps(original, indent=2, ensure_ascii=False) + "\n")
    claude_instructions = Path.home() / ".claude" / "CLAUDE.md"
    instructions_original = claude_instructions.read_text(encoding="utf-8") if claude_instructions.exists() else ""
    instructions_backup = backup(claude_instructions) if make_backup else None
    instructions_updated = replace_managed_block(
        instructions_original,
        claude_compact_block(optimization_enabled, managed_target_version(config)),
        CLAUDE_COMPACT_BLOCK_START,
        CLAUDE_COMPACT_BLOCK_END,
    )
    atomic_write(claude_instructions, instructions_updated)
    return [
        str(settings),
        str(claude_instructions),
        *( [str(backup_path)] if backup_path else [] ),
        *( [str(instructions_backup)] if instructions_backup else [] ),
    ]


def detect_client(home: Path | None = None) -> str:
    home = home or Path.home()
    codex_found = (home / ".codex").exists() or shutil.which("codex") is not None
    claude_found = (home / ".claude").exists() or shutil.which("claude") is not None
    if codex_found and claude_found:
        return "both"
    if codex_found:
        return "codex"
    if claude_found:
        return "claude-code"
    raise RuntimeError("No Codex or Claude Code installation was detected.")


def install_updater_skill(skill_bytes: bytes | None = None) -> Path | None:
    packaged = PACKAGED_SKILL_DIR / "SKILL.md"
    if skill_bytes is None:
        skill_bytes = packaged.read_bytes() if packaged.is_file() else EMBEDDED_UPDATER_SKILL
    if len(skill_bytes) > 100_000 or b"name: pragm-ai-updater" not in skill_bytes[:2_000]:
        raise RuntimeError("The updater skill is invalid.")
    target = UPDATER_SKILL_DIR / "SKILL.md"
    atomic_write_bytes(target, skill_bytes)
    packaged_metadata = PACKAGED_SKILL_DIR / "agents" / "openai.yaml"
    if packaged_metadata.is_file():
        atomic_write_bytes(UPDATER_SKILL_DIR / "agents" / "openai.yaml", packaged_metadata.read_bytes())
    return target


def fetch_bytes(url: str, maximum: int, timeout: int = 20) -> bytes:
    request = Request(url, headers={"User-Agent": f"PragmAI-Updater/{VERSION}"})
    try:
        with urlopen(request, timeout=timeout) as response:
            declared = integer(response.headers.get("Content-Length"))
            if declared > maximum:
                raise RuntimeError("The update file is too large.")
            content = response.read(maximum + 1)
    except HTTPError as error:
        raise RuntimeError(f"The update server rejected the request ({error.code}).") from error
    except URLError as error:
        raise RuntimeError("The update server is unavailable.") from error
    if len(content) > maximum:
        raise RuntimeError("The update file is too large.")
    return content


def trusted_update_url(url: str) -> bool:
    try:
        candidate = urlparse(url)
        trusted = urlparse(DEFAULT_UPDATE_MANIFEST)
        return (
            candidate.scheme == "https"
            and candidate.username is None
            and candidate.hostname == trusted.hostname
            and candidate.port == trusted.port
            and candidate.path.startswith("/downloads/")
            and not candidate.query
            and not candidate.fragment
        )
    except ValueError:
        return False


def verified_asset(specification: dict, maximum: int) -> bytes:
    url = specification.get("url") if isinstance(specification, dict) else None
    expected = specification.get("sha256") if isinstance(specification, dict) else None
    if not isinstance(url, str) or not trusted_update_url(url):
        raise RuntimeError("The update manifest contains an untrusted URL.")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise RuntimeError("The update manifest contains an invalid checksum.")
    content = fetch_bytes(url, maximum)
    if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), expected):
        raise RuntimeError("The downloaded update did not match its SHA-256 checksum.")
    return content


def version_tuple(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value or ""):
        raise RuntimeError("The update manifest contains an invalid version.")
    return tuple(int(part) for part in value.split("."))


def canonical_manifest_payload(manifest: dict) -> bytes:
    unsigned = dict(manifest)
    unsigned.pop("signature", None)
    return json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def verify_manifest_signature(manifest: dict) -> None:
    signature = manifest.get("signature") if isinstance(manifest, dict) else None
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value"}:
        raise RuntimeError("The update manifest is not signed.")
    if (signature.get("algorithm") != RELEASE_SIGNATURE_ALGORITHM or
            signature.get("key_id") != RELEASE_SIGNING_KEY_ID):
        raise RuntimeError("The update manifest uses an untrusted signing key.")
    try:
        raw_signature = base64.b64decode(signature.get("value", ""), validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError("The update manifest signature is invalid.") from error
    key_bytes = (RELEASE_PUBLIC_MODULUS.bit_length() + 7) // 8
    if len(raw_signature) != key_bytes:
        raise RuntimeError("The update manifest signature is invalid.")
    signature_integer = int.from_bytes(raw_signature, "big")
    if signature_integer >= RELEASE_PUBLIC_MODULUS:
        raise RuntimeError("The update manifest signature is invalid.")
    encoded = pow(
        signature_integer, RELEASE_PUBLIC_EXPONENT, RELEASE_PUBLIC_MODULUS
    ).to_bytes(key_bytes, "big")
    digest_info = SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(
        canonical_manifest_payload(manifest)
    ).digest()
    padding_length = key_bytes - len(digest_info) - 3
    expected = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info
    if padding_length < 8 or not hmac.compare_digest(encoded, expected):
        raise RuntimeError("The update manifest signature is invalid.")


def fetch_update_manifest(timeout: int = 20) -> dict:
    manifest_bytes = fetch_bytes(DEFAULT_UPDATE_MANIFEST, 100_000, timeout=timeout)
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("The update manifest is invalid.") from error
    if not isinstance(manifest, dict):
        raise RuntimeError("The update manifest is invalid.")
    verify_manifest_signature(manifest)
    if manifest.get("schema_version") != 1:
        raise RuntimeError("The update manifest schema is unsupported.")
    signing_key = manifest.get("signing_key")
    if not isinstance(signing_key, dict) or (
        signing_key.get("algorithm"), signing_key.get("key_id")
    ) != (RELEASE_SIGNATURE_ALGORITHM, RELEASE_SIGNING_KEY_ID):
        raise RuntimeError("The update manifest signing identity is invalid.")
    if (set(signing_key) != {"algorithm", "key_id", "public_key_url"} or
            signing_key.get("public_key_url") !=
            DEFAULT_UPDATE_MANIFEST.rsplit("/", 1)[0] + "/release-public-key.pem"):
        raise RuntimeError("The update manifest signing identity is invalid.")
    target_version = manifest.get("version")
    if not isinstance(target_version, str):
        raise RuntimeError("The update manifest contains an invalid version.")
    version_tuple(target_version)
    release_base = DEFAULT_UPDATE_MANIFEST.rsplit("/", 1)[0]
    expected_urls = {
        "connector": f"{release_base}/downloads/{target_version}/pragm_ai_connector.py",
        "instructions": f"{release_base}/downloads/{target_version}/INITIAL_OPTIMIZATION.md",
        "skill": f"{release_base}/downloads/{target_version}/pragm-ai-updater/SKILL.md",
    }
    for key, expected_url in expected_urls.items():
        specification = manifest.get(key)
        url = specification.get("url") if isinstance(specification, dict) else None
        checksum = specification.get("sha256") if isinstance(specification, dict) else None
        if not isinstance(specification, dict) or set(specification) != {"url", "sha256"}:
            raise RuntimeError("The update manifest contains an invalid asset.")
        if url != expected_url:
            raise RuntimeError("The update manifest contains an untrusted URL.")
        if not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise RuntimeError("The update manifest contains an invalid checksum.")
    return manifest


def update_availability(timeout: int = 20) -> str | None:
    target_version = fetch_update_manifest(timeout=timeout)["version"]
    return target_version if version_tuple(target_version) > version_tuple(VERSION) else None


def active_codex_instructions(home: Path | None = None) -> Path:
    codex_dir = (home or Path.home()) / ".codex"
    override = codex_dir / "AGENTS.override.md"
    if override.exists() and override.read_text(encoding="utf-8").strip():
        return override
    return codex_dir / "AGENTS.md"


def write_chat_update_notice(target_version: str, config: dict) -> int:
    version_tuple(target_version)
    clients = config.get("installed_clients")
    if not isinstance(clients, list) or not clients:
        detected = detect_client()
        clients = ["codex", "claude-code"] if detected == "both" else [detected]
    changed = 0
    optimization_enabled = active_optimization_state(config)["optimization_enabled"]
    if "codex" in clients:
        instructions = active_codex_instructions()
        original = instructions.read_text(encoding="utf-8") if instructions.exists() else ""
        updated = replace_managed_block(
            original,
            codex_rules_block(optimization_enabled, target_version),
            CODEX_RULES_BLOCK_START,
            CODEX_RULES_BLOCK_END,
        )
        if updated != original:
            atomic_write(instructions, updated)
            changed += 1
    if "claude-code" in clients:
        instructions = Path.home() / ".claude" / "CLAUDE.md"
        original = instructions.read_text(encoding="utf-8") if instructions.exists() else ""
        updated = replace_managed_block(
            original,
            claude_compact_block(optimization_enabled, target_version),
            CLAUDE_COMPACT_BLOCK_START,
            CLAUDE_COMPACT_BLOCK_END,
        )
        if updated != original:
            atomic_write(instructions, updated)
            changed += 1
    return changed


def apply_experiment_assignment(config: dict, assignment: dict, make_backup: bool = False) -> int:
    clients = config.get("installed_clients")
    if not isinstance(clients, list) or not clients:
        detected = detect_client()
        clients = ["codex", "claude-code"] if detected == "both" else [detected]
    enabled = bool(assignment["optimization_enabled"])
    changed = []
    if "codex" in clients:
        changed.extend(install_codex(config, enabled, make_backup=make_backup))
        install_updater_skill()
    if "claude-code" in clients:
        changed.extend(install_claude(config, enabled, make_backup=make_backup))
    if assignment.get("experiment_id"):
        config["active_experiment"] = assignment
    else:
        config.pop("active_experiment", None)
    config.pop("previous_pragmai_version", None)
    config["installed_clients"] = [client for client in ("codex", "claude-code") if client in clients]
    return len(changed)


def periodic_experiment_check(config: dict, moment: datetime | None = None) -> None:
    if optimization_mode(config) != "experiment":
        return
    assignment = experiment_assignment(config, moment)
    active = config.get("active_experiment")
    if isinstance(active, dict) and active.get("experiment_unit_id") == assignment["experiment_unit_id"]:
        return
    try:
        apply_experiment_assignment(config, assignment, make_backup=False)
        atomic_write(CONFIG_FILE, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    except Exception:
        # A/B rotation is best-effort; preserve the previous, truthfully labelled assignment on failure.
        pass


def periodic_update_check(config: dict, now: int | None = None) -> None:
    checked_at = int(now if now is not None else time.time())
    previous_check = integer(config.get("last_update_check_at"))
    if checked_at - previous_check < UPDATE_CHECK_INTERVAL_SECONDS:
        return
    config["last_update_check_at"] = checked_at
    try:
        available = update_availability(timeout=3)
        if available and config.get("last_update_notice_version") != available:
            write_chat_update_notice(available, config)
            config["last_update_notice_version"] = available
    except Exception:
        pass
    try:
        atomic_write(CONFIG_FILE, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    except OSError:
        # Update discovery is best-effort and must never interrupt telemetry.
        pass


def check_update() -> int:
    available = update_availability()
    if available:
        print(f"PragmAI update available: {VERSION} -> {available}.")
        print("Ask Codex to use pragm-ai-updater or run this connector with: update")
    else:
        print(f"PragmAI {VERSION} is up to date.")
    return 0


def repair() -> int:
    config = load_config()
    clients = config.get("installed_clients")
    if not isinstance(clients, list) or not clients:
        detected = detect_client()
        clients = ["codex", "claude-code"] if detected == "both" else [detected]
    config["previous_pragmai_version"] = config.get("version")
    config["installed_clients"] = clients
    assignment = (
        experiment_assignment(config)
        if optimization_mode(config) == "experiment"
        else {"optimization_enabled": True}
    )
    changed_count = apply_experiment_assignment(config, assignment, make_backup=True)
    config["version"] = VERSION
    config["connector_sha256"] = hashlib.sha256(INSTALL_FILE.read_bytes()).hexdigest()
    atomic_write(CONFIG_FILE, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"PragmAI {VERSION} verified; {changed_count} managed file(s) checked.")
    return 0


def set_optimization_mode(args) -> int:
    config = load_config()
    mode = args.mode.replace("-", "_")
    if mode not in OPTIMIZATION_MODES:
        raise RuntimeError("Unsupported optimization mode.")
    config["optimization_mode"] = mode
    assignment = (
        experiment_assignment(config)
        if mode == "experiment"
        else {"optimization_enabled": True}
    )
    changed_count = apply_experiment_assignment(config, assignment, make_backup=True)
    atomic_write(CONFIG_FILE, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    if mode == "always_on":
        print("PragmAI optimization is always ON; three-day A/B assignment is disabled.")
    else:
        print("PragmAI three-day alternating A/B assignment is enabled.")
    print(f"PragmAI {VERSION} verified; {changed_count} managed file(s) checked.")
    return 0


def doctor() -> int:
    checks: list[tuple[str, bool]] = []

    def record(label: str, condition: bool) -> None:
        checks.append((label, bool(condition)))

    try:
        config = load_config()
        record("Private configuration", True)
    except Exception:
        config = {}
        record("Private configuration", False)

    artifact = INSTALL_FILE
    record("Installed executable", artifact.is_file() and (os.name == "nt" or os.access(artifact, os.X_OK)))
    endpoint = urlparse(str(config.get("endpoint", "")))
    record(
        "Secure endpoint",
        endpoint.scheme == "https" and bool(endpoint.netloc) and endpoint.username is None,
    )
    record(
        "Private identity",
        bool(COMPANY_RE.fullmatch(str(config.get("company_id", ""))))
        and bool(EMAIL_RE.fullmatch(str(config.get("employee_id", ""))))
        and len(str(config.get("ingest_secret", ""))) >= 16,
    )

    clients = config.get("installed_clients") if isinstance(config, dict) else []
    clients = clients if isinstance(clients, list) else []
    record("Configured client list", bool(clients) and set(clients) <= {"codex", "claude-code"})
    if "codex" in clients:
        codex_config = Path.home() / ".codex" / "config.toml"
        codex_text = codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
        try:
            notify = top_level_json_value(codex_text, "notify")
        except RuntimeError:
            notify = None
        record("Codex hook", is_pragmai_command(notify, "codex-notify"))
        instructions = [Path.home() / ".codex" / "AGENTS.override.md", Path.home() / ".codex" / "AGENTS.md"]
        record(
            "Codex managed rules",
            any(path.exists() and CODEX_RULES_BLOCK_START in path.read_text(encoding="utf-8") for path in instructions),
        )
    if "claude-code" in clients:
        settings_path = Path.home() / ".claude" / "settings.json"
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            stop_hooks = ((settings.get("hooks") or {}).get("Stop") or [])
        except (OSError, json.JSONDecodeError, AttributeError):
            stop_hooks = []
        record("Claude Code hook", any(is_pragmai_command(entry, "claude-stop") for entry in stop_hooks))
        instructions = Path.home() / ".claude" / "CLAUDE.md"
        record(
            "Claude Code managed rules",
            instructions.exists() and CLAUDE_COMPACT_BLOCK_START in instructions.read_text(encoding="utf-8"),
        )

    for label, passed in checks:
        print(f"{'OK' if passed else 'FAIL'}  {label}")
    passed = sum(1 for _, condition in checks if condition)
    print(f"PragmAI doctor: {passed}/{len(checks)} checks passed.")
    return 0 if passed == len(checks) else 1


def restore_codex(config: dict) -> int:
    changed = 0
    codex_config = Path.home() / ".codex" / "config.toml"
    if codex_config.exists():
        original = codex_config.read_text(encoding="utf-8")
        baseline = config.get("baseline_codex")
        values = dict(baseline) if isinstance(baseline, dict) else {
            key: None for key in CODEX_OPTIMIZATION_KEYS
        }
        current_notify = top_level_json_value(original, "notify")
        if is_pragmai_command(current_notify, "codex-notify"):
            if "baseline_codex_notify" in config:
                values["notify"] = config.get("baseline_codex_notify")
            else:
                values["notify"] = config.get("chained_notify")
        updated = set_toml_values(original, values)
        if updated != original:
            backup(codex_config)
            atomic_write(codex_config, updated)
            changed += 1
    for instructions in (Path.home() / ".codex" / "AGENTS.override.md", Path.home() / ".codex" / "AGENTS.md"):
        if not instructions.exists():
            continue
        original = instructions.read_text(encoding="utf-8")
        updated = remove_managed_block(original, CODEX_RULES_BLOCK_START, CODEX_RULES_BLOCK_END)
        if updated != original:
            backup(instructions)
            atomic_write(instructions, updated)
            changed += 1
    return changed


def restore_claude(config: dict) -> int:
    changed = 0
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        original_text = settings_path.read_text(encoding="utf-8")
        settings = json.loads(original_text)
        if not isinstance(settings, dict):
            raise RuntimeError("Claude settings.json must contain an object.")
        hooks = settings.get("hooks")
        if isinstance(hooks, dict):
            stop_hooks = hooks.get("Stop")
            if isinstance(stop_hooks, list):
                hooks["Stop"] = [
                    entry for entry in stop_hooks if not is_pragmai_command(entry, "claude-stop")
                ]
                if not hooks["Stop"]:
                    hooks.pop("Stop", None)
            if not hooks:
                settings.pop("hooks", None)
        environment = settings.get("env")
        if not isinstance(environment, dict):
            environment = {}
            settings["env"] = environment
        baseline = config.get("baseline_claude")
        baseline = baseline if isinstance(baseline, dict) else {}
        for key in ("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_CODE_AUTO_COMPACT_WINDOW"):
            value = baseline.get(key)
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        if not environment:
            settings.pop("env", None)
        updated_text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
        if updated_text != original_text:
            backup(settings_path)
            atomic_write(settings_path, updated_text)
            changed += 1
    instructions = Path.home() / ".claude" / "CLAUDE.md"
    if instructions.exists():
        original = instructions.read_text(encoding="utf-8")
        updated = remove_managed_block(original, CLAUDE_COMPACT_BLOCK_START, CLAUDE_COMPACT_BLOCK_END)
        if updated != original:
            backup(instructions)
            atomic_write(instructions, updated)
            changed += 1
    return changed


def remove_installed_artifact() -> bool:
    if not INSTALL_FILE.exists():
        return True
    if os.name != "nt" or current_artifact_path() != INSTALL_FILE.resolve():
        INSTALL_FILE.unlink()
        return True
    remover = INSTALL_DIR / "remove-pragmai.cmd"
    content = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'del /f /q "{INSTALL_FILE}"\r\n'
        'del /f /q "%~f0"\r\n'
    )
    remover.write_text(content, encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        ["cmd.exe", "/d", "/c", str(remover)],
        close_fds=True,
        creationflags=flags,
    )
    return True


def uninstall() -> int:
    config = load_config()
    clients = config.get("installed_clients")
    clients = clients if isinstance(clients, list) else []
    changed = 0
    if "codex" in clients:
        changed += restore_codex(config)
    if "claude-code" in clients:
        changed += restore_claude(config)
    skill = UPDATER_SKILL_DIR / "SKILL.md"
    if skill.exists() and "name: pragm-ai-updater" in skill.read_text(encoding="utf-8")[:2_000]:
        shutil.rmtree(UPDATER_SKILL_DIR)
    CONFIG_FILE.unlink(missing_ok=True)
    remove_installed_artifact()
    print(f"PragmAI uninstalled; {changed} managed configuration file(s) restored.")
    print("Safety backups were retained and can be removed after verifying both clients.")
    return 0


def update() -> int:
    if STANDALONE:
        raise RuntimeError(
            "This preview standalone build is updated by running the official installer again."
        )
    manifest = fetch_update_manifest()
    target_version = manifest["version"]
    if version_tuple(target_version) < version_tuple(VERSION):
        raise RuntimeError("The update manifest would downgrade this connector.")
    connector_bytes = verified_asset(manifest.get("connector"), 2_000_000)
    verified_asset(manifest.get("instructions"), 1_000_000)
    skill_bytes = verified_asset(manifest.get("skill"), 100_000)
    match = re.search(rb'^VERSION = "(\d+\.\d+\.\d+)"$', connector_bytes, re.M)
    if not match or match.group(1).decode() != target_version:
        raise RuntimeError("The connector version does not match the update manifest.")

    previous_version = VERSION
    atomic_write_bytes(INSTALL_FILE, connector_bytes, 0o700)
    install_updater_skill(skill_bytes)
    result = subprocess.run(
        [sys.executable, str(INSTALL_FILE), "repair"],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "repair failed").strip().splitlines()[-1]
        raise RuntimeError(f"The connector was downloaded but configuration repair failed: {detail}")
    print(f"PragmAI updated: {previous_version} -> {target_version}.")
    if result.stdout.strip():
        print(result.stdout.strip())
    return 0


def install(args) -> int:
    company_id = args.company_id or os.environ.get("PRAGMAI_COMPANY_ID", "")
    endpoint = args.endpoint or os.environ.get("PRAGMAI_ENDPOINT", DEFAULT_ENDPOINT)
    if not COMPANY_RE.fullmatch(company_id):
        raise RuntimeError("company_id must contain 3-64 letters, numbers, underscores or dashes.")
    requested_mode = (args.optimization_mode or "experiment").replace("-", "_")
    print(install_privacy_notice(requested_mode))
    employee_id = (args.employee_email or input("Correo que autorizás como identificador: ")).strip().lower()
    if not EMAIL_RE.fullmatch(employee_id):
        raise RuntimeError("A valid, explicitly authorized employee email is required.")
    if not args.consent_confirmed:
        consent = input(
            f"¿Autorizás esta medición para {company_id} usando {employee_id} como identificador? [s/N]: "
        ).strip().lower()
        if consent not in {"s", "si", "sí", "y", "yes"}:
            raise RuntimeError("Installation cancelled because explicit consent was not granted.")
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme != "https" or not parsed_endpoint.netloc or parsed_endpoint.username:
        raise RuntimeError("The endpoint must be an HTTPS URL without embedded credentials.")
    if not args.ingest_secret_stdin:
        raise RuntimeError("The company ingest secret must be supplied through standard input.")
    ingest_secret = sys.stdin.readline().strip()
    if len(ingest_secret) < 16:
        raise RuntimeError("The company ingest secret must contain at least 16 characters.")

    previous_config = {}
    if CONFIG_FILE.exists():
        try:
            previous_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_config = {}
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    source_file = current_artifact_path()
    installed_file = INSTALL_FILE.resolve()
    if source_file != installed_file:
        shutil.copy2(source_file, INSTALL_FILE)
    INSTALL_FILE.chmod(0o700)
    installed_sha256 = hashlib.sha256(INSTALL_FILE.read_bytes()).hexdigest()
    config = {
        "version": VERSION,
        "endpoint": endpoint,
        "ingest_secret": ingest_secret,
        "company_id": company_id,
        "employee_id": employee_id,
        "billing_mode": args.billing_mode,
        "optimization_mode": requested_mode,
        "fingerprint_key": previous_config.get("fingerprint_key") or secrets.token_hex(32),
        "connector_sha256": installed_sha256,
        "installed_clients": [],
    }
    if previous_config:
        config["previous_pragmai_version"] = previous_config.get("version", "legacy")
        for key in ("baseline_codex", "baseline_codex_notify", "baseline_claude", "chained_notify"):
            if key in previous_config:
                config[key] = previous_config[key]
    selected_client = detect_client() if args.client == "auto" else args.client
    config["installed_clients"] = (
        ["codex", "claude-code"] if selected_client == "both" else [selected_client]
    )
    assignment = (
        experiment_assignment(config)
        if optimization_mode(config) == "experiment"
        else {"optimization_enabled": True}
    )
    changed_count = apply_experiment_assignment(config, assignment, make_backup=True)
    atomic_write(CONFIG_FILE, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print("PragmAI installed. Restart the configured client before the ingestion test.")
    print("Changed files:")
    print(f"Managed files checked: {changed_count}")
    for path in [INSTALL_FILE, CONFIG_FILE]:
        print(f"- {path}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="PragmAI direct privacy-safe connector")
    result.add_argument("--version", action="version", version=VERSION)
    commands = result.add_subparsers(dest="command", required=True)
    for command_name in ("setup", "install"):
        setup = commands.add_parser(command_name)
        setup.add_argument("--client", choices=("auto", "codex", "claude-code", "both"), default="auto")
        setup.add_argument("--company-id")
        setup.add_argument("--employee-email")
        setup.add_argument("--consent-confirmed", action="store_true", help=argparse.SUPPRESS)
        setup.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
        setup.add_argument("--billing-mode", choices=("subscription", "api", "unknown"), default="subscription")
        setup.add_argument("--optimization-mode", choices=("experiment", "always-on"), default="experiment")
        setup.add_argument("--ingest-secret-stdin", action="store_true", help=argparse.SUPPRESS)
    notify = commands.add_parser("codex-notify")
    notify.add_argument("payload")
    commands.add_parser("claude-stop")
    commands.add_parser("update")
    commands.add_parser("check-update")
    commands.add_parser("doctor")
    commands.add_parser("uninstall")
    commands.add_parser("repair", help=argparse.SUPPRESS)
    mode = commands.add_parser("set-optimization-mode")
    mode.add_argument("mode", choices=("experiment", "always-on"))
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"setup", "install"}:
            return install(args)
        if args.command == "codex-notify":
            return codex_notify(args.payload)
        if args.command == "claude-stop":
            return claude_stop()
        if args.command == "update":
            return update()
        if args.command == "check-update":
            return check_update()
        if args.command == "doctor":
            return doctor()
        if args.command == "uninstall":
            return uninstall()
        if args.command == "repair":
            return repair()
        if args.command == "set-optimization-mode":
            return set_optimization_mode(args)
        return 2
    except Exception as error:
        print(f"PragmAI: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
