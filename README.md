# An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition

[![GitHub Release](https://img.shields.io/github/v/release/Majid-Ghandali/fibonacci-character-sum-full-rank?display_name=tag\&sort=semver)](https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank/releases)
[![Manuscript DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22803009.svg)](https://doi.org/10.5281/zenodo.22803009)
[![Code Archive DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21431565.svg)](https://doi.org/10.5281/zenodo.21431565)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

> **Research compendium** — manuscript source, verification software, computational results, and reproducibility records
> **Majid Ghandali** · Independent Researcher, Tehran, Iran · 2026

This repository contains the source of the mathematical manuscript together with the computational software, finite-range verification data, release records, and reproducibility materials associated with:

> *An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition.*

The manuscript is archived as preprint **v1_0_0** on Zenodo under DOI `10.5281/zenodo.22803009`. The corresponding computational reproducibility release **FibChar v1_0_1** is archived separately under DOI `10.5281/zenodo.21431565`.

> **Proof versus computation.**
> The mathematical theorem is proved in the manuscript. The computations in this repository provide finite-range verification of the stated identities, structural conditions, and reported numerical results; they are not a substitute for the proof.

---

## Status and release identity

| Item                    | Value                                                                            |
| :---------------------- | :------------------------------------------------------------------------------- |
| Manuscript              | **v1_0_0** · 2026-09-16                                                          |
| Manuscript DOI          | `10.5281/zenodo.22803009`                                                        |
| Computational release   | **FibChar v1_0_1** · 2026-07-17                                                  |
| Code archive DOI        | `10.5281/zenodo.21431565`                                                        |
| Verification bound      | Every prime $p\le 2{,}000{,}000$ in the reported run                           |
| Current program         | [`code/Fibchar_v1_0_1.py`](code/Fibchar_v1_0_1.py)                               |
| Headline verification   | [`results/corollary_B1_verification.csv`](results/corollary_B1_verification.csv) |
| Full committed database | [`results/fib_char_db_N2000000.csv`](results/fib_char_db_N2000000.csv)           |
| Release records         | [`results/release-v1_0_1/`](results/release-v1_0_1/)                             |

### Citation roles

* **Mathematics, theorem, and proof:** cite the manuscript DOI.
* **Software, computational data, and reproducibility release:** cite the FibChar v1_0_1 DOI.
* **Exact release contents:** use the versioned release archive together with its manifest and checksums.

The manuscript and computational materials are maintained as separate citable records.

---

## Overview

The principal object is the quadratic-character sum

$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n),
$$

where $F_n$ is the Fibonacci sequence and $\chi_p$ denotes the quadratic character modulo an odd prime $p$, with

$$
\chi_p(0)=0.
$$

The paper studies the full-rank regime

$$
\alpha(p)=p-1,
$$

where $\alpha(p)$ is the rank of apparition of $p$ in the Fibonacci sequence.

Under this hypothesis, the paper derives an explicit evaluation of the character sum $S(p)$.

---

## Main theorem

Let $p\ge7$ be prime and suppose that

$$
\alpha(p)=p-1.
$$

Then

$$
p\equiv11\pmod{20}
\quad\text{or}\quad
p\equiv19\pmod{20},
$$

and

$$
S(p)
=
\sum_{n=1}^{p-1}\chi_p(F_n)
=
\begin{cases}
+1,&p\equiv11\pmod{20},\\[2mm]
-1,&p\equiv19\pmod{20}.
\end{cases}
$$

In the full-rank setting, if $r_-$ denotes the quadratic-nonresidue root and $r_+$ the quadratic-residue root of

$$
x^2-x-1
$$

in $\mathbb F_p$, the proof obtains the structural identity

$$
S(p)=\chi_p(r_--r_+).
$$

The full-rank hypothesis yields the primitive-root structure required for this reduction, and the remaining sign is determined through the cyclotomic/discriminant argument developed in the manuscript.

For the complete hypotheses, definitions, lemmas, and proof, see [`Paper/main.tex`](Paper/main.tex).

---

## Scientific mechanism

The proof can be summarized schematically as

```text
Full-rank condition
        α(p) = p − 1
                │
                ▼
Congruence constraints
 p ≡ 3 (mod 4),  p ≡ ±1 (mod 5)
                │
                ▼
Primitive-root structure
nonresidue root r_- of x²−x−1
                │
                ▼
Structural reduction
 S(p) = χ_p(r_- − r_+)
                │
                ▼
Cyclotomic / discriminant criterion
                │
                ▼
Explicit evaluation
 S(p) = +1 or −1 according to p (mod 20)
```

The computational suite checks the corresponding arithmetic conditions and identities over the finite verification range.

---

## Verification scope

The reported full-range computation covers every prime

$$
p\le2{,}000{,}000.
$$

The reported run processed:

| Quantity                                     |   Value |
| :------------------------------------------- | ------: |
| Primes tested                                | 148,933 |
| Full-rank primes $\alpha(p)=p-1$           |  26,407 |
| Full-rank primes with $p\equiv11\pmod{20}$ |  11,755 |
| Full-rank primes with $p\equiv19\pmod{20}$ |  14,652 |
| Main-theorem mismatches                      |   **0** |

The committed headline result is:

[`results/corollary_B1_verification.csv`](results/corollary_B1_verification.csv)

The filename is retained for release compatibility. The manuscript and current computational documentation identify the corresponding mathematical statement as the **Main Theorem**.

The complete committed database is:

[`results/fib_char_db_N2000000.csv`](results/fib_char_db_N2000000.csv)

These are finite computational results and should be interpreted as reproducibility and consistency evidence, not as numerical proofs.

---

## Reproducibility release v1_0_1

The current computational release is:

> **FibChar v1_0_1 — Reproducibility Release**

Archived under:

`10.5281/zenodo.21431565`

The release-specific materials are stored in:

```text
results/release-v1_0_1/
```

The release record contains, among other materials:

```text
results/release-v1_0_1/
├── MANIFEST.md
├── SHA256SUMS-v1_0_1.txt
├── self-test-v1_0_1.log
├── smoke-N10000.log
├── cli-help-v1_0_1.txt
├── environment-v1_0_1.txt
├── version-v1_0_1.txt
├── fib_char_N10000_db.csv
├── fib_char_N10000_empirical_claims.csv
├── fib_char_N10000_main_theorem.csv
├── fib_char_N10000_report.txt
├── fib_char_N10000_report.xlsx
├── fib_char_N10000_root_order_sign_checks.csv
├── fib_char_N10000_summary.json
└── latex_tables/
```

The manifest and checksum file provide a fixed record of the release contents.

See [`docs/reproducibility.md`](docs/reproducibility.md) for the detailed reproduction procedure.

---

## Quick start

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank.git
cd fibonacci-character-sum-full-rank

python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\Activate.ps1     # Windows PowerShell

python -m pip install --upgrade pip
python -m pip install -r Requirements.txt
```

Run the deterministic self-test:

```bash
python code/Fibchar_v1_0_1.py --no-gui --self-test
```

The self-test uses the five fixed Appendix-A examples

```text
11, 19, 31, 59, 79
```

and checks four invariants for each example:

1. the computed character sum agrees with the expected Appendix-A value;
2. $\alpha(p)=p-1$;
3. the arithmetic signature is `cm_only`;
4. $T_\alpha(p)=S_p$ in the full-rank case.

A successful run ends with:

```text
[OK] Self-test PASSED -- all 5 examples x 4 invariants verified.
```

A nonzero process exit status indicates failure.

---

## Full verification

To reproduce the sequential verification through $p=2{,}000{,}000$:

```bash
python code/Fibchar_v1_0_1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --out-dir results
```

To resume an interrupted sequential run:

```bash
python code/Fibchar_v1_0_1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --resume \
  --out-dir results
```

For a multi-process run:

```bash
python code/Fibchar_v1_0_1.py \
  --no-gui \
  --N 2000000 \
  --verify-b1 \
  --parallel \
  --workers 8 \
  --chunk-size 5000 \
  --out-dir results
```

Parallel mode does not use checkpoint/resume.

On Windows PowerShell:

```powershell
python code\Fibchar_v1_0_1.py --no-gui --self-test

python code\Fibchar_v1_0_1.py `
  --no-gui `
  --N 2000000 `
  --verify-b1 `
  --out-dir results
```

For the complete command-line interface:

```bash
python code/Fibchar_v1_0_1.py --help
```

The archived CLI record is retained at:

```text
results/release-v1_0_1/cli-help-v1_0_1.txt
```

---

## What the program computes

The verification suite distinguishes the following quantities.

The manuscript sum is

$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n).
$$

The rank-truncated sum is

$$
T_\alpha(p)=\sum_{n=1}^{\alpha(p)}\chi_p(F_n),
$$

and the full Pisano-period sum computed by the program is

$$
S_p=\sum_{n=1}^{\pi(p)}\chi_p(F_n).
$$

In the full-rank regime,

$$
\alpha(p)=p-1
\quad\text{and}\quad
\pi(p)=p-1,
$$

so the quantities relevant to the main theorem coincide.

Outside the full-rank regime, these sums need not agree. The implementation therefore keeps them as distinct quantities rather than conflating them.

For each prime in the computational range, the program can also compute:

* the rank of apparition $\alpha(p)$;
* the Pisano period $\pi(p)$;
* $v_2(\pi(p))$;
* the ratio $\pi(p)/\alpha(p)$;
* the arithmetic signature determined by $\chi_p(-1)$ and $\chi_p(5)$;
* the value $s=F_{\alpha(p)+1}\pmod p$;
* $\chi_p(s)$;
* positive, negative, and zero character counts;
* the main-theorem verification conditions;
* auxiliary empirical diagnostics.

The auxiliary empirical observations are computational diagnostics and should not be interpreted as additional proved results unless explicitly incorporated and proved in the manuscript.

---

## Computational backends

The v1_0_1 program provides three arithmetic backends for the Fibonacci walk:

| Backend | Character evaluation                   | Memory profile |
| :------ | :------------------------------------- | :------------- |
| A       | Quadratic-residue lookup table         | $O(p)$       |
| B       | Bitwise Jacobi evaluation              | $O(1)$       |
| C       | Euler-criterion modular exponentiation | $O(1)$       |

The implementation dispatches between these backends according to configurable thresholds.

The program uses Numba when available and falls back to pure Python where supported.

---

## Requirements

The supported Python baseline is:

```text
Python 3.11+
```

The required packages are:

```text
numpy
pandas
```

Optional components include:

* `numba` for JIT acceleration;
* `pyarrow` or `fastparquet` for Parquet checkpoint support;
* `openpyxl` for XLSX output;
* `tkinter` for the graphical interface.

The exact tested environment for the archived release is recorded in:

```text
results/release-v1_0_1/environment-v1_0_1.txt
```

The package requirements are specified in:

[`Requirements.txt`](Requirements.txt)

---

## Repository structure

```text
.
├── Paper/                              # Manuscript source
│   ├── main.tex
│   └── references.bib
│
├── code/                               # Versioned computational programs
│   ├── Fibchar_v1-0-0.py
│   └── Fibchar_v1_0_1.py              # Current release entry point
│
├── docs/                               # Reproducibility documentation
│   └── reproducibility.md
│
├── results/                            # Computational artifacts
│   ├── corollary_B1_verification.csv
│   ├── fib_char_db_N2000000.csv
│   └── release-v1_0_1/
│
├── CITATION.cff                        # Machine-readable citation metadata
├── LICENSE                             # CC BY 4.0
├── Requirements.txt
├── README.md
├── .gitignore
└── .gitattributes
```

The release-specific evidence is concentrated under:

```text
results/release-v1_0_1/
```

The manuscript source remains under:

```text
Paper/
```

and the executable verification suite under:

```text
code/
```

---

## Reproducibility documentation

The detailed computational protocol is documented in:

[`docs/reproducibility.md`](docs/reproducibility.md)

It records:

* the tested software environment;
* installation requirements;
* the principal verification commands;
* sequential checkpoint/resume behavior;
* parallel execution;
* generated output files;
* the distinction between $S(p)$, $T_\alpha(p)$, and $S_p$;
* character-evaluation backends;
* the reported finite-range computational summary.

The release archive additionally preserves logs, manifests, environment information, generated tables, and checksums.

---

## Integrity verification

The v1_0_1 release includes:

```text
results/release-v1_0_1/SHA256SUMS-v1_0_1.txt
```

and the corresponding release manifest:

```text
results/release-v1_0_1/MANIFEST.md
```

On Linux or macOS:

```bash
cd results/release-v1_0_1
sha256sum -c SHA256SUMS-v1_0_1.txt
```

On Windows PowerShell, an individual file can be checked with:

```powershell
Get-FileHash .\results\release-v1_0_1\self-test-v1_0_1.log -Algorithm SHA256
```

The resulting digest can then be compared with the corresponding entry in `SHA256SUMS-v1_0_1.txt`.

---

## Compile the manuscript

The manuscript source is:

[`Paper/main.tex`](Paper/main.tex)

From the `Paper/` directory:

```bash
cd Paper

pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

The source uses the `elsarticle` document class and the packages declared by the manuscript source.

A TeX Live or MiKTeX installation containing the required packages is needed for local compilation.

---

## Zenodo archives

### Manuscript

**An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition**

* Version: **v1_0_0**
* Resource type: **Preprint**
* Published: **2026-09-16**
* DOI: `10.5281/zenodo.22803009`

### Computational reproducibility release

**FibChar v1_0_1**

* Release: **v1_0_1**
* DOI: `10.5281/zenodo.21431565`

The manuscript archive and computational archive serve different citation purposes:

* cite the **manuscript DOI** for the mathematical result and proof;
* cite the **FibChar DOI** for software, computational data, and reproducibility reruns.

---

## Citation

Please use [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

### Manuscript

```bibtex
@article{Ghandali2026,
  author       = {Ghandali, Majid},
  title        = {An Explicit Evaluation of a Fibonacci Character Sum
                  for Primes with Full Rank of Apparition},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {v1_0_0},
  doi          = {10.5281/zenodo.22803009},
  url          = {https://doi.org/10.5281/zenodo.22803009}
}
```

### Computational release

```bibtex
@misc{Ghandali2026FibChar,
  author       = {Ghandali, Majid},
  title        = {FibChar v1_0_1: Reproducibility Materials for
                  An Explicit Evaluation of a Fibonacci Character Sum
                  for Primes with Full Rank of Apparition},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {v1_0_1},
  doi          = {10.5281/zenodo.21431565},
  url          = {https://doi.org/10.5281/zenodo.21431565}
}
```

When citing the mathematical result, cite the manuscript. When citing software, computational data, or a reproducibility rerun, cite the corresponding FibChar release.

---

## License

The repository's current root `LICENSE` file contains the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.

Accordingly, the repository currently identifies its licensed material under:

> **CC BY 4.0 — Creative Commons Attribution 4.0 International**

See [`LICENSE`](LICENSE) for the complete license text.

The license notice identifies:

```text
Copyright (C) 2026 Majid Ghandali.
```

The manuscript's machine-readable citation metadata likewise identifies the manuscript license as:

```yaml
license: "CC-BY-4.0"
```

Any future separation of manuscript licensing from software licensing should be accompanied by explicit license files for the respective materials and should be reflected in this README only after those files have been added to the repository.

---

## Author

**Majid Ghandali**
Independent Researcher, Tehran, Iran

Email: [majid.ghandali@gmail.com](mailto:majid.ghandali@gmail.com)
ORCID: [0009-0001-1097-1770](https://orcid.org/0009-0001-1097-1770)
