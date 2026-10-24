# Contributing

Use Python 3.11+, a local virtual environment, and `python -m pip install -e .`.
Run `python -m unittest discover -s tests -v`. Add synthetic fixtures for each parser change. Preserve deterministic ordering and exit codes. No network or process-launch dependencies belong in inspection code. Never attach real credentials or full production captures to issues. Describe OS, Python version, diagnostic code and a minimal redacted reproduction.

Public challenge tests must not encode its canonical solution. Test ordinary fixtures instead. Private reward material, operator notes and answer keys must remain outside this repository.
