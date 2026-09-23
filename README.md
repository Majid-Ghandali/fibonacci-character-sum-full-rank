# FibChar: Fibonacci Character Sum at Full Rank

[![Manuscript DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22803009.svg)](https://doi.org/10.5281/zenodo.22803009)
[![Code Archive DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21431565.svg)](https://doi.org/10.5281/zenodo.21431565)
[![License: MIT (code)](https://img.shields.io/badge/License-MIT%20(code)-yellow.svg)](LICENSE)
[![License: CC BY 4.0 (paper)](https://img.shields.io/badge/License-CC%20BY%204.0%20(paper)-lightgrey.svg)](Paper/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12.7-blue.svg)](https://www.python.org/)

**Majid Ghandali** · Independent Researcher, Tehran, Iran · 2026<br>
ORCID: [0009-0001-1097-1770](https://orcid.org/0009-0001-1097-1770)

Reproducibility materials for the preprint:

> *An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition*

> **Proof versus computation.** The mathematical theorem is proved in the manuscript. Computations in this repository provide finite-range verification of the stated identities and reported numerical results; they are not a substitute for the proof.

---

## Citation and DOI records

The manuscript and the computational release are separate research objects:

| Object | Use | DOI |
| --- | --- | --- |
| Manuscript preprint | Mathematical result and proof | [10.5281/zenodo.22803009](https://doi.org/10.5281/zenodo.22803009) |
| FibChar v1.0.1 reproducibility archive | Software, data, and reproducibility reruns | [10.5281/zenodo.21431565](https://doi.org/10.5281/zenodo.21431565) |

- Manuscript citation metadata: [`Paper/CITATION.cff`](Paper/CITATION.cff)
- Software citation metadata: [`CITATION.cff`](CITATION.cff)

---

## Quick start

```bash
git clone https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank.git
cd fibonacci-character-sum-full-rank

python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\Activate.ps1     # Windows PowerShell

python -m pip install --upgrade pip
python -m pip install -r Requirements.txt

# Deterministic self-test (Appendix A examples)
python code/Fibchar_v1-0-1.py --no-gui --self-test
```

A successful self-test ends with a line of the form:

```text
[OK] Self-test PASSED ...
```

---

## Main theorem (statement only)

Let $p \ge 7$ be prime and suppose $\alpha(p) = p-1$, where $\alpha(p)$ is the rank of apparition of $p$ in the Fibonacci sequence. Then

$$
p \equiv 11 \pmod{20}
\quad\text{or}\quad
p \equiv 19 \pmod{20},
$$

and

$$
S(p) = \sum_{n=1}^{p-1} \chi_p(F_n)
=
\begin{cases}
+1, & p \equiv 11 \pmod{20}, \\
-1, & p \equiv 19 \pmod{20}.
\end{cases}
$$

Here $\chi_p$ is the quadratic character modulo $p$, with the convention $\chi_p(0) = 0$.

For the full hypotheses, lemmas, and proof, see [`Paper/main.tex`](Paper/main.tex).

---

## Verification headline (committed evidence)

Reported full-range run through $p \le 2{,}000{,}000$:

| Quantity | Value |
| --- | ---: |
| Primes tested | 148,933 |
| Full-rank primes $\alpha(p) = p-1$ | 26,407 |
| Full-rank primes with $p \equiv 11 \pmod{20}$ | 11,755 |
| Full-rank primes with $p \equiv 19 \pmod{20}$ | 14,652 |
| Main-theorem mismatches | **0** |

- Headline CSV: [`results/corollary_B1_verification.csv`](results/corollary_B1_verification.csv)
- Full database: [`results/fib_char_db_N2000000.csv`](results/fib_char_db_N2000000.csv)

These are finite computational results offered as consistency evidence, not as numerical proofs.

---

## What the program computes

| Symbol | Definition |
| --- | --- |
| $S(p)$ | $\sum_{n=1}^{p-1} \chi_p(F_n)$ (manuscript sum) |
| $T_\alpha(p)$ | $\sum_{n=1}^{\alpha(p)} \chi_p(F_n)$ (rank-truncated sum) |
| $S_p$ | $\sum_{n=1}^{\pi(p)} \chi_p(F_n)$ (full Pisano-period sum in the code) |

In the full-rank regime, $\alpha(p) = \pi(p) = p-1$, so the quantities relevant to the main theorem coincide. Outside that regime they need not agree; the implementation keeps them distinct.

For each prime, the suite can also record the rank of apparition, the Pisano period, $v_2(\pi(p))$, the arithmetic signature determined by $\chi_p(-1)$ and $\chi_p(5)$, character counts, and main-theorem checks. Auxiliary empirical diagnostics are not additional theorems unless they are stated and proved in the manuscript.

### Character-evaluation backends

| Backend | Method | Memory |
| --- | --- | --- |
| A | Quadratic-residue lookup table | $O(p)$ |
| B | Bitwise Jacobi evaluation | $O(1)$ |
| C | Euler-criterion modular exponentiation | $O(1)$ |

The program dispatches among these backends according to configurable thresholds and uses Numba when available.

---

## Full verification commands

Sequential run through $p = 2{,}000{,}000$:

```bash
python code/Fibchar_v1-0-1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --out-dir results/reproduced-N2000000
```

Resume an interrupted sequential run:

```bash
python code/Fibchar_v1-0-1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --resume \
  --out-dir results/reproduced-N2000000
```

Parallel run (no checkpoint or resume):

```bash
python code/Fibchar_v1-0-1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --parallel \
  --out-dir results/reproduced-N2000000
```

In parallel mode, the recorded default worker policy is:

```text
max(1, (os.cpu_count() or 4) - 2)
```

Use `--workers` only when you deliberately want to override that automatic policy. Always use a **new** `--out-dir` for new runs. Do not write into `results/release-v1.0.1/`.

Windows PowerShell:

```powershell
python code\Fibchar_v1-0-1.py --no-gui --self-test
python code\Fibchar_v1-0-1.py --no-gui --N 2000000 --verify-b1 --out-dir results\reproduced-N2000000
```

Full CLI help:

```bash
python code/Fibchar_v1-0-1.py --help
```

---

## Frozen reproducibility release (v1.0.1)

Canonical software release: **FibChar v1.0.1**<br>
Executable artifact: [`code/Fibchar_v1-0-1.py`](code/Fibchar_v1-0-1.py)

Official historical evidence bundle:

```text
results/release-v1.0.1/
```

This directory is byte-preserved and checksum-recorded. Do **not** rename files in it, normalize its line endings, edit it, or overwrite it with a new rerun.

Authoritative records:

```text
results/release-v1.0.1/MANIFEST.md
results/release-v1.0.1/SHA256SUMS-v1.0.1.txt
```

Recorded historical smoke-test command (do not target the frozen directory again):

```bash
python code/Fibchar_v1-0-1.py --no-gui --N 10000 \
  --out-dir results/release-v1.0.1/smoke-N10000 --verify-b1 --parallel
```

Fresh local smoke test:

```bash
python code/Fibchar_v1-0-1.py --no-gui --N 10000 \
  --out-dir results/reproduced-smoke-N10000 --verify-b1 --parallel
```

Further detail: [`docs/reproducibility.md`](docs/reproducibility.md).

### Integrity verification

From the repository root (paths in the manifest are repository-relative):

```bash
sha256sum -c results/release-v1.0.1/SHA256SUMS-v1.0.1.txt
```

Windows (example for a single file):

```powershell
Get-FileHash code\Fibchar_v1-0-1.py -Algorithm SHA256
# Compare the digest with the corresponding line in SHA256SUMS-v1.0.1.txt
```

The official executable digest is recorded in the checksum manifest. Do not clean or rewrite release evidence to satisfy cosmetic checks; integrity is defined by `SHA256SUMS-v1.0.1.txt`.

---

## Repository layout

```text
Paper/                              manuscript (CC BY 4.0): main.tex, references.bib, PDF, LICENSE, CITATION.cff
code/Fibchar_v1-0-1.py              frozen executable for FibChar v1.0.1
code/Fibchar_v1-0-0.py              previous program snapshot
results/release-v1.0.1/             frozen, checksum-recorded release evidence
results/corollary_B1_verification.csv
results/fib_char_db_N2000000.csv
docs/reproducibility.md             reproduction guide
LICENSE                             MIT (code and computational materials)
Paper/LICENSE                       CC BY 4.0 (manuscript)
LICENSES.md                         scope of the two licenses
CITATION.cff                        software / FibChar citation
Requirements.txt
```

---

## Requirements

- Tested release environment: **Python 3.12.7**
- Install the pinned dependencies in [`Requirements.txt`](Requirements.txt): NumPy 1.26.4, Pandas 2.1.4, Numba 0.62.1, OpenPyXL 3.1.5, and XlsxWriter 3.2.0

Release environment record: `results/release-v1.0.1/environment-v1.0.1.txt`

---

## Manuscript compilation

Source: [`Paper/main.tex`](Paper/main.tex)

```bash
cd Paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

A TeX Live or MiKTeX installation providing `elsarticle` and the packages declared in the source is required.

---

## BibTeX

**Manuscript**

```bibtex
@misc{Ghandali2026Preprint,
  author       = {Ghandali, Majid},
  title        = {An Explicit Evaluation of a {F}ibonacci Character Sum for
                  Primes with Full Rank of Apparition},
  year         = {2026},
  version      = {v1.0.0},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.22803009},
  url          = {https://doi.org/10.5281/zenodo.22803009}
}
```

**Software / reproducibility archive**

```bibtex
@misc{Ghandali2026FibChar,
  author       = {Ghandali, Majid},
  title        = {{FibChar v1.0.1}: Reproducibility Materials},
  year         = {2026},
  version      = {v1.0.1},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.21431565},
  url          = {https://doi.org/10.5281/zenodo.21431565}
}
```

---

## License

This repository uses a deliberate dual-license structure:

| Content | Path | License |
| --- | --- | --- |
| Code, scripts, verification outputs, and computational artifacts | Root [`LICENSE`](LICENSE); `code/`, `results/`, … | **MIT** |
| Manuscript text (LaTeX, bibliography, PDF) | [`Paper/`](Paper/); [`Paper/LICENSE`](Paper/LICENSE) | **CC BY 4.0** |

Full scope statement: [`LICENSES.md`](LICENSES.md).

---

## Author

**Majid Ghandali**<br>
Independent Researcher, Tehran, Iran<br>
Email: [majid.ghandali@gmail.com](mailto:majid.ghandali@gmail.com)<br>
ORCID: [0009-0001-1097-1770](https://orcid.org/0009-0001-1097-1770)
