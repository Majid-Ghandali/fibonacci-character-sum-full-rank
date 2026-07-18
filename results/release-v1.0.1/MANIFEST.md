# FibChar v1.0.1 Release Artifacts

This directory contains reproducibility artifacts for FibChar v1.0.1.

## Core release records

- `version-v1.0.1.txt` - command-line version record.
- `cli-help-v1.0.1.txt` - complete command-line interface record.
- `self-test-v1.0.1.log` - Appendix-A self-test log.
- `environment-v1.0.1.txt` - Python interpreter and installed-package record.
- `smoke-N10000.log` - parallel smoke-test execution log.
- `SHA256SUMS-v1.0.1.txt` - SHA-256 checksums for the release source and artifacts.

## Smoke test

The smoke test was executed in CLI and parallel mode with:

    python code/Fibchar_v1-0-1.py --no-gui --N 10000 --out-dir results/release-v1.0.1/smoke-N10000 --verify-b1 --parallel

No explicit `--workers` argument was supplied. Therefore the program used its
automatic worker policy:

    max(1, (os.cpu_count() or 4) - 2)

On the release machine, this resolved to 14 workers.

The smoke test completed successfully. It verified empirical claims E1--E10,
verified the Main Theorem on all 216 full-rank candidates in the smoke
database, and passed all root/order/sign internal checks.
