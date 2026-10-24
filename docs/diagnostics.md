# Diagnostic code reference

| Code | Interpretation |
|---|---|
| NON_JSON_STDOUT | Non-JSON stdout line (including blank lines); move diagnostics to stderr |
| INVALID_JSON | JSON-looking line cannot be parsed unambiguously |
| INVALID_RPC | Parsed JSON has an unsupported or invalid MCP envelope |
| INVALID_UTF8 | Stdout bytes violate UTF-8 |
| LIKELY_DIAGNOSTIC | Heuristic wording suggests misplaced diagnostics; not proof of cause |
| UNTERMINATED_LINE | Final newline missing; capture may be incomplete |
| EMPTY_CAPTURE | No captured output; startup failure is only a hypothesis |
| LINE_LIMIT | Line exceeds inspection limit; not inspected |
| STDERR_ENCODING | Non-UTF-8 stderr bytes observed |
| CONFIG_SHAPE | Unsupported config field/container shape |
| MISSING_COMMAND | No usable command in the supported config subset |
| UNRESOLVED_REFERENCE | Literal interpolation/home marker; launcher may or may not expand it |
| QUOTED_COMMAND | Shell quotes appear inside the command string |
| NETWORK_PATH_SKIPPED | Explicit network path not probed |
| PATH_LOOKUP_UNVERIFIED | Bare command requires uninspected launcher PATH |
| FOREIGN_PATH | Other-OS path not probed |
| RELATIVE_COMMAND | Working-directory dependency cannot be resolved |
| PATH_UNCHECKED | Native absolute path not probed without --check-paths |
| EXECUTABLE_MISSING | With --check-paths, native path is absent or not a regular file |
| NOT_EXECUTABLE | With --check-paths, POSIX execute access is absent |

All diagnostics include file and physical 1-based line, certainty, explanation and remediation. Config findings also include JSON pointers. An absent field points to the enclosing object. No raw transcript excerpts are emitted, to avoid copying secrets and terminal control sequences. JSON uses escaped strings; Markdown escapes paths.
