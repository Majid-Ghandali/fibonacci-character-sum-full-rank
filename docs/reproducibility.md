
    # Reproducibility Guide

This document describes how to reproduce the computational results for the paper
*An Explicit Evaluation of a Fibonacci Character Sum for Primes of Full Rank of Apparition*.

## Repository Layout

- `paper/`: LaTeX source of the manuscript.
- `code/`: Python source code for the verification suite.
- `data/`: raw and processed data.
- `results/`: exported CSV, TXT, XLSX, and log files.
- `docs/`: additional notes, including this reproducibility guide.

## Requirements

- Python 3.10 or newer.
- NumPy.
- Pandas.
- Numba.
- OpenPyXL or XlsxWriter for Excel export.

## Main Script

The verification suite can be run in GUI or CLI mode.

Example CLI usage:
```bash
python fibchar.py --no-gui --N 2000000 --resume
```

## Outputs

The script writes the following outputs:

- `results/csv/fib_char_db_N2000000.csv`
- `results/txt/fib_char_report_N2000000.txt`
- `results/xlsx/fib_char_report_N2000000.xlsx`
- `results/csv/corollary_B1_verification.csv`
- checkpoint files during long runs, removed automatically after a successful finish

## Computational Summary

The current verified run processed 148,933 primes up to 2,000,000 and found 26,407 primes with full rank of apparition, all of which satisfied the main theorem.

The run also confirmed the empirical claims E1–E10 with zero violations.

## Notes

- The code uses three backends for evaluating the quadratic character:
  1. residue-table lookup,
  2. bitwise Jacobi symbol,
  3. modular exponentiation via Euler's criterion.
- Checkpointing is enabled every 2,000 primes.
- The code supports resume after interruption.
- For citation, use the Zenodo DOI and the `CITATION.cff` file in the repository root.
