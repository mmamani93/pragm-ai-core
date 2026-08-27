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
| `tokens_reasoning` | Aggregate reasoning tokens when exposed. |
| `model_calls` | Number of model calls observed inside the exchange. |
| `max_input_tokens_per_call` | Largest observed input context. |
| `calls_over_compaction_threshold` | Calls whose context crossed the configured threshold. |
| `cache_miss_calls` | Calls with no observed cache read. |

## Closed work and tool categories

`work_domain`, `task_type`, and `workflow_pattern` are selected locally from fixed enumerations. They are coarse technical categories, not stored task descriptions. `classification_version` identifies the deterministic ruleset.

`tool_category_counts` contains counts for closed tool families such as file inspection, testing, version control, or filesystem writing. It never contains individual tool names, commands, arguments, or results. `tool_result_characters` is only the aggregate character count of observed local tool results.

PragmAI Core does not emit automation scores, recommendations, quality judgments, or suggested improvements. Those are outside the public collection layer.

## Workflow and compacting counters

| Field | Meaning |
|---|---|
| `post_tool_model_calls` | Model calls observed after a tool result. |
| `continuation_model_calls` | Continuation calls observed inside the exchange. |
| `compaction_measurements` | Closed numeric measurements around observed compacting boundaries. Empty when no boundary is measurable. |
| `compaction_counterfactual` | Optional Codex v5 aggregate that replays the technical context trajectory against the original compaction threshold. It contains method, coverage, threshold and checkpoint bases, aggregate input, and estimated original compaction counters for the current exchange. It is emitted only in permanently enabled mode when the local session has enough compacting evidence. |
| `config_profile` | Closed public name of the active local profile. |
| `compaction_threshold_tokens`, `compaction_scope` | Effective observed threshold and scope. |
| `configured_compaction_threshold_tokens` | Threshold requested by the managed configuration. |
| `config_status` | Whether observed and requested configuration match. |
| `optimization_enabled` | Whether the managed optimization was active for this exchange. |
| `billing_mode` | Subscription, API, or unknown; it is not a price or charge. |
| `recurrence_key` | HMAC-derived shape identifier. It cannot be reversed into the source text and is not a session identifier. |

The v5 counterfactual reads the full Codex technical session only transiently. The session identifier, call sequence, source records, and conversation content never enter the event. The hosted service values this numeric aggregate and labels the result as an inferred longitudinal estimate rather than an observed charge or causal experiment.

## Explicitly forbidden

The connector and server schema reject prompts, responses, free text, transcripts, commands, arguments, individual tool names, tool output, file names, paths, URLs, session or thread identifiers, and unknown fields. Privacy tests verify representative cases before every release.
