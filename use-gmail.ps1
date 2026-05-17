# Activate the Gmail OAuth client (project: gmail-api-for-chat-llm).
# Run from the repo root, then restart the app.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Copy-Item (Join-Path $root "credentials_gmail.json") (Join-Path $root "credentials.json") -Force
Write-Host "Active OAuth client: GMAIL (gmail-api-for-chat-llm)" -ForegroundColor Green
Write-Host "Restart the app to pick up the change."
