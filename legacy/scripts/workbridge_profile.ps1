# WorkBridge helper functions for the user's PowerShell profile.
# This file is dot-sourced from:
#   C:\Users\user\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1

$WorkBridgeRoot = "C:\WorkBridge"

function cdx {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Prompt
    )

    $runner = Join-Path $WorkBridgeRoot "scripts\codex_logged.ps1"
    if (-not (Test-Path $runner)) {
        Write-Error "Missing Codex logging runner: $runner"
        return
    }

    & $runner $Prompt
}

function jnl {
    $today = Get-Date -Format "yyyy-MM-dd"
    $journalDir = Join-Path $WorkBridgeRoot "docs\journal"
    $path = Join-Path $journalDir "$today.md"
    $template = Join-Path $journalDir "_template.md"

    if (-not (Test-Path $journalDir)) {
        New-Item -ItemType Directory -Path $journalDir -Force | Out-Null
    }

    if (-not (Test-Path $path)) {
        if (Test-Path $template) {
            Copy-Item $template $path
            (Get-Content $path) -replace "YYYY-MM-DD", $today | Set-Content -Path $path -Encoding UTF8
        } else {
            $defaultBody = "# $today`n`n## 오늘 한 일`n`n## 결정한 것`n`n## 막힌 것 / 내일 할 것`n"
            $defaultBody | Set-Content -Path $path -Encoding UTF8
        }
    }

    if (Get-Command code -ErrorAction SilentlyContinue) {
        code $path
    } else {
        notepad $path
    }
}

function cdx-last {
    $codexJournalDir = Join-Path $WorkBridgeRoot "docs\journal\codex"
    if (-not (Test-Path $codexJournalDir)) {
        Write-Output "No Codex journal directory found: $codexJournalDir"
        return
    }

    Get-ChildItem $codexJournalDir |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function cjnl {
    $today = Get-Date -Format "yyyy-MM-dd"
    $codexJournalDir = Join-Path $WorkBridgeRoot "docs\journal\codex"
    $path = Join-Path $codexJournalDir "$today.md"

    if (-not (Test-Path $codexJournalDir)) {
        New-Item -ItemType Directory -Path $codexJournalDir -Force | Out-Null
    }

    if (-not (Test-Path $path)) {
        $defaultBody = @"
# $today Codex 작업 로그

## 오늘 계획
-

## 오늘 결정한 것
-

## 오늘 실행한 것
-

## 오늘 Codex에 물어본 것
### Q1.

A.

결정/액션:
-

## 다음에 이어서 할 것
-
"@
        $defaultBody | Set-Content -Path $path -Encoding UTF8
    }

    if (Get-Command code -ErrorAction SilentlyContinue) {
        code $path
    } else {
        notepad $path
    }
}
