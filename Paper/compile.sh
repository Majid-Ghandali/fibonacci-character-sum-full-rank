#!/usr/bin/env bash
# compile.sh -- Linux/macOS build script (bash equivalent of compile.ps1)
#
# Compiles manuscript/main_full_rank.tex to PDF using the standard
# pdflatex -> bibtex -> pdflatex -> pdflatex sequence required for
# bibliography and cross-reference resolution.
#
# Usage:
#   ./compile.sh
#
# Requires: pdflatex, bibtex (any standard TeX Live / MacTeX install)

set -euo pipefail

# Resolve paths relative to this script's own location, so it works
# regardless of the caller's current working directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
MANUSCRIPT_DIR="${SCRIPT_DIR}/manuscript"
TEX_BASENAME="main_full_rank"

if [[ ! -d "${MANUSCRIPT_DIR}" ]]; then
    echo "error: manuscript/ directory not found at ${MANUSCRIPT_DIR}" >&2
    exit 1
fi

if [[ ! -f "${MANUSCRIPT_DIR}/${TEX_BASENAME}.tex" ]]; then
    echo "error: ${TEX_BASENAME}.tex not found in ${MANUSCRIPT_DIR}" >&2
    exit 1
fi

for tool in pdflatex bibtex; do
    if ! command -v "${tool}" &>/dev/null; then
        echo "error: '${tool}' not found on PATH. Install TeX Live (Linux) or MacTeX (macOS)." >&2
        exit 1
    fi
done

cd "${MANUSCRIPT_DIR}"

echo "[1/4] pdflatex (pass 1) ..."
pdflatex -interaction=nonstopmode "${TEX_BASENAME}.tex" >/dev/null

echo "[2/4] bibtex ..."
bibtex "${TEX_BASENAME}"

echo "[3/4] pdflatex (pass 2) ..."
pdflatex -interaction=nonstopmode "${TEX_BASENAME}.tex" >/dev/null

echo "[4/4] pdflatex (pass 3, resolves cross-references) ..."
pdflatex -interaction=nonstopmode "${TEX_BASENAME}.tex" >/dev/null

if [[ -f "${TEX_BASENAME}.pdf" ]]; then
    echo ""
    echo "Success: ${MANUSCRIPT_DIR}/${TEX_BASENAME}.pdf"
else
    echo ""
    echo "error: build finished but ${TEX_BASENAME}.pdf was not produced." >&2
    echo "       Check ${TEX_BASENAME}.log for details." >&2
    exit 1
fi
