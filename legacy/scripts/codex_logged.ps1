param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Prompt
)

$WorkBridgeRoot = "C:\WorkBridge"
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logDir = Join-Path $WorkBridgeRoot "docs\journal\codex"
$logFile = Join-Path $logDir "$timestamp.txt"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

"=== TIMESTAMP ===" | Out-File $logFile -Encoding UTF8
$timestamp | Out-File $logFile -Append -Encoding UTF8
"`n=== PROMPT ===" | Out-File $logFile -Append -Encoding UTF8
$Prompt | Out-File $logFile -Append -Encoding UTF8
"`n=== OUTPUT ===" | Out-File $logFile -Append -Encoding UTF8

codex exec --sandbox workspace-write $Prompt 2>&1 |
    Tee-Object -FilePath $logFile -Append

Write-Host "`nLog saved: $logFile" -ForegroundColor Green
