---
name: pragm-ai-updater
description: Update, repair, check, or change the optimization mode of an installed PragmAI connector when the user explicitly asks. Preserve the existing company identity, authorized employee, secret, and client configuration.
---

# PragmAI updater

Use the official `pragmai` executable as the update entrypoint. Do not inspect the private configuration to find it.

To check the official manifest without installing anything, run the installed connector with:

```sh
pragmai check-update
```

For an authorized Windows standalone update on 0.7.18 or later, run `pragmai update`. This authorization includes the official GitHub fallback: do not ask again when WinGet cannot find the package. The command selects the signed manifest version, tries WinGet download, falls back only when WinGet or the requested package/version is absent, verifies the GitHub SHA-256 and archive, and hands off replacement to a separate executable. The helper retains a backup, runs `repair` and `doctor`, and reports completion. A handoff message or exit code 0 alone is not success: wait for the helper result or check `pragmai update-status`; `pending` requires waiting, `failed` requires investigation. After success, ask the user to restart Claude Code.

Windows 0.7.17 and earlier need a one-time bootstrap because their standalone `update` cannot download binaries. If WinGet cannot find `PragmAI.PragmAI`, use the authorized fallback from https://github.com/mmamani93/pragm-ai-core/releases: select the stable version reported by `check-update`, download `pragmai-windows-x64.zip`, verify its SHA-256 against GitHub before extraction, and run `repair` and `doctor` with the new executable. Ask for permission only if the existing user request did not authorize downloading and executing the official fallback. Do not reenroll or read the private configuration.

On macOS or Linux, update through the official package or artifact, then run `pragmai repair` and `pragmai doctor`. Native automatic binary download is currently Windows-only.

To leave the A/B experiment and keep optimization enabled all the time, run:

```sh
pragmai set-optimization-mode always-on
```

To participate again in the three-day crossover A/B experiment, run:

```sh
pragmai set-optimization-mode experiment
```

Install an update or run `repair` only after the user explicitly asks to install or repair PragmAI, or explicitly authorizes it in response to the managed chat notice. The notice itself and a request to check do not authorize installation. Use `check-update` to compare against the official release; use `--version` only when the user asks for the locally installed version.

Change the optimization mode only after an explicit request from the user. `always-on` keeps telemetry active, applies the optimized managed configuration immediately and omits experiment identifiers from later events. `experiment` immediately applies the current deterministic assignment and alternates ON/OFF every three UTC days; later changes are performed by the existing Codex notification hook or Claude Code Stop hook after an exchange. Neither command needs the email or installation code again.

The updater accepts only the exact official HTTPS origin, requires a release manifest signed by the embedded PragmAI public key, verifies semantic version and release hashes, and rejects unsigned or modified manifests and downgrades. `repair` atomically synchronizes the official executable with the private copy used by hooks, retains a recoverable backup when it replaces that copy, preserves company identity, authorized employee, credential, mode and clients, and reapplies only managed settings. It does not update silently. Do not read, display, copy or transmit the private PragmAI configuration file.

For a check, report whether an update exists and do not install it. For an authorized update, report the previous and installed connector versions from the command output, then continue the user's original task. If the installed connector does not support these subcommands, explain that it is a legacy installation. Revoke its old credential, install the current official executable and enroll again with a new temporary invitation and `pragmai setup`.

## Package-manager installations

A package-manager executable and the private executable invoked by managed hooks are separate installation states. After an authorized Homebrew, WinGet, or equivalent package update, do not report completion from the package-manager version alone. Use the exact managed executable path previously emitted by the installer or already recorded in the managed hook; never guess it or inspect the private PragmAI configuration to find it.

After updating the official executable, run `pragmai repair`. It compares and synchronizes the private copy automatically. Do not run `setup`, reenroll the employee, or change company identity, authorized email, credential, clients or optimization mode.

An update is complete only when `pragmai doctor` confirms the configured version, private-copy integrity, package/hook synchronization and every client check. For Windows versions before 0.7.18, use the authorized one-time bootstrap above when `update` directs the user to the package or artifact; this message is not a completed update.
