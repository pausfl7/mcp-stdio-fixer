# MCP stdio diagnostics

| File | Line | Code | Certainty | Evidence | Remediation |
|---|---:|---|---|---|---|
| &quot;examples/server-config.json&quot; | &quot;2&quot; | &quot;UNRESOLVED_REFERENCE&quot; | &quot;hypothesis&quot; | &quot;A literal variable or home reference requires host-specific expansion.&quot; | &quot;Check the client&#x27;s interpolation rules; supply a resolved non-secret path if appropriate. Values were not expanded.&quot; |

Static config inspection; no execution, environment reads or PATH lookup.
