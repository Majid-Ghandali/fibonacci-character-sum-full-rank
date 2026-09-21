# An Explicit Evaluation of a Fibonacci Character Sum for Primes with Full Rank of Apparition

[![Zenodo Preprint DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22803009.svg)](https://doi.org/10.5281/zenodo.22803009)
[![Zenodo Code DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21431565.svg)](https://doi.org/10.5281/zenodo.21431565)
[![License: MIT (code)](https://img.shields.io/badge/License-MIT%20(code)-yellow.svg)](LICENSE)
[![License: CC BY 4.0 (paper)](https://img.shields.io/badge/License-CC%20BY%204.0%20(paper)-lightgrey.svg)](manuscript/LICENSE)

**Majid Ghandali**
Independent Researcher, Tehran, Iran
ORCID: [0009-0001-1097-1770](https://orcid.org/0009-0001-1097-1770)

---

## What this repository is

This repository hosts the **preprint manuscript** and a **minimal reproducibility package** for the computational claims in the paper (full-rank verification up to \(2\times10^6\)). The complete, long-run archive (datasets, logs, extended diagnostics) is deposited separately on Zenodo.

| Object | DOI | Role |
|:--|:--|:--|
| Preprint (this manuscript) | [10.5281/zenodo.22803009](https://doi.org/10.5281/zenodo.22803009) | Fixed version v1.0.0 (2026-09-16) |
| Preprint concept record | [10.5281/zenodo.22803008](https://doi.org/10.5281/zenodo.22803008) | Always resolves to the latest preprint version |
| Full reproducibility archive | [10.5281/zenodo.21431565](https://doi.org/10.5281/zenodo.21431565) | Complete FibChar suite, datasets, logs (`FibChar v1.0.1`) |

Do not confuse the preprint DOI with the code-archive DOI — they are two independent Zenodo records.

---

## Repository layout

```text
.
├── manuscript/
│   ├── main_full_rank.tex          # paper source
│   ├── references_full_rank.bib    # bibliography
│   ├── main_full_rank.pdf          # compiled preprint
│   └── LICENSE                     # CC BY 4.0 (manuscript text/PDF only)
├── code/
│   ├── Fibchar_v1-0-1.py           # principal implementation (mirror)
│   └── README.md                   # how to reproduce the paper's claims
├── verification/
│   ├── corollary_B1_verification.csv
│   └── README.md
├── results/                        # extended run outputs (optional)
├── README.md
├── CITATION.cff
├── LICENSE                         # MIT (code, data, scripts)
├── requirements.txt
├── compile.ps1                     # Windows / PowerShell build script
├── compile.sh                      # Linux / macOS build script
├── .gitignore
└── .gitattributes
```

> [!NOTE]
> Folder names are **lowercase** (`manuscript/`, `code/`) to match `.gitattributes` and the path-normalization rule it declares (`code/Fibchar_v1-0-1.py text eol=lf`). Git is case-sensitive on Linux/CI even where a local filesystem may not be — keep the casing exact.

---

## Main theorem (statement)

For every prime \(p\ge7\) with rank of apparition \(\alpha(p)=p-1\),

$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n)=
\begin{cases}
+1, & p\equiv11\pmod{20},\\
-1, & p\equiv19\pmod{20}.
\end{cases}
$$

---

## Computational claims and how to check them

The manuscript reports a **non-circular** verification for all primes \(p\le2\times10^6\):

| Quantity | Value |
|:--|--:|
| Primes tested | 148,933 |
| Split primes \(p\equiv\pm1\pmod5\) | 74,461 |
| Full-rank primes \(\alpha(p)=p-1\) | 26,407 |
| \(p\equiv11\pmod{20}\) | 11,755 (all match \(S=+1\)) |
| \(p\equiv19\pmod{20}\) | 14,652 (all match \(S=-1\)) |
| Violations of the formula | 0 |

**Quick check (no full re-run):** open [`verification/corollary_B1_verification.csv`](verification/corollary_B1_verification.csv).

**Full re-run:** see [`code/README.md`](code/README.md).

**Windows (PowerShell):**

```powershell
pip install -r requirements.txt
python code\Fibchar_v1-0-1.py --no-gui --self-test
python code\Fibchar_v1-0-1.py --no-gui --N 2000000 --verify-b1
```

**Linux / macOS (bash):**

```bash
pip install -r requirements.txt
python3 code/Fibchar_v1-0-1.py --no-gui --self-test
python3 code/Fibchar_v1-0-1.py --no-gui --N 2000000 --verify-b1
```

Complete long-run archive: https://doi.org/10.5281/zenodo.21431565

---

## Compile the manuscript

**Windows (PowerShell):**

```powershell
.\compile.ps1
```

**Linux / macOS (bash):**

```bash
./compile.sh
```

Or manually from `manuscript/`, on any platform:

```bash
pdflatex -interaction=nonstopmode main_full_rank.tex
bibtex main_full_rank
pdflatex -interaction=nonstopmode main_full_rank.tex
pdflatex -interaction=nonstopmode main_full_rank.tex
```

---

## Citation

**Preprint:**

```bibtex
@misc{Ghandali2026FullRankPreprint,
  author    = {Ghandali, Majid},
  title     = {An Explicit Evaluation of a {F}ibonacci Character Sum for
               Primes with Full Rank of Apparition},
  year      = {2026},
  version   = {v1.0.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22803009},
  url       = {https://doi.org/10.5281/zenodo.22803009}
}
```

**Code / data archive:**

```bibtex
@misc{Ghandali2026FibChar,
  author    = {Ghandali, Majid},
  title     = {{FibChar v1.0.1}: Reproducibility Materials},
  year      = {2026},
  version   = {v1.0.1},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21431565},
  url       = {https://doi.org/10.5281/zenodo.21431565}
}
```

See also [`CITATION.cff`](CITATION.cff).

---

## License

Copyright (C) 2026 Majid Ghandali.

This repository is a **research compendium** with dual licensing:

| Content | Path | License |
|:--|:--|:--|
| Software, scripts, verification outputs, computational artifacts | repository root (`code/`, `verification/`, `results/`, …) | **MIT** — see [`LICENSE`](LICENSE) |
| Manuscript text (LaTeX, bibliography, compiled PDF) | [`manuscript/`](manuscript/) | **CC BY 4.0** — see [`manuscript/LICENSE`](manuscript/LICENSE) |

This split follows common practice for reproducible papers: permissive reuse of code, and standard scholarly attribution for the article text. The two Zenodo records remain independent (code DOI `10.5281/zenodo.21431565` via GitHub-release integration; preprint DOI `10.5281/zenodo.22803009` via manual deposit).
