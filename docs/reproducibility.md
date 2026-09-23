# Reproducibility Guide

This guide describes the computational materials accompanying:

> Majid Ghandali, *An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition* (2026).

## Scope and release boundary

The official computational release is **FibChar v1.0.1**. Its frozen evidence bundle is:

```text
results/release-v1.0.1/
```

This directory is a checksum-recorded historical release artifact. Do not rename files in it, convert its line endings, edit it, or reuse it as the output directory of a new rerun.

The formal release record is described by:

```text
results/release-v1.0.1/MANIFEST.md
results/release-v1.0.1/SHA256SUMS-v1.0.1.txt
```

The software/reproducibility DOI is [10.5281/zenodo.21431565](https://doi.org/10.5281/zenodo.21431565). The separate manuscript DOI is [10.5281/zenodo.22803009](https://doi.org/10.5281/zenodo.22803009).

## Requirements

The v1.0.1 environment record reports:

- Python 3.12.7
- NumPy 1.26.4
- Pandas 2.1.4
- Numba 0.62.1
- OpenPyXL 3.1.5
- XlsxWriter 3.2.0

Install the pinned Python dependencies from the repository root:

```bash
python -m pip install -r Requirements.txt
```

## Verification commands

The frozen release executable is:

```text
code/Fibchar_v1-0-1.py
```

The original recorded smoke-test command was:

```bash
python code/Fibchar_v1-0-1.py --no-gui --N 10000 --out-dir results/release-v1.0.1/smoke-N10000 --verify-b1 --parallel
```

Do not rerun that command into the frozen release directory. For a fresh local smoke test, use a new output directory:

```bash
python code/Fibchar_v1-0-1.py --no-gui --N 10000 --out-dir results/reproduced-smoke-N10000 --verify-b1 --parallel
```

The recorded parallel-worker policy is:

```text
max(1, (os.cpu_count() or 4) - 2)
```

The smoke run checked empirical claims E1--E10, the main theorem on full-rank candidates in the smoke database, and internal root/order/sign checks. Consult `results/release-v1.0.1/MANIFEST.md` for the authoritative release description.

## Integrity verification

Run checksum verification from the repository root.

On Linux or macOS:

```bash
sha256sum -c results/release-v1.0.1/SHA256SUMS-v1.0.1.txt
```

On Windows PowerShell, use `Get-FileHash` for any manifest-recorded path and compare the digest with `SHA256SUMS-v1.0.1.txt`.

## Notes on longer computations

The repository contains historical outputs associated with longer computations, including the `N=2,000,000` database. No long computation is required to verify the v1.0.1 release evidence. A long rerun should be planned separately, use a new output directory, and preserve its own environment and integrity record.

## Citation

- Cite the manuscript DOI for the mathematical theorem and proof.
- Cite the FibChar DOI for code, computational data, and reproducibility reruns.

Machine-readable citation metadata is provided in `Paper/CITATION.cff` and `CITATION.cff`, respectively.
