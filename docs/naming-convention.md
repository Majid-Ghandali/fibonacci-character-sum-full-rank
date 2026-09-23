# FibChar naming convention

The repository distinguishes public names from historical artifact filenames.

## Canonical public names

- Software name: `FibChar`
- Current public software release: `FibChar v1.0.1`
- Software/reproducibility DOI: `10.5281/zenodo.21431565`
- Manuscript preprint DOI: `10.5281/zenodo.22803009`

Use these forms in current README text, citation metadata, documentation, and public-facing descriptions.

## Historical artifact names

The following names are historical release identifiers and must be preserved literally:

- `code/Fibchar_v1-0-0.py`
- `code/Fibchar_v1-0-1.py`
- `results/release-v1.0.1/`

Historical release evidence, including files under `results/release-v1.0.1/`, must not be renamed, normalized, or rewritten because its byte-level identity is recorded by its release manifest and checksum file.

## Rule

Use `FibChar v1.0.1` for the public software name and version. Use historical filenames and release paths exactly as recorded when referring to immutable release artifacts.