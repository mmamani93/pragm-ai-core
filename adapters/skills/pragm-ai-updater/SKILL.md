---
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

For a check, report whether an update exists and do not install it. For an authorized update, report the previous and installed connector versions from the command output, then continue the user's original task. If the installed connector does not support these subcommands, explain that it is a legacy installation. Revoke its old credential, install the current official executable and enroll again with a new temporary invitation and `pragmai setup`.

## Package-manager installations

A package-manager executable and the private executable invoked by managed hooks are separate installation states. After an authorized Homebrew, WinGet, or equivalent package update, do not report completion from the package-manager version alone. Use the exact managed executable path previously emitted by the installer or already recorded in the managed hook; never guess it or inspect the private PragmAI configuration to find it.

Compare both executable versions. If they differ, treat this as a local synchronization issue, not as a reason to publish another package version. Preserve an adjacent recoverable backup of the old managed executable, atomically replace it with the already verified package-manager executable, and run `repair` from the managed executable. Do not run `setup`, reenroll the employee, or change company identity, authorized email, credential, clients, or optimization mode.

An update is complete only when the package-manager and managed executables report the same version, their SHA-256 hashes match, and `doctor` run from the managed executable passes every check. If the standalone `update` command directs the user back to the official installer, do not treat that message as successful synchronization.
