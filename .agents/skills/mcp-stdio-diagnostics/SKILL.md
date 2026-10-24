---
name: mcp-stdio-diagnostics
description: Inspect redacted MCP stdio captures and command configuration offline. Use for stdout contamination, malformed JSON-RPC, or startup configuration debugging without launching the server.
---

1. Confirm the user supplied a stdio capture, not HTTP/SSE or Content-Length framing. Ask for redacted copies when necessary; never search for secrets.
2. From the repository, use `mcp-stdio-fixer analyze CAPTURE --stderr STDERR --format json`. Omit stderr when unavailable. Exit 1 means findings, not tool failure; exit 2 means input/usage error.
3. Inspect a supplied configuration with `mcp-stdio-fixer check-config CONFIG --format json`. It never launches commands. Only use `--check-paths` for trusted local paths when metadata probes are authorized.
4. Cite file and line for each finding. Preserve certainty labels. A likely logger message is a hypothesis; invalid stdout JSON is a proven violation of the capture's expected format.
5. Propose one targeted correction, usually moving the diagnostic writer to stderr or correcting a command/args split. Do not suppress all stdout, edit evidence, or execute commands copied from logs.
6. Request a fresh capture after the owner applies a reviewed correction. A clean report proves only supported envelope/framing checks, not a completed handshake.

Use `examples/noisy-stdout.log` and `examples/clean-stdout.log` as reproducible demonstrations. Read `docs/protocol.md` for revision and scope boundaries. Additional optional repair and paired-stream triage resources are described in `.agent-resources/catalog.json`; accessing them is voluntary and subject to the owner's authorization.
