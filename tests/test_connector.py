import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "adapters" / "pragm_ai_connector.py"
SPEC = importlib.util.spec_from_file_location("pragm_ai_connector", MODULE_PATH)
connector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(connector)


class ConnectorTests(unittest.TestCase):
    def test_windows_data_directory_uses_local_app_data(self):
        with mock.patch.dict(
            connector.os.environ, {"LOCALAPPDATA": r"C:\Users\employee\AppData\Local"}
        ):
            self.assertEqual(
                connector.platform_data_dir("nt"),
                Path(r"C:\Users\employee\AppData\Local") / "PragmAI",
            )

    def test_install_parser_accepts_model_supplied_chat_values(self):
        args = connector.parser().parse_args([
            "install",
            "--company-id", "InverArg",
            "--employee-email", "employee@example.com",
            "--consent-confirmed",
            "--ingest-secret-stdin",
            "--optimization-mode", "always-on",
        ])
        self.assertEqual(args.employee_email, "employee@example.com")
        self.assertTrue(args.consent_confirmed)
        self.assertTrue(args.ingest_secret_stdin)
        self.assertEqual(args.optimization_mode, "always-on")

    def test_setup_is_the_public_install_command(self):
        args = connector.parser().parse_args([
            "setup",
            "--company-id", "InverArg",
            "--employee-email", "employee@example.com",
            "--ingest-secret-stdin",
        ])
        self.assertEqual(args.command, "setup")
        self.assertEqual(args.company_id, "InverArg")

    def test_source_install_commands_keep_the_python_interpreter(self):
        self.assertEqual(
            connector.installed_command("codex-notify"),
            [connector.sys.executable, str(connector.INSTALL_FILE), "codex-notify"],
        )

    def test_windows_claude_hook_is_safe_for_the_posix_shell(self):
        command = connector.claude_hook_command(
            [r"C:\Users\Claude Code\AppData\Local\PragmAI\pragmai.exe", "claude-stop"],
            "nt",
        )
        self.assertEqual(
            connector.shlex.split(command),
            ["C:/Users/Claude Code/AppData/Local/PragmAI/pragmai.exe", "claude-stop"],
        )
        self.assertNotIn("\\", command)

    def test_doctor_validates_a_healthy_local_install_without_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_file = home / ".local" / "share" / "pragm-ai" / "pragm_ai_connector.py"
            config_file = home / ".config" / "pragm-ai" / "config.json"
            install_file.parent.mkdir(parents=True)
            install_file.write_text("connector", encoding="utf-8")
            install_file.chmod(0o700)
            config_file.parent.mkdir(parents=True)
            config_file.write_text(json.dumps({
                "endpoint": connector.DEFAULT_ENDPOINT,
                "ingest_secret": "0123456789abcdef",
                "company_id": "TestCompany",
                "employee_id": "employee@example.com",
                "fingerprint_key": "11" * 32,
                "installed_clients": ["codex"],
                "version": connector.VERSION,
                "connector_sha256": connector.hashlib.sha256(b"connector").hexdigest(),
            }), encoding="utf-8")
            codex = home / ".codex"
            codex.mkdir()
            codex.joinpath("config.toml").write_text(
                f'notify = {json.dumps([connector.sys.executable, str(install_file), "codex-notify"])}\n',
                encoding="utf-8",
            )
            codex.joinpath("AGENTS.md").write_text(connector.CODEX_RULES_BLOCK, encoding="utf-8")
            with (
                mock.patch.object(connector, "INSTALL_FILE", install_file),
                mock.patch.object(connector, "CONFIG_FILE", config_file),
                mock.patch.object(connector.Path, "home", return_value=home),
                mock.patch("sys.stdout", new_callable=io.StringIO) as output,
            ):
                self.assertEqual(connector.doctor(), 0)
            self.assertNotIn("0123456789abcdef", output.getvalue())
            self.assertIn("10/10 checks passed", output.getvalue())

    def test_https_calls_use_the_explicit_trusted_context(self):
        request = connector.Request("https://m-pragm-ai.vercel.app/api/health")
        sentinel = object()
        response = mock.MagicMock()
        with (
            mock.patch.object(connector, "trusted_tls_context", return_value=sentinel),
            mock.patch.object(connector, "urlopen", return_value=response) as opened,
        ):
            self.assertIs(connector.open_https(request, 12), response)
        opened.assert_called_once_with(request, timeout=12, context=sentinel)

    def test_repair_synchronizes_package_managed_standalone_before_reapplying_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "package" / "pragmai"
            target = root / "managed" / "pragmai"
            source.parent.mkdir()
            target.parent.mkdir()
            source.write_bytes(b"current executable")
            target.write_bytes(b"old executable")
            target.chmod(0o700)
            with (
                mock.patch.object(connector, "STANDALONE", True),
                mock.patch.object(connector, "INSTALL_FILE", target),
                mock.patch.object(connector, "current_artifact_path", return_value=source),
            ):
                retained = connector.synchronize_managed_executable()
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertIsNotNone(retained)
            self.assertEqual(retained.read_bytes(), b"old executable")

    def test_uninstall_restores_prior_codex_and_claude_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_file = home / ".local" / "share" / "pragm-ai" / "pragm_ai_connector.py"
            config_file = home / ".config" / "pragm-ai" / "config.json"
            skill_dir = home / ".codex" / "skills" / "pragm-ai-updater"
            install_file.parent.mkdir(parents=True)
            install_file.write_text("connector", encoding="utf-8")
            install_file.chmod(0o700)
            config = {
                "endpoint": connector.DEFAULT_ENDPOINT,
                "ingest_secret": "0123456789abcdef",
                "company_id": "TestCompany",
                "employee_id": "employee@example.com",
                "fingerprint_key": "11" * 32,
                "installed_clients": ["codex", "claude-code"],
                "baseline_codex": {key: None for key in connector.CODEX_OPTIMIZATION_KEYS},
                "baseline_codex_notify": ["original-notify"],
                "baseline_claude": {
                    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "75",
                    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "legacy",
                },
            }
            config_file.parent.mkdir(parents=True)
            config_file.write_text(json.dumps(config), encoding="utf-8")
            codex = home / ".codex"
            codex.mkdir(exist_ok=True)
            codex.joinpath("config.toml").write_text(
                f'notify = {json.dumps([connector.sys.executable, str(install_file), "codex-notify"])}\n'
                'model_auto_compact_token_limit = 100000\ncompact_prompt = "PragmAI"\n',
                encoding="utf-8",
            )
            codex.joinpath("AGENTS.md").write_text(
                "# Existing\n\n" + connector.CODEX_RULES_BLOCK + "\n", encoding="utf-8"
            )
            skill_dir.mkdir(parents=True)
            skill_dir.joinpath("SKILL.md").write_text("name: pragm-ai-updater\n", encoding="utf-8")
            claude = home / ".claude"
            claude.mkdir()
            other_hook = {"matcher": "", "hooks": [{"type": "command", "command": "other-hook"}]}
            pragmai_hook = {
                "matcher": "",
                "hooks": [{"type": "command", "command": f"{connector.sys.executable} {install_file} claude-stop"}],
            }
            claude.joinpath("settings.json").write_text(json.dumps({
                "hooks": {"Stop": [other_hook, pragmai_hook]},
                "env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "64"},
                "theme": "dark",
            }), encoding="utf-8")
            claude.joinpath("CLAUDE.md").write_text(
                "# Existing\n\n" + connector.CLAUDE_COMPACT_BLOCK + "\n", encoding="utf-8"
            )

            with (
                mock.patch.object(connector, "INSTALL_FILE", install_file),
                mock.patch.object(connector, "INSTALL_DIR", install_file.parent),
                mock.patch.object(connector, "CONFIG_FILE", config_file),
                mock.patch.object(connector, "UPDATER_SKILL_DIR", skill_dir),
                mock.patch.object(connector.Path, "home", return_value=home),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                self.assertEqual(connector.uninstall(), 0)

            codex_text = codex.joinpath("config.toml").read_text(encoding="utf-8")
            self.assertEqual(connector.top_level_json_value(codex_text, "notify"), ["original-notify"])
            self.assertNotIn("model_auto_compact_token_limit", codex_text)
            self.assertNotIn(connector.CODEX_RULES_BLOCK_START, codex.joinpath("AGENTS.md").read_text())
            claude_settings = json.loads(claude.joinpath("settings.json").read_text())
            self.assertEqual(claude_settings["hooks"]["Stop"], [other_hook])
            self.assertEqual(claude_settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"], "75")
            self.assertEqual(claude_settings["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "legacy")
            self.assertEqual(claude_settings["theme"], "dark")
            self.assertNotIn(connector.CLAUDE_COMPACT_BLOCK_START, claude.joinpath("CLAUDE.md").read_text())
            self.assertFalse(config_file.exists())
            self.assertFalse(install_file.exists())
            self.assertFalse(skill_dir.exists())

    def test_model_supplied_values_complete_install_without_user_terminal_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install_file = root / "installed" / "pragm_ai_connector.py"
            config_file = root / "config" / "config.json"
            args = connector.parser().parse_args([
                "install",
                "--company-id", "InverArg",
                "--employee-email", "employee@example.com",
                "--consent-confirmed",
                "--ingest-secret-stdin",
                "--client", "codex",
                "--optimization-mode", "always-on",
            ])
            with (
                mock.patch.object(connector, "INSTALL_DIR", install_file.parent),
                mock.patch.object(connector, "INSTALL_FILE", install_file),
                mock.patch.object(connector, "CONFIG_FILE", config_file),
                mock.patch.object(connector, "detect_clients", return_value=["codex"]),
                mock.patch.object(connector, "install_codex", return_value=[]),
                mock.patch.object(connector, "install_updater_skill", return_value=None),
                mock.patch.object(connector.sys, "stdin", io.StringIO("0123456789abcdef\n")),
                mock.patch("builtins.input", side_effect=AssertionError("unexpected input")),
            ):
                self.assertEqual(connector.install(args), 0)

            saved = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["company_id"], "InverArg")
            self.assertEqual(saved["employee_id"], "employee@example.com")
            self.assertEqual(saved["ingest_secret"], "0123456789abcdef")
            self.assertEqual(saved["optimization_mode"], "always_on")
            self.assertNotIn("active_experiment", saved)

    def test_secure_onboarding_uses_email_pairing_without_printing_secrets(self):
        responses = [
            (201, {
                "pairing_code": "ABCD-EFGH",
                "pairing_secret": "temporary-pairing-secret-0123456789",
                "poll_after_seconds": 1,
            }),
            (202, {"status": "pending", "poll_after_seconds": 1}),
            (200, {
                "status": "authorized",
                "company_id": "InverArg",
                "employee_email": "employee@example.com",
                "ingest_credential": "pi_permanent-credential-0123456789",
            }),
        ]
        with (
            mock.patch.object(connector, "onboarding_request", side_effect=responses) as request,
            mock.patch.object(connector.time, "sleep"),
            mock.patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = connector.enroll_installation(
                connector.DEFAULT_ENDPOINT, "employee@example.com", timeout_seconds=30
            )
        self.assertEqual(result, (
            "InverArg", "employee@example.com", "pi_permanent-credential-0123456789"
        ))
        self.assertIn("ABCD-EFGH", output.getvalue())
        self.assertNotIn("temporary-pairing-secret", output.getvalue())
        self.assertNotIn("permanent-credential", output.getvalue())
        self.assertEqual(request.call_args_list[0].args[1], "POST")
        self.assertEqual(request.call_args_list[-1].kwargs["secret"], "temporary-pairing-secret-0123456789")

    def test_setup_uses_the_credential_returned_by_secure_onboarding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install_file = root / "installed" / "pragm_ai_connector.py"
            config_file = root / "config" / "config.json"
            args = connector.parser().parse_args([
                "setup",
                "--employee-email", "employee@example.com",
                "--consent-confirmed",
                "--client", "codex",
            ])
            with (
                mock.patch.object(connector, "INSTALL_DIR", install_file.parent),
                mock.patch.object(connector, "INSTALL_FILE", install_file),
                mock.patch.object(connector, "CONFIG_FILE", config_file),
                mock.patch.object(connector, "detect_clients", return_value=["codex"]),
                mock.patch.object(connector, "install_codex", return_value=[]),
                mock.patch.object(connector, "install_updater_skill", return_value=None),
                mock.patch.object(connector, "enroll_installation", return_value=(
                    "InverArg", "employee@example.com", "pi_permanent-credential-0123456789"
                )),
                mock.patch("builtins.input", side_effect=AssertionError("unexpected input")),
            ):
                self.assertEqual(connector.install(args), 0)
            saved = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["company_id"], "InverArg")
            self.assertEqual(saved["employee_id"], "employee@example.com")
            self.assertEqual(saved["ingest_secret"], "pi_permanent-credential-0123456789")

    def test_secure_setup_rejects_private_company_argument_before_pairing(self):
        args = connector.parser().parse_args([
            "setup",
            "--company-id", "InverArg",
            "--employee-email", "employee@example.com",
            "--consent-confirmed",
        ])
        with (
            mock.patch.object(connector, "detect_clients", return_value=["codex"]),
            mock.patch.object(
                connector, "enroll_installation", side_effect=AssertionError("pairing must not start")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "private recovery flow"):
                connector.install(args)

    def test_codex_config_update_preserves_sections_and_replaces_multiline_prompt(self):
        original = '''model = "gpt-test"
compact_prompt = """
old prompt
with several lines
"""
notify = ["wrapper", "--previous-notify", "[\\"old-hook\\"]"]

[project]
notify = ["project-specific"]
'''
        previous = connector.top_level_json_value(original, "notify")
        self.assertEqual(previous, ["wrapper", "--previous-notify", '["old-hook"]'])

        updated = connector.set_toml_values(original, {
            "compact_prompt": "new prompt",
            "model_auto_compact_token_limit": 100_000,
        })
        self.assertIn('compact_prompt = "new prompt"', updated)
        self.assertNotIn("old prompt", updated)
        self.assertIn('[project]\nnotify = ["project-specific"]', updated)
        self.assertEqual(updated.count('compact_prompt ='), 1)

    def setUp(self):
        self.config = {
            "company_id": "pilot-mauro",
            "employee_id": "mauro@example.com",
            "fingerprint_key": "11" * 32,
            "billing_mode": "subscription",
            "optimization_mode": "experiment",
            "active_experiment": {
                "experiment_id": connector.EXPERIMENT_ID,
                "experiment_unit_id": "eu_" + "aa" * 16,
                "experiment_period": "B6895",
                "optimization_enabled": True,
            },
        }

    def test_three_day_experiment_is_stable_private_balanced_and_alternating(self):
        moment = datetime(2026, 8, 25, tzinfo=timezone.utc)
        first = connector.experiment_assignment(self.config, moment)
        second = connector.experiment_assignment(self.config, moment)
        following = connector.experiment_assignment(self.config, moment.replace(day=28))
        next_cycle = connector.experiment_assignment(self.config, moment.replace(day=31))
        self.assertEqual(first, second)
        self.assertNotEqual(first["experiment_unit_id"], following["experiment_unit_id"])
        self.assertNotEqual(first["optimization_enabled"], following["optimization_enabled"])
        self.assertEqual(first["optimization_enabled"], next_cycle["optimization_enabled"])
        self.assertRegex(first["experiment_unit_id"], r"^eu_[a-f0-9]{32}$")
        self.assertNotIn(self.config["employee_id"], json.dumps(first))

        enabled = 0
        for index in range(200):
            candidate = dict(self.config, employee_id=f"employee-{index}@example.com")
            enabled += connector.experiment_assignment(candidate, moment)["optimization_enabled"]
        self.assertGreater(enabled, 70)
        self.assertLess(enabled, 130)

    def test_always_on_mode_has_no_experiment_identity(self):
        state = connector.active_optimization_state({
            **self.config,
            "optimization_mode": "always_on",
        })
        self.assertEqual(state, {"optimization_enabled": True})

    def test_always_on_mode_never_runs_experiment_rotation(self):
        config = {**self.config, "optimization_mode": "always_on"}
        with mock.patch.object(connector, "experiment_assignment") as assignment:
            connector.periodic_experiment_check(config)
        assignment.assert_not_called()

    def test_private_fingerprint_is_stable_and_contains_no_source_text(self):
        first = connector.recurrence_key(
            "Revisá /Users/mauro/secret.txt en https://example.com para 27 clientes",
            self.config["fingerprint_key"],
        )
        second = connector.recurrence_key(
            "Revisá /tmp/other.txt en https://other.example para 99 clientes",
            self.config["fingerprint_key"],
        )
        self.assertEqual(first, second)
        self.assertRegex(first, r"^rt_[a-f0-9]{32}$")
        self.assertNotIn("revisa", first)

    def test_classifier_uses_fixed_taxonomy_and_coarse_tool_families(self):
        result = connector.classify("Corregí un bug del repositorio", ["shell", "filesystem_write"])
        self.assertEqual(result["work_domain"], "software")
        self.assertEqual(result["workflow_pattern"], "code_change")
        self.assertNotIn("automation_score", result)
        self.assertNotIn("automation_confidence", result)
        self.assertNotIn("tool_categories", result)
        self.assertEqual(connector.tool_category("apply_patch"), "filesystem_write")
        self.assertEqual(connector.tool_category("exec_command"), "shell_general")
        self.assertEqual(connector.tool_category("exec_command", {"cmd": "rg --files"}), "shell_file_inspection")
        self.assertEqual(connector.tool_category("exec_command", {"cmd": "npm test"}), "shell_testing")
        self.assertEqual(connector.tool_category("exec_command", {"cmd": "git status"}), "shell_version_control")
        self.assertEqual(connector.classify("Hola", [])["workflow_pattern"], "general_assistance")

    def test_usage_aggregation_reports_calls_and_context_distribution(self):
        result = connector.aggregate_usage([
            {"input_tokens": 90_000, "cached_input_tokens": 70_000, "output_tokens": 2_000, "total_tokens": 92_000},
            {"input_tokens": 120_000, "cached_input_tokens": 80_000, "output_tokens": 4_000, "reasoning_output_tokens": 1_000},
        ])
        self.assertEqual(result["model_calls"], 2)
        self.assertEqual(result["tokens_input"], 210_000)
        self.assertEqual(result["max_input_tokens_per_call"], 120_000)
        self.assertEqual(result["calls_over_compaction_threshold"], 1)
        self.assertEqual(result["tokens_cache_read"], 150_000)

    def test_codex_produces_one_content_free_event_per_user_exchange(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "rollout-thread-12345678.jsonl"
            records = [
                {"timestamp": "2026-08-24T12:00:00Z", "type": "turn_context", "payload": {"turn_id": "turn-abc", "model": "gpt-5.6-sol", "effort": "high"}},
                {"timestamp": "2026-08-24T12:00:01Z", "type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "arguments": "TOP SECRET"}},
                {"timestamp": "2026-08-24T12:00:01Z", "type": "response_item", "payload": {"type": "function_call_output", "output": "PRIVATE RESULT"}},
                {"timestamp": "2026-08-24T12:00:02Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 60_000, "cached_input_tokens": 50_000, "output_tokens": 2_000, "total_tokens": 62_000}}}},
                {"timestamp": "2026-08-24T12:00:03Z", "type": "compacted", "payload": {}},
                {"timestamp": "2026-08-24T12:00:04Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 40_000, "cached_input_tokens": 30_000, "output_tokens": 1_000, "total_tokens": 41_000}}}},
                {"timestamp": "2026-08-24T12:00:05Z", "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-abc"}},
            ]
            session.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            payload = {
                "type": "agent-turn-complete",
                "thread-id": "thread-12345678",
                "turn-id": "turn-abc",
                "cwd": "/Users/mauro/private-client",
                "input-messages": ["Arreglá el código del cliente ACME en https://private.example"],
                "last-assistant-message": "Contenido privado de la respuesta",
            }
            event = connector.codex_event(payload, self.config, root)

        self.assertEqual(event["model_calls"], 2)
        self.assertEqual(event["tool_category_counts"], {"shell_general": 1})
        self.assertEqual(event["tool_result_characters"], len("PRIVATE RESULT"))
        self.assertEqual(event["post_tool_model_calls"], 1)
        self.assertEqual(event["continuation_model_calls"], 1)
        self.assertEqual(event["compaction_measurements"][0]["model_calls_after"], 1)
        self.assertEqual(event["compaction_measurements"][0]["tokens_avoided_estimated"], 20_000)
        self.assertEqual(event["config_profile"], "smart_100k")
        self.assertEqual(event["compaction_threshold_tokens"], 127_000)
        self.assertEqual(event["compaction_scope"], "body_after_prefix")
        self.assertEqual(event["telemetry_version"], 6)
        self.assertEqual(event["experiment_id"], connector.EXPERIMENT_ID)
        self.assertEqual(event["experiment_unit_id"], "eu_" + "aa" * 16)
        self.assertTrue(event["optimization_enabled"])
        for redundant in (
            "event_kind", "repeatability", "tokens_total", "tool_calls",
            "classified_tool_calls", "tool_categories", "compactions_count",
            "avg_input_tokens_per_call", "configured_compaction_scope",
        ):
            self.assertNotIn(redundant, event)
        serialized = json.dumps(event)
        for sensitive in ("ACME", "private.example", "private-client", "TOP SECRET", "PRIVATE RESULT", "Contenido privado"):
            self.assertNotIn(sensitive, serialized)
        for forbidden_key in ("prompt", "response", "content", "path", "url", "tool_names"):
            self.assertNotIn(f'"{forbidden_key}"', serialized)

    def test_codex_deduplicates_compaction_markers_and_classifies_nested_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "rollout-thread-12345678.jsonl"
            records = [
                {"timestamp": "2026-08-24T12:00:00Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 120_000, "cached_input_tokens": 100_000, "output_tokens": 2_000}}}},
                {"timestamp": "2026-08-24T12:00:00Z", "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "previous-turn"}},
                {"timestamp": "2026-08-24T12:00:01Z", "type": "compacted", "payload": {}},
                {"timestamp": "2026-08-24T12:00:01Z", "type": "event_msg", "payload": {"type": "context_compacted"}},
                {"timestamp": "2026-08-24T12:00:02Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 10_000}}}},
                {"timestamp": "2026-08-24T12:00:03Z", "type": "turn_context", "payload": {"turn_id": "turn-abc", "model": "gpt-5.6-sol"}},
                {"timestamp": "2026-08-24T12:00:04Z", "type": "response_item", "payload": {"type": "function_call", "name": "functions.exec", "arguments": "await tools.web__run({}); await tools.apply_patch('private')"}},
                {"timestamp": "2026-08-24T12:00:05Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 30_000, "cached_input_tokens": 20_000, "output_tokens": 1_000}}}},
                {"timestamp": "2026-08-24T12:00:06Z", "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-abc"}},
            ]
            session.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
            payload = {"thread-id": "thread-12345678", "turn-id": "turn-abc", "input-messages": ["Investigá y corregí"]}
            event = connector.codex_event(payload, self.config, root)

        self.assertEqual(event["model_calls"], 1)
        self.assertEqual(event["tool_category_counts"], {"filesystem_write": 1, "web": 1})
        measurement = event["compaction_measurements"][0]
        self.assertTrue(measurement["before_exchange"])
        self.assertEqual(measurement["compacted_context_tokens"], 10_000)
        self.assertEqual(measurement["model_calls_after"], 1)
        self.assertEqual(measurement["tokens_avoided_estimated"], 90_000)
        self.assertNotIn("private", json.dumps(event))

    def test_codex_replays_the_full_session_against_the_original_limit(self):
        def usage(value, cached=None):
            return {
                "type": "event_msg",
                "payload": {"type": "token_count", "info": {"last_token_usage": {
                    "input_tokens": value,
                    "cached_input_tokens": value if cached is None else cached,
                    "output_tokens": 1,
                }}},
            }

        records = [
            usage(25_000), usage(125_000), {"type": "compacted", "payload": {}},
            usage(25_000), usage(125_000), {"type": "compacted", "payload": {}},
            {"type": "turn_context", "payload": {"turn_id": "current"}},
            usage(25_000), usage(130_000, 120_000), usage(135_000, 125_000),
        ]
        config = {
            **self.config,
            "optimization_mode": "always_on",
            "baseline_codex": {
                "model_auto_compact_token_limit": 230_000,
                "model_auto_compact_token_limit_scope": "total",
                "compact_prompt": None,
            },
        }
        result = connector.codex_compaction_counterfactual(
            records, len(records) - 3, len(records) - 1, config
        )
        self.assertEqual(result["original_threshold_tokens"], 230_000)
        self.assertEqual(result["checkpoint_tokens_estimated"], 25_000)
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual(result["actual_model_input_tokens"], 290_000)
        self.assertEqual(result["original_model_input_tokens_estimated"], 490_000)
        self.assertEqual(result["original_compactions_estimated"], 1)
        self.assertEqual(result["original_compaction_input_tokens_estimated"], 230_000)
        self.assertNotIn("session_id", json.dumps(result))

    def test_codex_simulates_threshold_grid_without_observed_compaction(self):
        def usage(value):
            return {
                "type": "event_msg",
                "payload": {"type": "token_count", "info": {"last_token_usage": {
                    "input_tokens": value,
                    "cached_input_tokens": value,
                    "output_tokens": 1,
                }}},
            }

        records = [
            usage(20_000),
            {"type": "turn_context", "payload": {"turn_id": "current"}},
            usage(70_000), usage(90_000),
        ]
        config = {
            **self.config,
            "optimization_mode": "always_on",
            "baseline_codex": {
                "model_auto_compact_token_limit": 230_000,
                "model_auto_compact_token_limit_scope": "total",
                "compact_prompt": None,
            },
        }
        result = connector.codex_compaction_sensitivity(records, 1, 3, config)
        self.assertEqual(result["checkpoint_tokens_estimated"], 10_000)
        self.assertEqual(result["checkpoint_basis"], "profile_checkpoint_target")
        self.assertEqual(result["actual_model_input_tokens"], 160_000)
        self.assertEqual(len(result["scenarios"]), 6)
        minus_50k = next(
            item for item in result["scenarios"]
            if item["threshold_offset_tokens"] == -50_000
        )
        self.assertEqual(minus_50k["threshold_tokens"], 77_000)
        self.assertEqual(minus_50k["compactions_estimated"], 1)
        self.assertEqual(minus_50k["model_input_tokens_estimated"], 100_000)
        current = next(
            item for item in result["scenarios"]
            if item["threshold_offset_tokens"] == 0
        )
        self.assertEqual(current["compactions_estimated"], 0)
        self.assertEqual(current["model_input_tokens_estimated"], 160_000)
        self.assertTrue(next(item for item in result["scenarios"] if item["is_original_limit"]))
        self.assertNotIn("session_id", json.dumps(result))

    def test_codex_discards_internal_review_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "rollout-thread-12345678.jsonl"
            records = [
                {"timestamp": "2026-08-24T12:00:00Z", "type": "turn_context", "payload": {"turn_id": "review-turn", "model": "codex-auto-review"}},
                {"timestamp": "2026-08-24T12:00:01Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 100, "output_tokens": 10}}}},
            ]
            session.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
            payload = {"thread-id": "thread-12345678", "turn-id": "review-turn", "input-messages": ["review"]}
            self.assertIsNone(connector.codex_event(payload, self.config, root))

    def test_claude_code_aggregates_transcript_without_uploading_content(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "claude.jsonl"
            records = [
                {"type": "user", "uuid": "user-1", "timestamp": "2026-08-24T13:00:00Z", "message": {"content": "Analizá el contrato secreto de ACME"}},
                {"type": "assistant", "timestamp": "2026-08-24T13:00:01Z", "message": {"model": "claude-sonnet-5", "usage": {"input_tokens": 100, "cache_read_input_tokens": 50, "cache_creation_input_tokens": 25, "output_tokens": 20}, "content": [{"type": "tool_use", "name": "Read", "input": {"path": "/secret"}}]}},
                {"type": "user", "timestamp": "2026-08-24T13:00:02Z", "message": {"content": [{"type": "tool_result", "content": "raw secret"}]}},
                {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-08-24T13:00:02Z", "compactMetadata": {"preTokens": 99999}},
                {"type": "assistant", "timestamp": "2026-08-24T13:00:03Z", "message": {"model": "claude-sonnet-5", "usage": {"input_tokens": 120, "cache_read_input_tokens": 80, "output_tokens": 30}, "content": [{"type": "text", "text": "private answer"}]}},
            ]
            transcript.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
            event = connector.claude_event({"session_id": "session-secret", "transcript_path": str(transcript)}, self.config)

        self.assertEqual(event["client"], "claude-code")
        self.assertEqual(event["model_calls"], 2)
        self.assertEqual(event["tokens_input"], 375)
        self.assertEqual(event["tool_category_counts"], {"filesystem_read": 1})
        self.assertEqual(event["tool_result_characters"], len("raw secret"))
        self.assertEqual(event["config_profile"], "smart_100k")
        self.assertEqual(event["compaction_threshold_tokens"], 127_000)
        self.assertEqual(event["compaction_scope"], "approximate_total")
        self.assertEqual(event["compaction_measurements"][0]["model_calls_after"], 1)
        serialized = json.dumps(event)
        for sensitive in ("ACME", "contrato secreto", "/secret", "raw secret", "private answer", "session-secret"):
            self.assertNotIn(sensitive, serialized)

    def test_toml_update_only_replaces_top_level_settings(self):
        original = 'notify = ["old"]\n[project]\nnotify = ["nested"]\n'
        updated = connector.set_toml_values(original, {"notify": ["new"], "model_auto_compact_token_limit": 100000})
        self.assertIn('notify = ["new"]', updated)
        self.assertIn('notify = ["nested"]', updated)
        self.assertEqual(updated.count("model_auto_compact_token_limit"), 1)

    def test_managed_claude_compaction_block_is_idempotent(self):
        first = connector.replace_managed_block(
            "# Existing rules\n",
            connector.CLAUDE_COMPACT_BLOCK,
            connector.CLAUDE_COMPACT_BLOCK_START,
            connector.CLAUDE_COMPACT_BLOCK_END,
        )
        second = connector.replace_managed_block(
            first,
            connector.CLAUDE_COMPACT_BLOCK,
            connector.CLAUDE_COMPACT_BLOCK_START,
            connector.CLAUDE_COMPACT_BLOCK_END,
        )
        self.assertEqual(first, second)
        self.assertIn("# Existing rules", second)
        self.assertEqual(second.count(connector.CLAUDE_COMPACT_BLOCK_START), 1)
        self.assertIn("10,000 tokens", second)

    def test_client_detection_lists_available_clients(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".claude").mkdir()
            with mock.patch.object(connector.shutil, "which", return_value=None):
                self.assertEqual(connector.detect_clients(home), ["claude-code"])
                self.assertEqual(connector.detect_client(home), "claude-code")
                (home / ".codex").mkdir()
                self.assertEqual(connector.detect_clients(home), ["codex", "claude-code"])
                self.assertEqual(connector.detect_client(home), "both")

    def test_setup_stops_before_pairing_when_no_client_is_installed(self):
        args = connector.parser().parse_args(["setup"])
        with (
            mock.patch.object(connector, "detect_clients", return_value=[]),
            mock.patch.object(
                connector, "enroll_installation", side_effect=AssertionError("pairing must not start")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "No se detectó Codex ni Claude Code"):
                connector.install(args)

    def test_setup_prompts_for_one_of_the_detected_clients(self):
        with (
            mock.patch.object(connector, "detect_clients", return_value=["codex", "claude-code"]),
            mock.patch("builtins.input", side_effect=["invalid", "2"]),
            mock.patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(connector.select_setup_clients("auto"), ["claude-code"])
        self.assertIn("Codex", output.getvalue())
        self.assertIn("Claude Code", output.getvalue())
        self.assertIn("Elegí 1, 2 o 3", output.getvalue())

    def test_explicit_setup_client_must_be_installed(self):
        with mock.patch.object(connector, "detect_clients", return_value=["claude-code"]):
            with self.assertRaisesRegex(RuntimeError, "Codex.*no fue detectado"):
                connector.select_setup_clients("codex")

    def test_reinstall_source_can_already_be_the_installed_connector(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connector.py"
            path.write_text("unchanged", encoding="utf-8")
            self.assertEqual(path.resolve(), path.resolve())
            with mock.patch.object(connector, "INSTALL_FILE", path):
                source_file = path.resolve()
                installed_file = connector.INSTALL_FILE.resolve()
                if source_file != installed_file:
                    connector.shutil.copy2(source_file, connector.INSTALL_FILE)
            self.assertEqual(path.read_text(encoding="utf-8"), "unchanged")

    def test_updater_accepts_only_the_official_https_origin(self):
        self.assertTrue(connector.trusted_update_url(
            "https://m-pragm-ai.vercel.app/downloads/pragm_ai_connector.py"
        ))
        self.assertFalse(connector.trusted_update_url(
            "http://m-pragm-ai.vercel.app/downloads/pragm_ai_connector.py"
        ))
        self.assertFalse(connector.trusted_update_url(
            "https://m-pragm-ai.vercel.app.evil.example/pragm_ai_connector.py"
        ))
        self.assertFalse(connector.trusted_update_url(
            "https://user@m-pragm-ai.vercel.app/pragm_ai_connector.py"
        ))
        self.assertFalse(connector.trusted_update_url(
            "https://m-pragm-ai.vercel.app/downloads/0.6.4/pragm_ai_connector.py?replace=1"
        ))

    def test_release_manifest_signature_rejects_any_modification(self):
        manifest_path = MODULE_PATH.parents[1] / "public" / "pragm-ai-update.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        connector.verify_manifest_signature(manifest)
        self.assertIn("instructions", manifest)

        tampered = json.loads(json.dumps(manifest))
        tampered["version"] = "99.0.0"
        with self.assertRaisesRegex(RuntimeError, "signature"):
            connector.verify_manifest_signature(tampered)
        unsigned = dict(manifest)
        unsigned.pop("signature")
        with self.assertRaisesRegex(RuntimeError, "not signed"):
            connector.verify_manifest_signature(unsigned)

    def test_release_manifest_requires_exact_immutable_asset_paths(self):
        manifest_path = MODULE_PATH.parents[1] / "public" / "pragm-ai-update.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with mock.patch.object(
            connector, "fetch_bytes", return_value=json.dumps(manifest).encode()
        ):
            self.assertEqual(connector.fetch_update_manifest(), manifest)

        wrong_path = json.loads(json.dumps(manifest))
        wrong_path["connector"]["url"] = wrong_path["connector"]["url"].replace(
            f"/{manifest['version']}/", "/other/"
        )
        with (
            mock.patch.object(
                connector, "fetch_bytes", return_value=json.dumps(wrong_path).encode()
            ),
            mock.patch.object(connector, "verify_manifest_signature"),
            self.assertRaisesRegex(RuntimeError, "untrusted URL"),
        ):
            connector.fetch_update_manifest()

    def test_updater_skill_install_is_bounded_and_uses_expected_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "pragm-ai-updater"
            skill = b"---\nname: pragm-ai-updater\ndescription: Test updater.\n---\n"
            with mock.patch.object(connector, "UPDATER_SKILL_DIR", target):
                installed = connector.install_updater_skill(skill)
            self.assertEqual(installed, target / "SKILL.md")
            self.assertEqual((target / "SKILL.md").read_bytes(), skill)

            with mock.patch.object(connector, "UPDATER_SKILL_DIR", target):
                with self.assertRaises(RuntimeError):
                    connector.install_updater_skill(b"not a skill")

    def test_downloaded_connector_embeds_the_exact_updater_skill(self):
        skill_path = MODULE_PATH.parent / "skills" / "pragm-ai-updater" / "SKILL.md"
        self.assertEqual(connector.EMBEDDED_UPDATER_SKILL, skill_path.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "installed-skill"
            missing_package = Path(directory) / "missing-package"
            with (
                mock.patch.object(connector, "UPDATER_SKILL_DIR", target),
                mock.patch.object(connector, "PACKAGED_SKILL_DIR", missing_package),
            ):
                connector.install_updater_skill()
            self.assertEqual((target / "SKILL.md").read_bytes(), skill_path.read_bytes())

    def test_codex_install_preserves_global_rules_and_adds_managed_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            (codex_dir / "config.toml").write_text('model = "gpt-test"\n', encoding="utf-8")
            (codex_dir / "AGENTS.md").write_text("# Existing global rule\n", encoding="utf-8")
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_codex({})

            instructions = (codex_dir / "AGENTS.md").read_text(encoding="utf-8")
            codex_config = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn("# Existing global rule", instructions)
            self.assertIn(connector.CODEX_RULES_BLOCK_START, instructions)
            self.assertIn("Never include prompts", instructions)
            self.assertIn(json.dumps(connector.sys.executable), codex_config)

    def test_codex_reinstall_keeps_the_original_notify_for_uninstall(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            original_notify = ["original-hook", "--quiet"]
            (codex_dir / "config.toml").write_text(
                f"notify = {json.dumps(original_notify)}\n", encoding="utf-8"
            )
            first_config = {}
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_codex(first_config, make_backup=False)
                second_config = {
                    "previous_pragmai_version": connector.VERSION,
                    "baseline_codex": first_config["baseline_codex"],
                    "baseline_codex_notify": first_config["baseline_codex_notify"],
                    "chained_notify": first_config["chained_notify"],
                }
                connector.install_codex(second_config, make_backup=False)
                connector.restore_codex(second_config)

            restored = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertEqual(connector.top_level_json_value(restored, "notify"), original_notify)

    def test_codex_experiment_off_restores_the_pre_install_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            original = (
                'model_auto_compact_token_limit = 155000\n'
                'model_auto_compact_token_limit_scope = "total"\n'
                'compact_prompt = "original checkpoint"\n'
            )
            (codex_dir / "config.toml").write_text(original, encoding="utf-8")
            config = {}
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_codex(config, True, make_backup=False)
                connector.install_codex(config, False, make_backup=False)
            restored = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn("155000", restored)
            self.assertIn('model_auto_compact_token_limit_scope = "total"', restored)
            self.assertIn('compact_prompt = "original checkpoint"', restored)
            instructions = (codex_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(connector.PRAGMAI_CORE_RULES, instructions)
            self.assertNotIn(connector.PRAGMAI_OPTIMIZATION_RULES, instructions)

    def test_codex_install_uses_an_existing_global_override(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            (codex_dir / "config.toml").write_text('', encoding="utf-8")
            (codex_dir / "AGENTS.md").write_text("# Regular rules\n", encoding="utf-8")
            override = codex_dir / "AGENTS.override.md"
            override.write_text("# Active override\n", encoding="utf-8")
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_codex({})

            self.assertEqual((codex_dir / "AGENTS.md").read_text(encoding="utf-8"), "# Regular rules\n")
            instructions = override.read_text(encoding="utf-8")
            self.assertIn("# Active override", instructions)
            self.assertIn(connector.CODEX_RULES_BLOCK_START, instructions)

    def test_update_availability_only_reports_a_newer_version(self):
        major, minor, patch = connector.version_tuple(connector.VERSION)
        newer_version = f"{major}.{minor}.{patch + 1}"
        with mock.patch.object(connector, "fetch_update_manifest", return_value={"version": newer_version}):
            self.assertEqual(connector.update_availability(), newer_version)
        with mock.patch.object(connector, "fetch_update_manifest", return_value={"version": connector.VERSION}):
            self.assertIsNone(connector.update_availability())

    def test_update_notice_is_written_to_managed_chat_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".codex").mkdir()
            (home / ".claude").mkdir()
            (home / ".codex" / "AGENTS.md").write_text("# Existing Codex rule\n", encoding="utf-8")
            (home / ".claude" / "CLAUDE.md").write_text("# Existing Claude rule\n", encoding="utf-8")
            config = {**self.config, "installed_clients": ["codex", "claude-code"]}
            with mock.patch.object(connector.Path, "home", return_value=home):
                self.assertEqual(connector.write_chat_update_notice("0.5.4", config), 2)

            codex = (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            claude = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            for text in (codex, claude):
                self.assertIn("0.5.4 is available", text)
                self.assertIn("ask whether they authorize", text)
            self.assertIn("# Existing Codex rule", codex)
            self.assertIn("# Existing Claude rule", claude)

    def test_periodic_update_check_notifies_once_per_version(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config = dict(self.config)
            with (
                mock.patch.object(connector, "CONFIG_FILE", config_path),
                mock.patch.object(connector, "update_availability", return_value="0.5.4") as availability,
                mock.patch.object(connector, "write_chat_update_notice", return_value=1) as notice,
            ):
                connector.periodic_update_check(config, now=100_000)
                connector.periodic_update_check(config, now=100_001)

            availability.assert_called_once_with(timeout=3)
            notice.assert_called_once_with("0.5.4", config)
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["last_update_check_at"], 100_000)
            self.assertEqual(saved["last_update_notice_version"], "0.5.4")

    def test_claude_install_configures_official_auto_compaction(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            claude_dir = home / ".claude"
            claude_dir.mkdir()
            (claude_dir / "settings.json").write_text('{"env":{"EXISTING":"kept"}}\n', encoding="utf-8")
            (claude_dir / "CLAUDE.md").write_text("# Existing rules\n", encoding="utf-8")
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_claude()

            settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["env"]["EXISTING"], "kept")
            hook_command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn(str(connector.INSTALL_FILE).replace("\\", "/"), hook_command)
            self.assertIn(str(connector.sys.executable).replace("\\", "/"), hook_command)
            self.assertNotIn("CLAUDE_CODE_AUTO_COMPACT_WINDOW", settings["env"])
            self.assertEqual(settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"], "64")
            self.assertEqual(len(settings["hooks"]["Stop"]), 1)
            instructions = (claude_dir / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("# Existing rules", instructions)
            self.assertIn("10,000 tokens", instructions)

    def test_claude_experiment_off_restores_the_pre_install_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            claude_dir = home / ".claude"
            claude_dir.mkdir()
            (claude_dir / "settings.json").write_text(
                '{"env":{"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE":"80"}}\n', encoding="utf-8"
            )
            config = {}
            with mock.patch.object(connector.Path, "home", return_value=home):
                connector.install_claude(config, True, make_backup=False)
                connector.install_claude(config, False, make_backup=False)
            settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"], "80")
            instructions = (claude_dir / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn(connector.PRAGMAI_CORE_RULES, instructions)
            self.assertNotIn("PragmAI compact instructions", instructions)


if __name__ == "__main__":
    unittest.main()
