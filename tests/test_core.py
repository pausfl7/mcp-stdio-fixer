import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mcp_stdio_fixer.core import analyze, check_config, command_style, shape_error, strict_json
from mcp_stdio_fixer.cli import main, markdown


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'capture'

    def inspect(self, data):
        self.path.write_bytes(data)
        return analyze(str(self.path))

    def config(self, obj, probe=False):
        self.path.write_text(json.dumps(obj, indent=2), encoding='utf-8')
        return check_config(str(self.path),probe)

    def test_clean(self):
        self.assertEqual(self.inspect(b'{"jsonrpc":"2.0","id":1,"result":{}}\n')['findings'],[])

    def test_noise_evidence_and_no_echo(self):
        r = self.inspect(b'INFO secret-canary\n{"jsonrpc":"2.0","method":"ping"}\n')
        self.assertEqual([x['code'] for x in r['findings']],['NON_JSON_STDOUT','LIKELY_DIAGNOSTIC'])
        self.assertEqual(r['findings'][0]['line'],1)
        self.assertNotIn('secret-canary',json.dumps(r))

    def test_json_log(self):
        self.assertEqual(self.inspect(b'{"level":"info"}\n')['findings'][0]['code'],'INVALID_RPC')

    def test_invalid_json(self):
        self.assertEqual(self.inspect(b'{broken}\n')['findings'][0]['code'],'INVALID_JSON')

    def test_invalid_utf8(self):
        self.assertEqual(self.inspect(b'\xff\n')['findings'][0]['code'],'INVALID_UTF8')

    def test_batch_scalar_and_blank(self):
        for value in [b'[]\n', b'42\n', b'null\n']:
            with self.subTest(value=value):
                self.assertEqual(self.inspect(value)['findings'][0]['code'],'INVALID_RPC')
        self.assertEqual(self.inspect(b'\n')['findings'][0]['code'],'NON_JSON_STDOUT')

    def test_crlf_and_escaped_newline(self):
        self.assertEqual(self.inspect(b'{"jsonrpc":"2.0","method":"custom","params":{"x":"a\\nb"}}\r\n')['findings'],[])

    def test_truncation_and_empty(self):
        self.assertEqual(self.inspect(b'{"jsonrpc":"2.0","method":"ping"}')['findings'][0]['code'],'UNTERMINATED_LINE')
        self.assertEqual(self.inspect(b'')['findings'][0]['certainty'],'hypothesis')

    def test_unsupported_framing(self):
        for data in [b'Content-Length: 40\n',b'data: {}\n', b'\xef\xbb\xbf{}\n']:
            with self.subTest(data=data): self.assertTrue(self.inspect(data)['findings'])

    def test_shapes(self):
        good=[{'jsonrpc':'2.0','method':'unknown','params':{}},
              {'jsonrpc':'2.0','id':'x','result':{}},
              {'jsonrpc':'2.0','error':{'code':-32700,'message':'Parse error'}},
              {'jsonrpc':'2.0','id':0,'method':'ping'}]
        for msg in good: self.assertIsNone(shape_error(msg))
        bad=[{'jsonrpc':'2.0','id':True,'result':{}},
             {'jsonrpc':'2.0','id':None,'result':{}},
             {'jsonrpc':'2.0','id':1.2,'method':'ping'},
             {'jsonrpc':'2.0','id':1,'result':[]},
             {'jsonrpc':'2.0','method':'ping','params':[]},
             {'jsonrpc':'2.0','id':1,'result':{},'error':{}},
             {'jsonrpc':'2.0','method':'ping','result':{}},
             {'jsonrpc':'2.0','error':{'code':True,'message':'x'}},
             {'jsonrpc':'1.0','method':'ping'},
             {'jsonrpc':'2.0','result':{}}]
        for msg in bad:
            with self.subTest(msg=msg): self.assertIsNotNone(shape_error(msg))

    def test_strict_json(self):
        for s in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}']:
            with self.assertRaises(ValueError): strict_json(s)

    def test_stderr_not_failure(self):
        err = self.path.parent/'stderr'
        err.write_text('ERROR harmless test text\n',encoding='utf-8')
        self.path.write_bytes(b'{"jsonrpc":"2.0","method":"ping"}\n')
        self.assertEqual(analyze(str(self.path),str(err))['findings'],[])

    def test_stderr_encoding(self):
        err=self.path.parent/'stderr';err.write_bytes(b'\xff\n')
        self.path.write_bytes(b'{"jsonrpc":"2.0","method":"ping"}\n')
        r=analyze(str(self.path),str(err))
        self.assertEqual(r['findings'][0]['code'],'STDERR_ENCODING')
        self.assertEqual(r['findings'][0]['file'],str(err))

    def test_config_locations(self):
        self.path.write_text('{\n "mcpServers": {\n "a": {"command": "${BIN}"},\n "b": {\n "command": "%OTHER%"\n }\n }\n}',encoding='utf-8')
        r=check_config(str(self.path))['findings']
        self.assertEqual([(x['line'],x['pointer']) for x in r],[(3,'/mcpServers/a/command'),(5,'/mcpServers/b/command')])

    def test_variable_no_environment_read(self):
        with patch('os.getenv',side_effect=AssertionError('environment read')), patch.dict(os.environ,{},clear=True):
            r=self.config({'command':'${BIN}','args':['$ARG','%ARG%','~/server'],'env':{'KEY':'sentinel'}})
        self.assertEqual(len(r['findings']),4)
        self.assertNotIn('sentinel',json.dumps(r))

    def test_path_styles(self):
        for value,style in [(r'C:\Program Files\app.exe','windows'),(r'\\host\share\app.exe','network'),('//host/share','network'),('/usr/bin/python','posix'),('./app','posix'),('python','bare')]:
            self.assertEqual(command_style(value),style)

    def test_missing_executable_native(self):
        r=self.config({'command':str(self.path.parent/'missing-executable')},True)
        self.assertEqual(r['findings'][0]['code'],'EXECUTABLE_MISSING')

    def test_unprobed_and_foreign_paths(self):
        r=self.config({'command':str(self.path.parent/'missing')})
        self.assertEqual(r['findings'][0]['code'],'PATH_UNCHECKED')
        foreign='/usr/bin/python' if os.name=='nt' else r'C:\Python\python.exe'
        self.assertEqual(self.config({'command':foreign},True)['findings'][0]['code'],'FOREIGN_PATH')

    def test_network_and_bare(self):
        self.assertEqual(self.config({'command':r'\\server\share\app'},True)['findings'][0]['code'],'NETWORK_PATH_SKIPPED')
        self.assertEqual(self.config({'command':'python'})['findings'][0]['code'],'PATH_LOOKUP_UNVERIFIED')

    def test_invalid_config(self):
        for obj in [{}, {'command':' '}, {'mcpServers':[]}]:
            self.assertTrue(self.config(obj)['findings'])
        self.assertEqual(self.config({'command':'${BIN}','args':[1],'env':{'a':3}})['findings'][0]['code'],'CONFIG_SHAPE')

    def test_limits(self):
        self.assertEqual(self.inspect(b'a'*(1024*1024+1)+b'\n')['findings'][0]['code'],'LINE_LIMIT')
        with self.assertRaises(ValueError): self.inspect(b'a'*(8*1024*1024+1))

    def test_cli_codes_and_sanitized_error(self):
        self.path.write_bytes(b'{"jsonrpc":"2.0","method":"ping"}\n')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['analyze',str(self.path),'--format','json']),0)
        self.path.write_bytes(b'noise\n')
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(['analyze',str(self.path)]),1)
        error=io.StringIO()
        with contextlib.redirect_stderr(error): self.assertEqual(main(['check-config',str(self.path)]),2)
        self.assertNotIn('noise',error.getvalue())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm: main(['bad-command'])
        self.assertEqual(cm.exception.code,2)

    def test_markdown_injection(self):
        rendered=markdown({'findings':[dict(file='x|\n<script>`',line=1,code='X',certainty='observation',message='a',remediation='b')]})
        self.assertNotIn('<script>',rendered)
        self.assertIn('&#124;',rendered)

    def test_checked_examples(self):
        root=Path(__file__).resolve().parents[1]
        # Relative evidence paths are intentionally stable across hosts.
        old=Path.cwd()
        try:
            os.chdir(root)
            result=analyze('examples/noisy-stdout.log','examples/server.err')
            self.assertEqual(json.dumps(result,indent=2)+'\n',Path('examples/expected-noisy.json').read_text(encoding='utf-8'))
            self.assertEqual(markdown(check_config('examples/server-config.json')),Path('examples/expected-config.md').read_text(encoding='utf-8'))
        finally: os.chdir(old)


if __name__=='__main__': unittest.main()
