# mcp-stdio-fixer

Offline, read-only **MCP server stdout contamination** and **startup failure diagnostics**.
Find banners, invalid UTF-8, malformed JSON and an **invalid JSON-RPC response** in captured stdio output. Inspect command configuration without launching it.

## Install from this repository

Python 3.11+; no runtime dependencies. The distribution is not claimed to exist on PyPI.
Run from the extracted repository directory.

Linux:
```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```
Windows PowerShell:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\mcp-stdio-fixer.exe --help
```
Installation may fetch setuptools from your configured package index. The installed CLI itself never uses the network. Without installation, set `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH="src"`) and use `python -m mcp_stdio_fixer`.

## A reproducible example

```console
mcp-stdio-fixer analyze examples/noisy-stdout.log --stderr examples/server.err --format json
mcp-stdio-fixer check-config examples/server-config.json
```

The first command identifies `examples/noisy-stdout.log:1` as `NON_JSON_STDOUT` (a violation), plus `LIKELY_DIAGNOSTIC` (a hypothesis about its cause). The JSON-RPC response on line 2 is structurally valid. The second flags a literal environment reference without reading its value. Both commands exit **1**, because they have findings. [Checked full output](examples/expected-noisy.json) and [config output](examples/expected-config.md) are regenerated and compared by tests.

```console
mcp-stdio-fixer analyze examples/clean-stdout.log --format markdown
mcp-stdio-fixer check-config your-redacted-config.json --format json
```

A clean envelope check exits **0**. Usage, unreadable input or invalid config JSON exits **2**. Any diagnostic, including an inspection limitation, exits **1**; consumers should inspect `certainty`, not treat every finding as a protocol violation. Use `--check-paths` only for trusted local native absolute executable paths when filesystem existence checks are wanted. No PATH search, environment expansion or executable reads occur.

## Scope

Pinned to **MCP revision 2025-11-25**, stdio only. Physical LF lines carry individual UTF-8 JSON-RPC envelopes; CRLF is accepted. Pretty-printed multiline JSON, batches, SSE and Content-Length framing are not stdio messages in this scope. See [protocol decisions](docs/protocol.md) and [diagnostic codes](docs/diagnostics.md).

An **MCP stdio handshake** cannot be proven successful from a one-sided fragment. This tool checks framing and envelope shapes, not full method schemas, negotiated capabilities, response correlation, startup exit status or server correctness. Unknown method names pass envelope checks. An empty capture is inconclusive. Stderr content alone is not a failure. Error responses may omit IDs under the pinned revision; null IDs are rejected.

Only explicitly supplied files are read (8 MiB/file; 1 MiB/stdout line). Give it **redacted copies**, not secret-bearing configurations: it must read supplied bytes to parse them. It does not discover credential files or read environment values. Reports omit raw message bodies and config values, but paths and JSON pointers may identify local resources. Oversized lines are reported as uninspected. No telemetry, downloads, shell evaluation, commands, repairs or background processes.

The name describes a diagnostic aid: fixes are proposed in text, never applied. `--check-paths` uses filesystem metadata and can traverse mounted filesystems or symlinks; explicit UNC/network paths are skipped. Foreign OS paths are classified without probing. Relative paths cannot be resolved without knowing the launcher's working directory.

## Develop

```console
python -m pip install -e .
python -m unittest discover -s tests -v
```

CI covers Python 3.11 and 3.13 on Linux and Windows. Local verification is documented in the separate delivery report; CI configuration is not a claim of a completed hosted run. Keep fixtures synthetic. See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.

Suggested GitHub topics: `mcp`, `model-context-protocol`, `stdio`, `json-rpc`, `debugging`, `python`, `offline`, `developer-tools`.
