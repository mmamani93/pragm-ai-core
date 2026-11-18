import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('connector_native', Path(__file__).parents[1] / 'adapters/pragm_ai_connector.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class NativeSignalsTests(unittest.TestCase):
    def setUp(self):
        self.config = {'company_id': 'TestCompany', 'employee_id': 'employee@example.com',
                       'optimization_mode': 'always_on', 'fingerprint_key': '11' * 32}

    def test_hook_never_transmits_native_content_or_identifiers(self):
        payload = {'hook_event_name':'PostCompact','trigger':'auto',
                   'session_id':'PRIVATE_SENTINEL','transcript_path':'PRIVATE_SENTINEL',
                   'compact_summary':'PRIVATE_SENTINEL','cwd':'PRIVATE_SENTINEL'}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c.Path,'home',return_value=Path(d)):
            signal = c.native_signal(payload,'claude-code',self.config)
        self.assertEqual(signal['kind'],'compaction_complete')
        self.assertEqual(signal['categories'],{'trigger':'auto'})
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(signal))

    def test_snapshot_preserves_absence_and_separates_model_window_from_config(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c.Path,'home',return_value=Path(d)):
            home = Path(d); (home/'.claude').mkdir()
            (home/'.claude/settings.json').write_text(json.dumps({'env':{'CLAUDE_CODE_AUTO_COMPACT_WINDOW':'127000'}}))
            p = {'hook_event_name':'StatusLine','context_window':{'context_window_size':1000000,'current_usage':None},
                 'fast_mode':False,'prompt_cache':{'requests':10,'misses':2,'last_miss_cause':{'causes':['tools_changed']}}}
            s = c.native_signal(p,'claude-code',self.config)
            self.assertEqual(s['metrics']['context_window_tokens'],1000000)
            self.assertEqual(s['metrics']['configured_window_tokens'],127000)
            self.assertNotIn('context_input_tokens',s['metrics'])
            self.assertEqual(s['categories']['speed'],'normal')
            self.assertEqual(s['categories']['cache_cause'],'tools_changed')

    def test_failed_request_does_not_invent_tokens(self):
        s = c.native_signal({'hook_event_name':'PostModelRequest','status':'failed','error':'PRIVATE_SENTINEL',
                             'token_usage':None},'codex',self.config)
        self.assertEqual(s['metrics'],{})
        self.assertEqual(s['categories'],{'status':'failed'})
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(s))

    def test_unknown_categories_and_malformed_metrics_cannot_leak(self):
        s = c.make_native_signal('codex','model_request',
            {'input_tokens':True,'output_tokens':-1,'secret':123,'duration_ms':3.4},
            {'effort':'PRIVATE_SENTINEL','error_category':'PRIVATE_SENTINEL','secret':'PRIVATE_SENTINEL'},self.config)
        self.assertEqual(s['metrics'],{})
        self.assertEqual(s['categories'],{'error_category':'other'})

    def test_on_off_restores_both_settings_and_preserves_statusline_and_hooks(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c.Path,'home',return_value=Path(d)):
            home = Path(d); (home/'.claude').mkdir()
            old = {'type':'command','command':'existing-status'}
            hook = {'hooks':[{'type':'command','command':'existing-hook'}]}
            path = home/'.claude/settings.json'
            path.write_text(json.dumps({'env':{'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE':'80','CLAUDE_CODE_AUTO_COMPACT_WINDOW':'300000'},
                'statusLine':old,'hooks':{'PreCompact':[hook]}}))
            config = dict(self.config)
            c.install_claude(config,True,False)
            c.install_claude(config,True,False)
            current = json.loads(path.read_text())
            self.assertEqual(current['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW'],'127000')
            self.assertNotIn('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE',current['env'])
            self.assertEqual(len(current['hooks']['PreCompact']),2)
            self.assertEqual(config['baseline_claude_statusline'],old)
            c.install_claude(config,False,False)
            current = json.loads(path.read_text())
            self.assertEqual(current['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW'],'300000')
            self.assertEqual(current['env']['CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'],'80')
            self.assertEqual(current['hooks']['PreCompact'][0],hook)

    def test_native_codex_hooks_do_not_erase_other_handlers(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c.Path,'home',return_value=Path(d)):
            home=Path(d);(home/'.codex').mkdir()
            path=home/'.codex/hooks.json'
            original={'hooks':{'PostModelRequest':[{'hooks':[{'type':'command','command':'existing'}]}]}}
            path.write_text(json.dumps(original))
            c.codex_native_hooks(False);c.codex_native_hooks(False)
            self.assertEqual(len(json.loads(path.read_text())['hooks']['PostModelRequest']),2)
            c.codex_native_hooks(False,True)
            self.assertEqual(json.loads(path.read_text()),original)

    def test_cooldown_stores_only_a_clock_not_analytics(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(c,'INSTALL_DIR',Path(d)):
            self.assertTrue(c.status_sample_due(100000))
            self.assertFalse(c.status_sample_due(100010))
            self.assertTrue(c.status_sample_due(100061))
            self.assertEqual((Path(d)/'status-sample-clock').read_text(),'100061')
            self.assertEqual(len(list(Path(d).iterdir())),1)

    def test_otel_redacts_all_content_and_maps_only_numeric_fields(self):
        attributes={'event.name':'claude_code.compaction','trigger':'auto','success':'false',
                    'duration_ms':'150','pre_tokens':640000,'post_tokens':12000,
                    'session.id':'PRIVATE_SENTINEL','error':'PRIVATE_SENTINEL','model':'PRIVATE_SENTINEL'}
        body={'resourceLogs':[{'resource':{'secret':'PRIVATE_SENTINEL'},'scopeLogs':[{'logRecords':[{
            'attributes':[{'key':k,'value':{'intValue':v} if type(v) is int else {'stringValue':v}} for k,v in attributes.items()]}]}]}]}
        result=c.claude_otel_signals(body,self.config)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['categories']['status'],'failed')
        self.assertEqual(result[0]['metrics']['pre_tokens'],640000)
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))

    def test_haiku_100k_threshold_counts_all_input_components(self):
        result=c.aggregate_usage([{'input_tokens':1000,'cache_read_input_tokens':100000,
                                  'output_tokens':10}],cache_write_in_input=False,price_threshold=100000)
        self.assertEqual(result['long_context_fresh_input_tokens'],1000)
        self.assertEqual(result['long_context_cached_input_tokens'],100000)
        self.assertEqual(result['long_context_output_tokens'],10)

    def test_observational_hook_failure_never_interrupts_or_prints_payload(self):
        with mock.patch.object(c,'load_config',side_effect=RuntimeError('PRIVATE_SENTINEL')), \
             mock.patch.object(c.sys,'stdin',io.StringIO('{}')), \
             mock.patch.object(c.sys,'stdout',io.StringIO()) as out, \
             mock.patch.object(c.sys,'stderr',io.StringIO()) as err:
            self.assertEqual(c.native_hook('codex'),0)
            self.assertEqual(out.getvalue()+err.getvalue(),'')
