# PragmAI telemetry reference

PragmAI emits one aggregate event after a human exchange. The connector builds the event transiently and sends it directly; it does not create a local analytics history, CSV, retry queue, or transcript copy.

The canonical synthetic example is [`examples/telemetry-event.json`](../examples/telemetry-event.json). Its values are invented and contain no customer activity.

## Identity and envelope

| Field | Meaning |
|---|---|
| `event_id` | Random identifier for deduplication. It is not a conversation or session identifier. |
| `occurred_at` | Completion timestamp. |
| `company_id` | Stable company identifier assigned by PragmAI. |
| `employee_id` | Lowercase email explicitly authorized by the employee. |
| `client` | Closed client name, currently Codex or Claude Code. |
| `connector_version` | Local connector version. |
| `telemetry_version` | Event schema version. |

## Model and usage counters

The connector uses counters exposed by the local client. Missing data remains absent or null rather than being invented.

| Field | Meaning |
|---|---|
| `model`, `reasoning_effort` | Model configuration reported by the client. |
| `duration_ms` | Elapsed time covered by the exchange when observable. |
| `tokens_input`, `tokens_output` | Aggregate input and output tokens. |
| `tokens_cache_read`, `tokens_cache_write` | Aggregate cache counters when exposed. |
| `tokens_cache_write_1h` | Subset of cache-write tokens using a one-hour TTL when the client exposes it. |
| `tokens_reasoning` | Aggregate reasoning tokens when exposed. |
| `model_calls` | Number of model calls observed inside the exchange. |
| `max_input_tokens_per_call` | Largest observed input context. |
| `calls_over_compaction_threshold` | Calls whose context crossed the configured threshold. |
| `cache_miss_calls` | Calls with no observed cache read. |
| `long_context_fresh_input_tokens`, `long_context_cached_input_tokens`, `long_context_cache_write_tokens`, `long_context_output_tokens` | Usage buckets from calls above the provider's long-context pricing threshold. They permit server-side per-call pricing without transmitting call sequences. |

## Closed work and tool categories

`work_domain`, `task_type`, and `workflow_pattern` are selected locally from fixed enumerations. They are coarse technical categories, not stored task descriptions. `classification_version` identifies the deterministic ruleset.

`tool_category_counts` contains counts for closed tool families such as file inspection, testing, version control, or filesystem writing. It never contains individual tool names, commands, arguments, or results. `tool_result_characters` is only the aggregate character count of observed local tool results.

Codex telemetry v7 can also emit `code_lines_added`, `code_lines_removed`, `plugin_calls`, and `plugin_category_counts`. Code lines come only from explicit completed `FileChange` items for recognized code files. Plugin calls come only from explicit completed MCP tool items and are grouped into the existing closed taxonomy. Null means the client did not expose the activity signal; zero means it was measured and no matching activity occurred. File names, paths, diffs, content, plugin names, and individual tool names are discarded locally. Skill use is not inferred when the client does not expose an explicit reliable signal.

PragmAI Core does not emit automation scores, recommendations, quality judgments, or suggested improvements. Those are outside the public collection layer.

## Workflow and compacting counters

| Field | Meaning |
|---|---|
| `post_tool_model_calls` | Model calls observed after a tool result. |
| `continuation_model_calls` | Continuation calls observed inside the exchange. |
| `compaction_measurements` | Closed numeric measurements around observed compacting boundaries. Empty when no boundary is measurable. |
| `compaction_counterfactual` | Optional Codex v5 aggregate that replays the technical context trajectory against the original compaction threshold. It contains method, coverage, threshold and checkpoint bases, aggregate input, and estimated original compaction counters for the current exchange. It is emitted only in permanently enabled mode when the local session has enough compacting evidence. |
| `compaction_sensitivity` | Optional Codex v6 aggregate that deterministically replays a closed grid at the current threshold, ±25,000 and ±50,000 tokens, plus the original limit. It contains only scenario totals and labeled threshold/checkpoint bases, including a profile checkpoint estimate for sessions that never compacted. |
| `config_profile` | Closed public name of the active local profile. |
| `compaction_threshold_tokens`, `compaction_scope` | Effective observed threshold and scope. |
| `configured_compaction_threshold_tokens` | Threshold requested by the managed configuration. |
| `config_status` | Whether observed and requested configuration match. |
| `optimization_enabled` | Whether the managed optimization was active for this exchange. |
| `billing_mode` | Subscription, API, or unknown; it is not a price or charge. |
| `recurrence_key` | HMAC-derived shape identifier. It cannot be reversed into the source text and is not a session identifier. |

The v5 counterfactual, v6 sensitivity grid, and v7 activity counters read Codex technical records only transiently. The session identifier, call sequence, source records, file metadata, diffs, plugin names, and conversation content never enter the event. All three run entirely as deterministic local software and do not call the model. The hosted service values these numeric aggregates and labels inferred values separately from observed counters.

## Explicitly forbidden

The connector and server schema reject prompts, responses, free text, transcripts, commands, arguments, individual tool names, tool output, file names, paths, URLs, session or thread identifiers, and unknown fields. Privacy tests verify representative cases before every release.
