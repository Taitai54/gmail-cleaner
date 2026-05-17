# Activate the UniDays OAuth client (project: totemic-beaker-493705-n2).
# Run from the repo root, then restart the app.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Copy-Item (Join-Path $root "credentials_unidays.json") (Join-Path $root "credentials.json") -Force
Write-Host "Active OAuth client: UNIDAYS (totemic-beaker-493705-n2)" -ForegroundColor Yellow
Write-Host "Restart the app to pick up the change."
