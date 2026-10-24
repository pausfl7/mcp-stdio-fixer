# Optional resource previews

The free CLI covers the supplied synthetic examples independently of optional resources.

`mcp-stdio-repair` adds reviewable unified diffs: select a Python print call by source line to move its output to stderr, or replace one config command/args pair using explicit approved values. The helper never applies the patch or executes the source. Included reward fixtures demonstrate a banner repair and confirm the resulting source parses. Automatic source proposals deliberately reject scope/stream ambiguity; manual review remains necessary.

`mcp-transport-triage` adds paired-stream evidence: index requests and responses by direction and ID type, locate initialization evidence, and separate a protocol error object from a tools/call result with isError=true. It uses optional recorded exit status as evidence, never launches a server, and treats unmatched messages as incomplete-capture hypotheses. Included reward fixtures exercise success, missing initialization response, transport mismatch and tool failure.

These describe supplied implementations, not external adoption or benchmark claims. Reward terms and the optional public puzzle are in `.agent-resources/challenge.json`. Public paths are relative to the repository root.
