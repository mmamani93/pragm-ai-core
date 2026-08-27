# PragmAI Core

PragmAI Core is the auditable local component of PragmAI. It installs the Codex and Claude Code hooks, converts locally available technical metadata into a closed telemetry schema, removes content, and sends one aggregate event per human exchange.

This repository exists so employees, customers, and auditors can verify exactly what leaves a workstation. It does not contain the PragmAI backend, dashboard, credentials, metric evaluation, business interpretation, recommendations, or the logic used to decide possible improvements.

## Privacy boundary

PragmAI Core may send an employee-authorized email plus technical counters and closed categories. It never sends prompts, responses, transcripts, commands, arguments, tool output, file names, paths, URLs, session identifiers, or individual tool names.

Codex telemetry v5 can emit a closed numeric counterfactual for the current exchange. Telemetry v6 adds a deterministic sensitivity grid at the current compaction threshold, ±25,000 and ±50,000 tokens, plus the original limit. Both reconstruct the technical context trajectory transiently on the workstation and discard the source sequence. The grid also covers sessions without an observed compaction and makes no model calls. Only aggregate counters and labeled method/basis values leave the workstation.

See [the telemetry reference](docs/TELEMETRY.md) and [a synthetic complete event](examples/telemetry-event.json).

## Commands

On macOS, install the current release from the public Homebrew tap:

```text
brew install mmamani93/tap/pragmai
```

Windows and Linux artifacts are available from the versioned GitHub Release. WinGet remains unavailable until Microsoft accepts the catalog submission; do not present it as an active installation method before then.

After installation, the public interface is:

```text
pragmai setup
pragmai doctor
pragmai uninstall
```

`setup` asks for the employee-authorized email and requests a short-lived pairing. It prints only a public code, which the employee authorizes from the manually shared one-use invitation link. The hosted service then delivers an individual revocable credential directly to the executable. The temporary link may travel through a trusted chat, but no permanent credential appears in chat, URLs, or command arguments.

The local connector stores that credential only in its private user configuration and binds every event to the invited company and email. `doctor` performs local checks without reading company analytics or printing credentials. `uninstall` removes only PragmAI-managed changes and restores the captured pre-installation configuration.

## Build locally

The released executable includes its Python runtime; employees do not need Python installed. Python and PyInstaller are required only on a release machine:

```sh
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -p "test_*.py"
python scripts/build_standalone.py --clean
```

PyInstaller builds separately on each operating system. GitHub Actions produces macOS arm64, macOS x64, Windows x64, and Linux x64 artifacts from the same tagged source.

## Repository boundary

Public:

- local connector and installation lifecycle;
- exact outbound telemetry construction;
- closed taxonomies and privacy controls;
- tests, synthetic event, release verification key, and reproducible build workflow.

Private:

- ingestion operations and storage;
- company administration and credentials;
- dashboards and metric evaluation;
- economic interpretation, recommendations, and improvement decisions.

## License

PragmAI Core is licensed under the Mozilla Public License 2.0. The hosted PragmAI platform and private analysis components are not included in this license.
