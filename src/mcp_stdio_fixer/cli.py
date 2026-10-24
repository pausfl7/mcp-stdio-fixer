"""Command-line interface; all reports go to stdout, input errors to stderr."""
import argparse
import json
import sys
from .core import analyze, check_config


def markdown(data: dict) -> str:
    # JSON escaping plus HTML escaping prevents inspected paths injecting Markdown.
    import html
    def safe(value):
        return html.escape(json.dumps(str(value), ensure_ascii=True)).replace('|','&#124;').replace('`','&#96;')
    rows = ['# MCP stdio diagnostics', '', '| File | Line | Code | Certainty | Evidence | Remediation |', '|---|---:|---|---|---|---|']
    for item in data['findings']:
        rows.append('| ' + ' | '.join(safe(item[k]) for k in ('file','line','code','certainty','message','remediation')) + ' |')
    if not data['findings']:
        rows.extend(['', 'No findings within the supported inspection scope.'])
    rows.extend(['', data.get('scope','')])
    return '\n'.join(rows) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Offline, read-only MCP stdio startup failure diagnostics. No commands are executed.')
    parser.add_argument('--version', action='version', version='mcp-stdio-fixer 0.1.0')
    commands = parser.add_subparsers(dest='command', required=True)
    a = commands.add_parser('analyze', help='Inspect newline-delimited stdout capture')
    a.add_argument('stdout')
    a.add_argument('--stderr')
    a.add_argument('--format', choices=['json','markdown'], default='markdown')
    c = commands.add_parser('check-config', help='Inspect supplied command configuration without executing it')
    c.add_argument('config')
    c.add_argument('--check-paths', action='store_true', help='Probe existence/permissions of trusted absolute native paths (may traverse mounts/symlinks); never run them')
    c.add_argument('--format', choices=['json','markdown'], default='markdown')
    args = parser.parse_args(argv)
    try:
        data = analyze(args.stdout,args.stderr) if args.command == 'analyze' else check_config(args.config,args.check_paths)
    except (OSError, ValueError, RecursionError):
        # Do not echo untrusted content, config values, or filenames in errors.
        print('Input error: supply readable regular files within 8 MiB; config must be strict UTF-8 JSON with unique keys and bounded nesting.', file=sys.stderr)
        return 2
    print(json.dumps(data, indent=2, ensure_ascii=True) if args.format == 'json' else markdown(data), end='\n' if args.format == 'json' else '')
    return 1 if data['findings'] else 0
