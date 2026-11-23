# Mufti AI setup check ("doctor"): shows what is ready, what is missing, and the exact fix
# (English + Hinglish). Read-only: it never starts, stops, installs or rebuilds anything.
#   .\doctor.ps1          human-readable report
#   .\doctor.ps1 --json   machine-readable report (for another AI or a script)
Set-Location $PSScriptRoot
if (!(Test-Path '.venv/Scripts/python.exe')) {
  Write-Host '[FAIL] Python environment missing. Run:  python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
  exit 1
}
& .venv/Scripts/python.exe -m app.core.setup_check @args
