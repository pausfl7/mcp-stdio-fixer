"""Offline, bounded, non-executing MCP stdio inspection (2025-11-25)."""
from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
from typing import Any

REVISION = "2025-11-25"
MAX_BYTES = 8 * 1024 * 1024
MAX_LINE = 1024 * 1024


def read_bytes(path: str) -> bytes:
    p = Path(path)
    if not stat.S_ISREG(p.stat().st_mode):
        raise ValueError("Input must be a regular file")
    with p.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Input exceeds 8 MiB limit")
    return data


def strict_json(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON member")
            result[key] = value
        return result

    def constant(_: str) -> Any:
        raise ValueError("Non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def valid_id(value: Any) -> bool:
    return type(value) in (str, int)


def shape_error(message: Any) -> str | None:
    if not isinstance(message, dict):
        return "Expected one JSON-RPC object; batch arrays and scalar messages are unsupported."
    if message.get("jsonrpc") != "2.0":
        return 'Expected jsonrpc equal to "2.0".'
    if "id" in message and not valid_id(message["id"]):
        return "MCP IDs must be strings or integers, never null, floats or booleans."
    if "method" in message:
        if not isinstance(message["method"], str):
            return "Method must be a string."
        if "result" in message or "error" in message:
            return "A request/notification cannot also be a response."
        if "params" in message and not isinstance(message["params"], dict):
            return "MCP params must be an object."
    else:
        if ("result" in message) == ("error" in message):
            return "A response must contain exactly one of result or error."
        if "params" in message:
            return "Response cannot contain request params."
        if "result" in message:
            if "id" not in message or not isinstance(message["result"], dict):
                return "A successful MCP response requires an ID and an object result."
        else:
            e = message["error"]
            if not isinstance(e, dict) or type(e.get("code")) is not int or not isinstance(e.get("message"), str):
                return "Error must contain an integer code and string message."
            # 2025-11-25 allows omitted IDs for errors with unreadable request IDs.
    return None


def finding(path: str, line: int, code: str, certainty: str, message: str,
            remediation: str, pointer: str | None = None) -> dict[str, Any]:
    item = dict(file=path, line=line, code=code, certainty=certainty,
                message=message, remediation=remediation)
    if pointer is not None:
        item["pointer"] = pointer
    return item


def report(kind: str, findings: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return dict(schema_version=1, kind=kind, protocol_revision=REVISION,
                findings=findings, **extra)


def analyze(stdout: str, stderr: str | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    data = read_bytes(stdout)
    valid = 0
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    for number, raw in enumerate(lines, 1):
        def add(code: str, certainty: str, message: str, fix: str) -> None:
            findings.append(finding(stdout, number, code, certainty, message, fix))
        if len(raw) > MAX_LINE:
            add("LINE_LIMIT", "limitation", "Line exceeds 1 MiB inspection limit.", "Inspect a smaller redacted capture.")
            continue
        try:
            line = raw.decode("utf-8")
        except UnicodeDecodeError:
            add("INVALID_UTF8", "violation", "Line is not valid UTF-8.", "Configure UTF-8 encoding at the writer; recapture original bytes.")
            continue
        try:
            msg = strict_json(line)
        except (ValueError, RecursionError):
            code = "INVALID_JSON" if line.lstrip().startswith(('{', '[', '"')) else "NON_JSON_STDOUT"
            add(code, "violation", "Line is not a single unambiguous JSON message.", "Write only compact JSON-RPC to stdout; send diagnostics to stderr.")
            if re.search(r"\b(info|debug|warn|warning|error|starting|listening|traceback)\b", line, re.I):
                add("LIKELY_DIAGNOSTIC", "hypothesis", "Text resembles a diagnostic accidentally written to stdout.", "Inspect the logger or startup banner writer and redirect only that writer to stderr.")
            continue
        error = shape_error(msg)
        if error:
            add("INVALID_RPC", "violation", error, "Correct the message producer against the documented MCP envelope; do not edit captured evidence.")
        else:
            valid += 1
    if data and not data.endswith(b"\n"):
        findings.append(finding(stdout, len(lines), "UNTERMINATED_LINE", "hypothesis", "Capture ends without a newline; it may be truncated or the writer may not have flushed a complete frame.", "Recapture complete output and check the writer's newline/flush behavior."))
    if not data:
        findings.append(finding(stdout, 1, "EMPTY_CAPTURE", "hypothesis", "No stdout bytes were captured; startup failure is only one possible cause.", "Check capture timing, stderr and the launch configuration."))
    stderr_lines = 0
    if stderr:
        err_data = read_bytes(stderr)
        err_lines = err_data.split(b"\n")
        if err_lines[-1] == b"":
            err_lines.pop()
        stderr_lines = len(err_lines)
        for number, raw in enumerate(err_lines, 1):
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(finding(stderr, number, "STDERR_ENCODING", "observation", "Stderr contains non-UTF-8 bytes.", "Check stderr encoding separately; this does not prove a stdout protocol failure."))
    return report("transcript", findings, valid_messages=valid, stdout_lines=len(lines), stderr_lines=stderr_lines,
                  scope="Envelope/framing only; no handshake, method schema or request-response correlation validation.")


TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+')
REF = re.compile(r'\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*|%[^%]+%')


def locations(text: str) -> dict[str, int]:
    """Locate JSON pointer values after strict parsing; never use key-only search."""
    tokens = list(TOKEN.finditer(text))
    positions: dict[str, int] = {}
    i = 0
    def walk(pointer: str) -> None:
        nonlocal i
        positions[pointer] = text.count("\n", 0, tokens[i].start()) + 1
        token = tokens[i].group()
        i += 1
        if token == "{":
            while tokens[i].group() != "}":
                key = json.loads(tokens[i].group()).replace("~", "~0").replace("/", "~1")
                i += 2  # key, colon
                walk(pointer + "/" + key)
                if tokens[i].group() != ",":
                    break
                i += 1
            i += 1
        elif token == "[":
            n = 0
            while tokens[i].group() != "]":
                walk(pointer + "/" + str(n))
                n += 1
                if tokens[i].group() != ",":
                    break
                i += 1
            i += 1
    walk("")
    return positions


def command_style(command: str) -> str:
    if command.startswith(("\\\\", "//")):
        return "network"
    if PureWindowsPath(command).drive or "\\" in command:
        return "windows"
    if "/" in command:
        return "posix"
    return "bare"


def check_config(path: str, check_paths: bool = False) -> dict[str, Any]:
    text = read_bytes(path).decode("utf-8")
    obj = strict_json(text)
    loc = locations(text)
    out: list[dict[str, Any]] = []
    def add(pointer: str, code: str, certainty: str, message: str, fix: str) -> None:
        out.append(finding(path, loc.get(pointer, 1), code, certainty, message, fix, pointer))
    servers = obj.get("mcpServers") if isinstance(obj, dict) and "mcpServers" in obj else None
    if servers is not None:
        if not isinstance(servers, dict):
            add("/mcpServers", "CONFIG_SHAPE", "observation", "mcpServers must be an object.", "Use a mapping of names to command configurations.")
            return report("config", out)
        entries = [("/mcpServers/" + k.replace("~", "~0").replace("/", "~1"), v) for k,v in servers.items()]
    else:
        entries = [("", obj)]
    for base, cfg in entries:
        if not isinstance(cfg, dict):
            add(base, "CONFIG_SHAPE", "observation", "Server config must be an object.", "Provide command, optional args and env.")
            continue
        cmd = cfg.get("command")
        if not isinstance(cmd, str) or not cmd.strip():
            add(base, "MISSING_COMMAND", "observation", "Nonempty command string is missing.", "Set the executable separately from its args; HTTP configurations are outside this tool's scope.")
            continue
        for field, predicate in [("args", lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v)), ("env", lambda v: isinstance(v, dict) and all(isinstance(x, str) for x in v.values()))]:
            if field in cfg and not predicate(cfg[field]):
                add(base + "/" + field, "CONFIG_SHAPE", "observation", "Invalid " + field + " container or value types.", "Use an array of strings for args and a string-valued object for env.")
        # Inspect only supplied data. Never expand variables or read os.environ.
        def refs(value: Any, ptr: str) -> None:
            if isinstance(value, str) and (REF.search(value) or value.startswith("~")):
                add(ptr, "UNRESOLVED_REFERENCE", "hypothesis", "A literal variable or home reference requires host-specific expansion.", "Check the client's interpolation rules; supply a resolved non-secret path if appropriate. Values were not expanded.")
            elif isinstance(value, list):
                for n, v in enumerate(value): refs(v, ptr + "/" + str(n))
            elif isinstance(value, dict):
                for k,v in value.items(): refs(v, ptr + "/" + k.replace("~", "~0").replace("/", "~1"))
        refs(cfg, base)
        ptr = base + "/command"
        if REF.search(cmd) or cmd.startswith("~"):
            continue
        style = command_style(cmd)
        if cmd.startswith(('"', "'")):
            add(ptr, "QUOTED_COMMAND", "hypothesis", "Command appears to include literal shell quotes.", "Store the executable path without surrounding quotes; place arguments in args.")
        if style == "network":
            add(ptr, "NETWORK_PATH_SKIPPED", "limitation", "Network command paths are never probed.", "Check the path manually in the intended environment.")
        elif style == "bare":
            add(ptr, "PATH_LOOKUP_UNVERIFIED", "limitation", "Bare executable needs the launcher's PATH; PATH is not read.", "Confirm availability in the launcher environment, or specify an absolute executable path.")
        elif (style == "windows") != (os.name == "nt"):
            add(ptr, "FOREIGN_PATH", "limitation", "Command path belongs to another operating-system syntax.", "Check existence on the target OS; this tool does not translate paths.")
        elif not Path(cmd).is_absolute():
            add(ptr, "RELATIVE_COMMAND", "hypothesis", "Relative command depends on the launcher's working directory.", "Set an explicit absolute path after confirming the intended launch directory.")
        elif not check_paths:
            add(ptr, "PATH_UNCHECKED", "limitation", "Absolute path was not probed.", "Optionally use --check-paths for trusted local paths; no executable content is read.")
        else:
            p = Path(cmd)
            if not p.is_file():
                add(ptr, "EXECUTABLE_MISSING", "observation", "Command is not an existing regular file on this host.", "Correct the path or install the intended executable; do not download from untrusted diagnostics.")
            elif os.name != "nt" and not os.access(p, os.X_OK):
                add(ptr, "NOT_EXECUTABLE", "observation", "File lacks execute permission for the current process.", "Verify the file and intended permissions before changing them.")
    return report("config", out, scope="Static config inspection; no execution, environment reads or PATH lookup.")
