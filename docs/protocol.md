# Protocol boundary

Reference revision: 2025-11-25, reviewed 2026-10-24.

- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://modelcontextprotocol.io/specification/2025-11-25/basic

Only stdio framing and base envelope checks are implemented. Requests and notifications have a string method and optional object params. Successful responses have an ID and object result. Error responses have an integer error code and string message; their ID may be absent when an incoming request's ID could not be read. An ID, when present, must be a string or integer (not a Python boolean, float or null). Result/error are mutually exclusive. Unknown extension fields are retained conceptually but not method-validated. Empty string methods/IDs are not forbidden by this envelope checker.

Arrays are reported INVALID_RPC: batching is outside the pinned stdio message forms. Duplicate object members are rejected as ambiguous JSON, including in nested payloads. Python's non-standard NaN/Infinity are rejected. Arbitrarily large numeric payloads and deep nesting are bounded by the interpreter and input limits; parser recursion failures produce a diagnostic or input error. Blank stdout lines and UTF-8 BOMs are not valid protocol frames. CRLF endings are accepted; escaped JSON newline characters are fine. An unterminated final frame is a truncation/flush hypothesis, not proof of a live writer's bug.

No paired request/response stream is supplied, so no handshake, duplicate-session-ID, order, timeout or method-specific validation is performed. No log-prefix stripping or automatic recovery rewrites evidence. A well-formed JSON log object is still invalid if it lacks a JSON-RPC envelope. stderr is counted and checked for encoding, not interpreted as an error by its mere presence.

Config inspection accepts a direct object or an mcpServers mapping; this is an explicitly supported client-config subset, not an MCP standard configuration schema. Other transports and client-specific interpolation rules remain outside scope. JSON pointers and physical line numbers identify value locations, including multiline values and repeated keys in different objects. No value is echoed.
