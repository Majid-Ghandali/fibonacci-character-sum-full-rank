

A Fibonacci Character Sum Identity for Primes of Full Rank of Apparition

Companion repository for the paper

"A Fibonacci Character Sum Identity for Primes of Full Rank of Apparition"

by Majid Ghandali.

Abstract

This repository accompanies the paper A Fibonacci Character Sum Identity for Primes of Full Rank of Apparition and provides a fully reproducible computational verification of the main theorem together with the numerical evidence reported in the manuscript.

For an odd prime (p), let (\chi_p) denote the quadratic character modulo (p), and define

[S(p)=\sum_{n=1}^{p-1}\chi_p(F_n),]

where (F_n) is the Fibonacci sequence and (\alpha(p)) denotes the rank of apparition of (p).

The paper proves that whenever

[\alpha(p)=p-1,]

one necessarily has

[p\equiv 11 \pmod{20}\qquad\text{or}\qquadp\equiv 19 \pmod{20},]

and furthermore

[S(p)=\begin{cases}+1,& p\equiv 11\pmod{20},\[2mm]-1,& p\equiv 19\pmod{20}.\end{cases}]

The proof shows that, in the full-rank regime, the nonresidue root of

[x^2-x-1]

becomes a primitive root of (\mathbb F_p^\times), reducing the character sum to a structural quadratic-character identity. The sign is then determined by a discriminant criterion involving fifth roots of unity.

The repository contains all source code, computational verification scripts, numerical outputs, and reproducibility materials required to reproduce the results.

Main Theorem

Let (p\ge 7) be a prime satisfying

[\alpha(p)=p-1.]

Then

[p\equiv 11 \pmod{20}\qquad\text{or}\qquadp\equiv 19 \pmod{20},]

and

[ S(p)=\sum_{n=1}^{p-1}\chi_p(F_n)

\begin{cases}+1,& p\equiv 11\pmod{20},\[2mm]-1,& p\equiv 19\pmod{20}.\end{cases}]

Proof Structure

The computational artifact mirrors the logical structure of the proof.

Full rank condition:
α(p) = p − 1
          ↓
p ≡ 3 (mod 4)
and
p ≡ ±1 (mod 5)
          ↓
Nonresidue root of
x² − x − 1
is primitive
          ↓
Structural identity

S(p)=χp(α−β)

          ↓
Fifth-root discriminant criterion
          ↓
Explicit sign

S(p)=±1


Repository Layout

paper/
    LaTeX source of the manuscript

code/
    Verification programs

data/
    Raw and processed datasets

results/
    Generated outputs and logs

docs/
    Reproducibility documentation


Repository Contents

paper/

LaTeX source files of the manuscript, including:

article source,

bibliography,

tables,

figures,

supplementary material used for submission.

code/

Python implementation of the verification framework, including:

rank-of-apparition computations,

Fibonacci character-sum evaluation,

diagnostic tests,

empirical verification routines.

data/

Input and derived datasets used throughout the project:

prime lists,

computed invariants,

intermediate tables,

metadata required for reproducibility.

results/

Generated outputs of the computational pipeline:

CSV files,

TXT reports,

XLSX spreadsheets,

verification logs,

publication-ready tables.

docs/

Supporting documentation, including:

reproducibility instructions,

implementation notes,

version history,

project documentation.

Reproducibility

The verification framework computes, for every prime

[p<2,000,000,]

the rank of apparition (\alpha(p)) together with the Fibonacci character sum

[S(p)=\sum_{n=1}^{p-1}\chi_p(F_n).]

To evaluate the quadratic character efficiently, the implementation supports three interchangeable backends:

quadratic-residue lookup tables,

bitwise Jacobi-symbol computation,

Euler-criterion modular exponentiation.

The verification outputs include:

complete prime lists,

computed values of (\alpha(p)),

computed values of (S(p)),

diagnostic tables,

checkpoint files,

execution logs,

empirical verification reports.

Current Verification Record

The current computation processed

[148,933]

primes up to

[2,000,000.]

Among them,

[26,407]

primes satisfy

[\alpha(p)=p-1.]

All such primes satisfy the main theorem with zero observed violations.

Empirical Observations

The verification log additionally records the empirical observations E1–E10.

ObservationDescription

E1

(v_2(\pi)=v_2(p+1)+1) on DI

E2

(\pi=4\alpha) and (\alpha) odd on (Z\setminus DI)

E3

(\pi=\alpha) on cm_only

E4

(\alpha\mid(p+1)) for inert primes

E5

(\alpha\mid(p-1)) for split primes

E6

parity law for exponent (k) controlled by (\chi_p(-1))

E7

complementary parity law for (k)

E8

full-rank sign theorem on cm_only

E9

additional structural regularities

E10

additional informational regularities

These observations are included for documentation purposes and remain logically separate from the proven theorem.

Installation

Clone the repository:

git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY


Install dependencies:

pip install -r requirements.txt


Run the verification suite:

python code/main.py


Citation

If you use this repository, please cite:

the accompanying paper,

the archived reproducibility package.

Citation metadata is provided through:

CITATION.cff


and the corresponding BibTeX entries.

License

This project is distributed under the MIT License.

See:

LICENSE


for details.

Release Information

The reproducibility archive associated with this repository is maintained through Zenodo.

The DOI corresponding to the archived release will be recorded here once the release is finalized.

Version: v1.0.1
DOI: pending release


چند نکته حرفه‌ای که در این نسخه اعمال شده و ارزش واقعی دارند
