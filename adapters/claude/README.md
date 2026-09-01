# Claude Code adapter

Claude Code uses the shared `adapters/pragm_ai_connector.py` connector. Installation adds a `Stop` hook that locally processes the latest human exchange and sends one aggregate technical event.

This integration covers Claude Code, including when it runs inside Warp. It does not cover the claude.ai website.

## Enrollment

1. Install the official executable for the platform.
2. Run `pragmai setup`.
3. Confirm that it detected Claude Code and, if Codex is also present, choose Claude Code or both. If it detects no supported client, it exits without changes.
4. Explicitly authorize content-free telemetry and the normalized email that identifies the employee.
5. Obtain a temporary public code and confirm it through the one-use invitation link shared by a PragmAI administrator over a trusted channel.
6. Allow the executable to back up the configuration, install the `Stop` hook, and add the managed block to `~/.claude/CLAUDE.md`.
7. Run `pragmai doctor`, restart Claude Code, and complete validation.

The individual credential is delivered directly to the executable and never appears in chat, the link, the public code, or command arguments. The employee assistant does not query Supabase or interpret company analytics.

## Capture and privacy

The hook reads the technical transcript already maintained by Claude Code, identifies the latest human-initiated exchange, aggregates its calls, and discards content before sending. It does not invoke the model or create a local history, CSV file, or queue.

When Claude Code exposes them, PragmAI sends:

- aggregate input, output, cache, and reasoning tokens;
- internal calls, maximum input, and calls over the threshold;
- duration and canonical compaction measurements;
- closed tool families and aggregate result size;
- client, model, effort, profile, and closed work categories;
- connector version, telemetry version, and configuration status;
- ON/OFF state and an experimental HMAC identity only in `experiment`;
- private HMAC recurrence fingerprint.

Claude Code does not expose a subscription-credit unit equivalent to the one published for Codex. Therefore, `credits_used` has no coverage for Claude instead of being inferred from tokens; the API equivalent can still be calculated from the current public price. When telemetry distinguishes one-hour cache writes, that volume is preserved so its specific price can be applied.

Prompts, responses, transcripts, session identifiers, tool names and arguments, commands, files, paths, URLs, results, and all free text outside the schema are discarded. Missing fields remain absent; they are neither invented nor completed with another model call.

## Optimization and compaction

Modes:

- `experiment`: alternates ON/OFF in three-day UTC blocks;
- `always_on`: remains ON and is excluded from the A/B experiment.

In ON, the connector adds persistent instructions for a checkpoint target of at most 10,000 tokens and configures `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=64` against a 200,000-token reference. In OFF, it restores the previous value and removes only the optimization rules.

Claude Code does not provide Codex's explicit `body_after_prefix` scope, and some versions may ignore the override. The configuration remains tentative until compaction and continuity are observed on the actual computer. A marker does not prove complete measurement or credit savings.

Changing the mode requires an explicit user request. The hook may prepare the next block after an exchange, but it records the state actually used. It is not a scheduled task or an additional model call.

Longitudinal v5 replay and v6 sensitivity are specific to Codex. Claude retains only the compaction measurements its telemetry permits it to observe.

## Validation

After restarting Claude Code:

1. run `pragmai doctor`;
2. complete one human exchange;
3. confirm one row under the correct company and email;
4. verify version, telemetry, configuration, calls, families, and `tool_result_characters`;
5. require a complete assignment in `experiment`; in `always_on`, require ON and no experiment identifiers;
6. confirm that no sensitive content is present;
7. validate capture and compaction separately.

Do not declare the integration active until this test is completed in the real environment. Economic estimates are calculated on the server and are not official Claude Code charges. Missing subscription-credit coverage is a coverage limitation, not zero consumption.

## Updates and recovery

At most once every 24 hours of use, the connector may check a signed official manifest without calling the model or sending additional telemetry. It verifies the signature before trusting a version, location, or hash and installs only after explicit authorization.

The updater preserves company, email, credential, mode, hooks, and base configuration. It rejects modifications, downgrades, and assets that do not match the signed manifest.

Use of PragmAI and the decision to install, defer, test, or apply an update are the user's responsibility. The user must verify release authenticity and integrity, maintain backups, test compatibility, secure the device and credentials, and validate the result. No maintenance, support, update, notification, compatibility, or recovery obligation exists unless separately agreed in writing. See the repository `LICENSE` for the supplemental disclaimer and MPL 2.0 warranty and liability terms.

If an installation is revoked or compromised, a PragmAI administrator creates a new invitation and the employee repeats `pragmai setup`. Previous credentials are never recovered or redistributed. `pragmai uninstall` removes only managed changes, restores previous hooks, and keeps recoverable backups.

## Security boundary

Signatures and hashes protect the publication chain, but compromised hosting may make downloads unavailable, and a person or malware with administrative control of the computer can still alter local software or configuration. Those risks require device controls and cannot be solved by the connector alone.
