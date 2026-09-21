$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $Root "Paper")

if (-not (Test-Path ".\main.tex")) {
  Write-Error "main.tex not found in Paper\. Flatten Paper\PAPER if needed."
}

Get-ChildItem -ErrorAction SilentlyContinue *.aux,*.bbl,*.blg,*.log,*.out,*.toc,*.synctex.gz |
  Remove-Item -Force -ErrorAction SilentlyContinue

pdflatex -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) { Write-Warning "pdflatex pass 1 had errors (see main.log)" }

bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex

if (Test-Path ".\main.pdf") {
  $pdf = Get-Item ".\main.pdf"
  Write-Host "OK: $($pdf.FullName)  ($($pdf.Length) bytes)"
} else {
  Write-Error "PDF not produced. Check Paper\main.log"
}
