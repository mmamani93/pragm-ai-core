# PragmAI — managed rules and telemetry

This source document is included in the connector's signed release. It defines what PragmAI installs, what data it processes, and which optimization rules it manages. It contains no credentials and does not replace the public installation guide.

## Installation and consent

The standard path is to install the official executable and run `pragmai setup`. A PragmAI administrator creates a temporary invitation in the administration page and shares it directly with the employee.

During `setup`:

1. the executable detects Codex, Claude Code, or both; if neither is found, it reports that result and exits without changing the computer or consuming the invitation;
2. if both are installed, the employee chooses Codex, Claude Code, or both;
3. the executable explains the local changes and telemetry;
4. the employee explicitly authorizes use of their email as an identifier;
5. the email is normalized to lowercase and is not used for any other purpose;
6. the executable displays a temporary public code;
7. the employee confirms it through the invitation link;
8. the server delivers an individual revocable credential directly to the executable;
9. the affected configurations are backed up and only the selected hooks are installed;
10. `pragmai doctor` verifies the result without exposing secrets.

The permanent credential never appears in the link, public code, chat, a URL, or command arguments. The standalone executable does not require Python or third-party packages on the employee's computer.

Operational commands:

- `pragmai setup`: pairs and installs;
- `pragmai doctor`: diagnoses configuration, integrity, and synchronization without querying Supabase or exposing credentials;
- `pragmai check-update`: performs a read-only check of the signed manifest;
- `pragmai repair`: synchronizes the private copy used by hooks and repairs managed changes with authorization;
- `pragmai uninstall`: removes only managed changes and restores previous configurations.

## Permanent privacy rules

These rules are installed in every mode and are merged without deleting existing instructions:

- never include prompts, responses, commands, arguments, file names, paths, URLs, transcripts, session identifiers, or individual tool names in telemetry;
- never expose private configuration or keep credentials outside protected local storage;
- never create local analytics histories, queues, CSV files, or files for the model to process metrics;
- transform information transiently and send only technical metrics and closed categories;
- never query Supabase or interpret company analytics from the employee assistant;
- check for updates in read-only mode; install, repair, or change the mode only after an explicit request;
- preserve user and project instructions; the more specific rule takes precedence.

If the endpoint is unavailable, the event is discarded. PragmAI prioritizes avoiding data accumulation on the employee's computer.

## Optimization modes

- `experiment`: alternates ON/OFF in three-day UTC blocks. Assignment is pseudonymous and the event records the state actually used.
- `always_on`: remains ON and generates no experiment identity.

Changing modes requires explicit authorization. OFF retains capture, privacy, and update checks; it removes only the optimization interventions and restores the backed-up prior configuration.

## Rules active in ON

The following block is installed only in ON. It is merged with existing instructions without replacing them:

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

Do not install a vector database, SQLite, a local generative model, a semantic router, or continuously rewritten memory by default. They require a demonstrated bottleneck and a controlled comparison.

## Managed compaction

In Codex, ON configures:

```toml
model_auto_compact_token_limit = 100000
model_auto_compact_token_limit_scope = "body_after_prefix"
```

The limit applies to the body after the fixed prefix, not to total context. It may be exceeded around a transition, and one row may aggregate multiple internal calls; calls, maxima, and observed compactions are measured instead of being inferred from one isolated number.

Claude Code has no public option equivalent to `body_after_prefix`. PragmAI derives an approximate 64% trigger from a 200,000-token reference window and adds checkpoint instructions. It must be validated in each real environment; if the client does not honor it, it is reported as unvalidated.

The checkpoint target is at most 10,000 tokens and preserves:

- objective and requirements;
- active instructions;
- verified facts and required evidence;
- decisions and corrections;
- completed changes and tests;
- blockers and next steps.

It removes redundant conversation and resolved output. The size is a target, not an exact guarantee.

## Local capture

### Codex

The local `notify` hook locates the completed exchange in the telemetry maintained by the client, aggregates its internal calls, and produces one `user_exchange` event. It discards internal activity, `codex-auto-review`, turns with no usage, and all content.

### Claude Code

The `Stop` hook takes only the latest human-initiated exchange, aggregates its calls, and reduces tools to closed families. This integration covers Claude Code, not the claude.ai website.

### Common transformations

Task text may be used transiently in memory to assign `work_domain`, `task_type`, and `workflow_pattern` from closed lists and to produce an HMAC fingerprint of the normalized form. Neither the normalized text nor the HMAC key leaves the computer.

Tools are reduced to counts in the closed families `web`, `browser`, `filesystem_read`, `filesystem_write`, `database`, `office_documents`, `image_generation`, `external_app`, and `other`, plus the subfamilies `shell_testing`, `shell_build_deploy`, `shell_version_control`, `shell_database`, `shell_dependency_management`, `shell_data_processing`, `shell_file_inspection`, and `shell_general`. Names, arguments, and commands are never transmitted. Historical events are not reclassified when the available evidence is insufficient.

The fingerprint permits recurrence to be counted within the same company, employee, and pattern:

- first observation: `low`;
- second observation: `medium`;
- third or later observation: `high`.

This measures observed technical similarity; it does not prove that a process can be automated. A PragmAI administrator validates the context with the employee before recommending changes.

## Metrics sent

Only when exposed by the client:

- connector and telemetry versions;
- company and authorized email;
- client, model, reasoning effort, and profile;
- aggregate input, output, cache-read, cache-write, and reasoning tokens;
- internal-call count and maximum input per call;
- post-tool calls, continuations, and cache misses;
- tool-family counts and aggregate result characters;
- duration and technical compaction measurements;
- requested versus effective configuration and ON/OFF state;
- pseudonymous experiment identity only in `experiment`;
- closed work categories and private recurrence;
- compaction replay and sensitivity when supported by the telemetry version.

Missing fields are never invented. Averages, totals, costs, credits, and recurrence are derived centrally when they can be calculated from base data. The API accepts some legacy fields for compatibility but validates and discards them before storage when they are redundant.

Results after a compaction are observed. Avoided tokens, compaction cost, avoided credits, and net savings are server-side counterfactual estimates: they may be negative and are not an official provider charge or credit.

PragmAI does not emit an automation score from the connector. Recommendations require central analysis and additional company evidence.

## Updates, security, and user responsibility

At most once every 24 hours of use, the connector may check the official manifest. The check:

- does not call the model or send additional telemetry;
- verifies the signature before trusting a version, location, or hash;
- installs nothing;
- adds a managed notice when a newer version exists.

Installation occurs only after the user authorizes it. For the standalone executable, the official package or artifact is updated first; `pragmai repair` then atomically synchronizes the private copy used by hooks. Identity, credential, mode, and base configuration are preserved, and a recoverable backup is retained. `pragmai doctor` requires both copies to match in version and integrity.

On Windows, WinGet is tried first. If it cannot find `PragmAI.PragmAI`, the assistant reports that limitation and asks for explicit authorization before downloading or executing an alternative. Only after authorization may it use the stable release at <https://github.com/mmamani93/pragm-ai-core/releases>, select the version named by the signed manifest, download `pragmai-windows-x64.zip`, verify its SHA-256 against the digest published by GitHub, and run `repair` and `doctor` with the new executable. Inspecting the release page is read-only and does not authorize installation.

Use of PragmAI and the decision to install, defer, test, or apply an update are the user's responsibility. The user must obtain any required authorization, verify release authenticity and integrity, maintain backups, test compatibility, secure the device and credentials, and validate the result. Unless separately agreed in writing, PragmAI and its contributors have no duty to provide, monitor, install, or test updates; preserve compatibility or availability; or recover systems or data. See `LICENSE` for the supplemental disclaimer, warranty disclaimer, and limitation of liability.

A valid signature protects the publication chain, but it cannot prevent a person or malware with control of the local account or administrative privileges from replacing software. Local permissions, company authentication, and revocable credentials reduce risk; they do not eliminate it.

## Validation

After restarting the client:

1. run `pragmai doctor`;
2. perform one employee-initiated test exchange;
3. confirm exactly one row under the correct company and email;
4. reconcile tokens and internal calls;
5. verify the telemetry version, effective configuration, and mode;
6. verify the absence of free text, individual tool names, commands, arguments, paths, URLs, and session identifiers;
7. in `experiment`, require a complete assignment; in `always_on`, require ON and no experiment identifiers;
8. record only pass or fail.

Recover a revoked installation with a new invitation and `pragmai setup`. Previous credentials are never recovered or redistributed.
