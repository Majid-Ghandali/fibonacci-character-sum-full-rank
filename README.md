# An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition

[![GitHub Release](https://img.shields.io/github/v/release/Majid-Ghandali/fibonacci-character-sum-full-rank?display_name=tag&sort=semver)](https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

> **Research compendium** — manuscript source, verification code, and computational results  
> **Majid Ghandali** · Independent Researcher, Tehran, Iran · 2026

This repository contains the reproducibility materials for *An Explicit Evaluation of a Fibonacci Character Sum for Primes of Full Rank of Apparition*. The mathematical proof is in [`Paper/main.tex`](Paper/main.tex); the executable verification suite is [`code/Fibchar_v1-0-1.py`](code/Fibchar_v1-0-1.py).

> **Important distinction.** Computational verification supports the theorem on a finite range; it is not a substitute for the proof. The proof is contained in the manuscript.

## Status and versions

| Item | Value |
|:--|:--|
| Code | FibChar **v1.0.1** · released 2026-07-17 |
| Manuscript source | [`Paper/main.tex`](Paper/main.tex) |
| Verification bound | every prime `p ≤ 2,000,000` in the reported run |
| Committed headline output | [`results/corollary_B1_verification.csv`](results/corollary_B1_verification.csv) |
| Full database | [`results/fib_char_db_N2000000.csv`](results/fib_char_db_N2000000.csv) |
| Previous code archive | [10.5281/zenodo.20707467](https://doi.org/10.5281/zenodo.20707467) |

The code metadata intentionally identifies `10.5281/zenodo.20707467` as the previous release. Do not infer a newer code DOI until it has been minted and recorded in the repository.

## Main theorem

Let `p ≥ 7` be prime and let `α(p)` be the rank of apparition of `p` in the Fibonacci sequence. If `α(p) = p − 1`, then

\[
p\equiv 11\pmod{20}\quad\text{or}\quad p\equiv 19\pmod{20},
\]

and

\[
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n)=
\begin{cases}
+1,&p\equiv11\pmod{20},\\
-1,&p\equiv19\pmod{20}.
\end{cases}
\]

Here `F_n` is the Fibonacci sequence and `χ_p` is the Legendre symbol, with `χ_p(0)=0`. See [`Paper/main.tex`](Paper/main.tex) for the complete statement and proof.

## Verification summary

The reported run through `p = 2,000,000` processed 148,933 primes and found 26,407 full-rank primes. All 26,407 matched the theorem, with zero mismatches. The class totals are:

| `p mod 20` | Predicted `S(p)` | Count | Mismatches |
|:--:|--:|--:|--:|
| 11 | `+1` | 11,755 | 0 |
| 19 | `−1` | 14,652 | 0 |

The committed summary is [`results/corollary_B1_verification.csv`](results/corollary_B1_verification.csv). The full database is [`results/fib_char_db_N2000000.csv`](results/fib_char_db_N2000000.csv). These results are reproducible calculations, not an independent proof.

## Quick start

The repository uses a case-sensitive layout. Run these commands from the repository root:

```bash
git clone https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank.git
cd fibonacci-character-sum-full-rank
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .\\.venv\\Scripts\\Activate.ps1 # Windows PowerShell
python -m pip install --upgrade pip
python -m pip install -r Requirements.txt

# Fast deterministic check: five Appendix-A examples, five invariants each
python code/Fibchar_v1-0-1.py --no-gui --self-test
```

A successful self-test ends with:

```text
[OK] Self-test PASSED  --  all 5 examples * 5 invariants verified.
```

The five checked primes are `11, 19, 31, 59, 79`. A nonzero exit status indicates failure.

## Full verification

To reproduce a complete run and write outputs under the repository's `results/` directory:

```bash
python code/Fibchar_v1-0-1.py \\
  --no-gui --N 2000000 --verify-b1 --out-dir results
```

For a multi-process run (checkpoint/resume is not used in parallel mode):

```bash
python code/Fibchar_v1-0-1.py \\
  --no-gui --N 2000000 --verify-b1 --parallel \\
  --workers 8 --chunk-size 5000 --out-dir results
```

To resume an interrupted sequential run:

```bash
python code/Fibchar_v1-0-1.py \\
  --no-gui --N 2000000 --verify-b1 --resume --out-dir results
```

Windows PowerShell uses the same options and the Windows path separator:

```powershell
python code\Fibchar_v1-0-1.py --no-gui --self-test
python code\Fibchar_v1-0-1.py --no-gui --N 2000000 --verify-b1 --out-dir results
```

See [`docs/reproducibility.md`](docs/reproducibility.md) and the built-in help:

```bash
python code/Fibchar_v1-0-1.py --help
```

## What the program computes

For each prime, the program computes the Pisano period `π(p)`, the rank of apparition `α(p)`, and two related character sums:

- `S_p = Σ_{n=1}^{π(p)} χ_p(F_n)`, the full Pisano-period sum stored in the `S_p` column;
- `T_α = Σ_{n=1}^{α(p)} χ_p(F_n)`, the rank-truncated sum;
- the manuscript's `S(p) = Σ_{n=1}^{p−1} χ_p(F_n)`.

When `α(p)=p−1`, one has `π(p)=α(p)=p−1` and the terminal Fibonacci value contributes zero, so the manuscript sum, `T_α`, and `S_p` agree. Outside the full-rank regime, `S_p` is generally not the same quantity as the manuscript's `S(p)`; the verifier therefore compares the theorem with `T_α` and uses `S_p` as a consistency check.

With `--verify-b1`, the suite also checks the root/order/sign structural statements used in the proof and records the empirical diagnostics E1–E10. The latter are exploratory observations and are not presented as part of the proof.

## Dependencies

`Requirements.txt` contains the tested versions:

- Python 3.11+ (the release environment was Python 3.12.7);
- required: `numpy`, `pandas`;
- optional/recommended: `numba` for JIT acceleration;
- optional: `pyarrow` for Parquet checkpoints and `openpyxl`/`xlsxwriter` for XLSX reports;
- optional: `tkinter` for the graphical interface.

If optional packages are unavailable, the program retains a pure-Python fallback where supported; the CLI self-test does not require the GUI.

## Repository structure

```text
.
├── Paper/                         # Manuscript source and bibliography
│   ├── main.tex
│   └── references.bib
├── code/                          # Verification suite
│   ├── Fibchar_v1-0-0.py
│   └── Fibchar_v1-0-1.py          # Current entry point
├── docs/
│   └── reproducibility.md         # Reproduction notes
├── results/                       # Committed and generated outputs
│   ├── corollary_B1_verification.csv
│   └── fib_char_db_N2000000.csv
├── CITATION.cff
├── LICENSE
├── Requirements.txt
├── .gitignore
└── .gitattributes
```

Do not change the capitalization of `Paper/`, `code/`, or `Requirements.txt` in commands or links on case-sensitive systems.

## Compile the manuscript

The manuscript source is [`Paper/main.tex`](Paper/main.tex). From the `Paper/` directory, a standard LaTeX build is:

```bash
cd Paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

This requires a TeX distribution with `pdflatex`, `bibtex`, and the packages used by the source. The repository currently does not advertise a GitHub Actions manuscript workflow; compilation is a local operation.

## Citation

Use [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata. Cite the manuscript for the mathematics and this repository (or its archived release, when available) for code and computational data.

```bibtex
@misc{Ghandali2026,
  author       = {Ghandali, Majid},
  title        = {An Explicit Evaluation of a Fibonacci Character Sum for
                  Primes with Full Rank of Apparition},
  year         = {2026},
  howpublished = {Research manuscript and reproducibility repository},
  url          = {https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank}
}
```

## License

The repository code, scripts, and computational artifacts are distributed under the [MIT License](LICENSE). Any separate licensing terms stated in the manuscript source or future archival record take precedence for those materials; check the relevant file before redistributing the paper.

## Author

**Majid Ghandali** · Independent Researcher, Tehran, Iran  
Email: [majid.ghandali@gmail.com](mailto:majid.ghandali@gmail.com) · [ORCID 0009-0001-1097-1770](https://orcid.org/0009-0001-1097-1770)
