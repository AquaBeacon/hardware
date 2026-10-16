# auto_continue.ps1  (ASCII only: PowerShell 5.1 misparses BOM-less UTF-8 Japanese)
#
# Resumes the latest Claude Code conversation after the 5-hour rate limit resets,
# and keeps re-issuing "continue" until the -Until deadline.
#
# Usage (detached):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_continue.ps1 -At "2026-07-11 10:30" -Until "2026-07-11 13:59"
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_continue.ps1 -InMinutes 300
#
# Behavior:
#   1) wait until the target time
#   2) run: claude --continue --permission-mode acceptEdits -p "continue"
#   3) on failure (limit not yet reset etc.) retry every -RetryMinutes
#   4) on success, if before -Until, issue another continue after 2 min
# Log: tools\auto_continue.log

param(
    [string]$At = "",
    [int]$InMinutes = 0,
    [string]$Until = "",
    [string]$Prompt = "continue",
    [int]$RetryMinutes = 15
)

$projectDir = Split-Path -Parent $PSScriptRoot
$logFile = Join-Path $PSScriptRoot "auto_continue.log"
$claudeExe = "C:\Users\ryupc\.local\bin\claude.exe"
if (-not (Test-Path $claudeExe)) { $claudeExe = "claude" }

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    $line | Out-File $logFile -Append -Encoding utf8
}

if ($At -ne "") {
    $target = Get-Date $At
} elseif ($InMinutes -gt 0) {
    $target = (Get-Date).AddMinutes($InMinutes)
} else {
    Write-Host "Usage: -At `"2026-07-11 10:30`" or -InMinutes 300"
    exit 1
}
if ($target -lt (Get-Date)) { $target = $target.AddDays(1) }

if ($Until -ne "") {
    $deadline = Get-Date $Until
} else {
    $deadline = Get-Date -Hour 13 -Minute 59 -Second 0
    if ($deadline -lt (Get-Date)) { $deadline = $deadline.AddDays(1) }
}

Log "waiting: first run at $target / deadline $deadline (project: $projectDir, claude: $claudeExe)"

while ((Get-Date) -lt $target) {
    $remain = ($target - (Get-Date)).TotalSeconds
    Start-Sleep -Seconds ([Math]::Min([Math]::Max($remain, 1), 60))
}

Set-Location $projectDir

$run = 0
while ((Get-Date) -lt $deadline) {
    $run++
    Log "run #$run : starting claude --continue"
    $out = & $claudeExe --continue --permission-mode acceptEdits -p $Prompt 2>&1
    $code = $LASTEXITCODE
    $out | Out-File $logFile -Append -Encoding utf8
    Log "run #$run finished (exit=$code)"

    if ((Get-Date) -ge $deadline) { break }

    $outText = ($out | Out-String)
    if ($code -ne 0 -or $outText -match 'limit|rate|usage|unavailable') {
        Log "failure or still rate-limited -> retry in $RetryMinutes min"
        Start-Sleep -Seconds ($RetryMinutes * 60)
    } else {
        Log "success -> next continue in 2 min"
        Start-Sleep -Seconds 120
    }
}

Log "deadline $deadline reached. auto_continue exiting."
