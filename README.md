An Explicit Evaluation of a Fibonacci Character Sum for Primes of Full Rank of Apparition

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Companion repository for the paper **"An Explicit Evaluation of a Fibonacci Character Sum for Primes of Full Rank of Apparition"** by Majid Ghalandali.

---

## Abstract

This repository accompanies the paper *An Explicit Evaluation of a Fibonacci Character Sum for Primes of Full Rank of Apparition* and provides a fully reproducible computational verification of the main theorem and the empirical claims recorded in the manuscript.

For an odd prime $p$, let $\chi_p$ denote the quadratic character modulo $p$, and define
$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n),
$$
where $(F_n)$ is the Fibonacci sequence and $\alpha(p)$ is the rank of apparition of $p$.

The paper proves that if
$$
\alpha(p)=p-1,
$$
then necessarily
$$
p\equiv 11 \pmod{20}
\quad\text{or}\quad
p\equiv 19 \pmod{20},
$$
and moreover
$$
S(p)=
\begin{cases}
+1,& p\equiv 11\pmod{20},\\[2mm]
-1,& p\equiv 19\pmod{20}.
\end{cases}
$$

The proof shows that in the full-rank regime the nonresidue root of $x^2-x-1$ becomes a primitive root of $\mathbb{F}_p^\times$, which reduces the Fibonacci character sum to a structural character identity. The sign is then determined by a discriminant criterion related to fifth roots of unity.

This repository contains the source code, computational verification scripts, exported tables, and reproducibility artifacts needed to reproduce the results of the paper.

---

## Main Theorem

Let $p\ge 7$ be a prime such that
$$
\alpha(p)=p-1.
$$
Then
$$
p\equiv 11 \pmod{20}
\quad\text{or}\quad
p\equiv 19 \pmod{20},
$$
and
$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n)=
\begin{cases}
+1,& p\equiv 11\pmod{20},\\[2mm]
-1,& p\equiv 19\pmod{20}.
\end{cases}
$$

---

## Proof Pipeline

The computational artifact mirrors the logical structure of the paper:

```text
[Full rank: alpha(p) = p-1]
    ↓
[p ≡ 3 (mod 4) and p ≡ ±1 (mod 5)]
    ↓
[Nonresidue root of x^2 - x - 1 is primitive]
    ↓
[Structural identity: S(p) = χ_p(α - β)]
    ↓
[Sign via fifth-root discriminant criterion]
    ↓
[Explicit value: +1 or -1]
```

---

## Repository Contents

- `paper/` — LaTeX source of the manuscript.
- `code/` — Python verification code.
- `- `data/` — Raw and processed numerical data, including prime lists, computed invariants, diagnostic tables, and metadata used to reproduce the verification pipeline.
- `results/` — CSV, tables, logs, and exported outputs.
- `docs/` — Reproducibility notes and implementation details.

---

## Reproducibility

The verification pipeline computes, for each prime $p<2{,}000{,}000$, the rank of apparition $\alpha(p)$ and the character sum
$$
S(p)=\sum_{n=1}^{p-1}\chi_p(F_n).
$$

The code uses three interchangeable backends for evaluating the quadratic character:
- quadratic residue table lookup,
- bitwise Jacobi symbol computation,
- Euler-criterion modular exponentiation.

The output includes:
- the complete list of primes tested,
- the values of $\alpha(p)$,
- the values of $S(p)$,
- diagnostic tables,
- checkpoint files,
- and a verification log for the main theorem.

The current run processed $148{,}933$ primes up to $2{,}000{,}000$ and found $26{,}407$ primes with $\alpha(p)=p-1$, all of which satisfied the main theorem with zero violations.

The verification log also confirms the empirical claims `E1`–`E10`, including:
- `E1`: $v_2(\pi)=v_2(p+1)+1$ on `DI`,
- `E2`: $\pi=4\alpha$ and $\alpha$ odd on $Z\setminus DI$,
- `E3`: $\pi=\alpha$ on `cm_only`,
- `E4`: $\alpha\mid(p+1)$ for inert primes,
- `E5`: $\alpha\mid(p-1)$ for split primes,
- `E6` and `E7`: parity of the exponent $k$ is controlled by $\chi_p(-1)$,
- `E8`: the main theorem for full-rank `cm_only` primes,
- `E9` and `E10`: additional informational regularities on selected subclasses.

---

## Citation

If you use this repository, please cite the paper and the code archive using the Zenodo DOI and the BibTeX entry in `references.bib`.

A `CITATION.cff` file is included to support automatic citation metadata on GitHub and Zenodo.

---

## License

This project is released under the MIT License. See `LICENSE` for details.

=======================

#  gitignore.py

# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class
*.so

# Environments
.env
.envrc
.venv/
venv/
env/
ENV/
env.bak/
venv.bak/

# Jupyter / IPython
.ipynb_checkpoints/
profile_default/
ipython_config.py

# Python packaging / build
.Python
build/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Python test / coverage
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache/
nosetests.xml
coverage.xml
*.cover
*.py.cover
.hypothesis/
.pytest_cache/
cover/
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.pytype/
cython_debug/
.ruff_cache/

# Project/runtime files
tempCodeRunnerFile.py
.pdm-python
.pdm-build/
.pypirc
.pixi/
__pypackages__/
marimo/_static/
marimo/_lsp/
__marimo__/
.streamlit/secrets.toml

# LaTeX / TeX auxiliary files
*.aux
*.bbl
*.bcf
*.blg
*.brf
*.fdb_latexmk
*.fls
*.idx
*.ilg
*.ind
*.lof
*.log
*.lot
*.maf
*.mtc
*.mtc0
*.mw
*.nav
*.out
*.pdfsync
*.run.xml
*.snm
*.synctex.gz
*.toc
*.xdv

# LaTeX build directories
_build/
latex.out/
latexmk-output/

# OS / editor files
.DS_Store
Thumbs.db
.idea/
.vscode/
