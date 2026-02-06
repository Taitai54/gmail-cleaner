# Gmail Cleaner - Windows Desktop Shortcut Creator
# Run this once to create a clickable shortcut on your desktop
#
# Usage: Right-click this file -> "Run with PowerShell"

$ProjectDir = $PSScriptItem.DirectoryName
if (-not $ProjectDir) {
    $ProjectDir = (Get-Location).Path
}

$ShortcutName = "Gmail Cleaner"
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "$ShortcutName.lnk"
$TargetPath = Join-Path $ProjectDir "run.bat"

# Create the shortcut
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.WindowStyle = 1  # Normal window
$Shortcut.Description = "Gmail Cleaner - Email management tool"
$Shortcut.Save()

Write-Host "Shortcut created on your desktop: $ShortcutPath"
Write-Host ""
Write-Host "Double-click '$ShortcutName' on your desktop to launch Gmail Cleaner."
Write-Host ""
Read-Host "Press Enter to close"
