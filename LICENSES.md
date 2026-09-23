# License Scope

This repository intentionally uses two licenses because its software and its scholarly manuscript are different classes of work.

## 1. Code and computational materials: MIT License

The root [LICENSE](LICENSE) applies to the repository's code and computational materials, including Python source code in `code/`, scripts, computational documentation, configuration, and generated computational materials unless a more specific license notice accompanies an item.

The machine-readable software citation record is [CITATION.cff](CITATION.cff). It identifies FibChar v1.0.1 and its software/reproducibility archive.

## 2. Manuscript: CC BY 4.0

The manuscript materials in [Paper/](Paper/) are licensed under the Creative Commons Attribution 4.0 International license. The authoritative manuscript license text is [Paper/LICENSE](Paper/LICENSE).

This scope includes the manuscript source, bibliography, compiled manuscript PDF, and the manuscript citation record [Paper/CITATION.cff](Paper/CITATION.cff), unless a file in `Paper/` states otherwise.

## 3. Frozen release evidence

`results/release-v1.0.1/` is a preserved historical reproducibility bundle. Its files remain within the computational-materials scope above, but their published byte sequence is also fixed by `SHA256SUMS-v1.0.1.txt`.

For reproducibility and provenance, do not normalize, rename, edit, or overwrite files in that directory. Create new output directories for new runs.

## 4. Third-party software and dependencies

The repository depends on third-party software and Python packages. Their licenses remain their own; this file does not replace, modify, or relicense third-party terms.

## 5. Citation distinction

License scope and citation purpose are separate questions:

- Cite the manuscript DOI for the mathematical result and proof.
- Cite the FibChar DOI for the software, computational data, and reproducibility reruns.

See the README for the two DOI records and their intended use.
