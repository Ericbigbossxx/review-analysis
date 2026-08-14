[CmdletBinding()]
param(
    [ValidateSet('DryRun','SmokeTest','Production')][string]$Mode = 'DryRun',
    [string]$RunId,
    [string]$ReportDate,
    [switch]$Resume,
    [ValidateSet('APPROVE_RUN','HOLD_RUN')][string]$ScopeDecision,
    [ValidateSet('APPROVE_RUN','HOLD_RUN')][string]$DataDecision,
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ReportDate)) { $ReportDate = Get-Date -Format 'yyyy-MM-dd' }
if ([string]::IsNullOrWhiteSpace($RunId)) { $RunId = 'WEEKLY_REVIEW_' + (Get-Date -Format 'yyyyMMdd') }
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) { $PythonPath = $venvPython }
    else { $PythonPath = 'C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe' }
}
if (-not [System.IO.Path]::IsPathRooted($PythonPath)) { throw 'PythonPath must be an absolute path.' }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw "PythonPath does not exist: $PythonPath" }
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path

$arguments = @(
    (Join-Path $PSScriptRoot 'run_weekly_review_tracker.py'),
    '--run-id', $RunId,
    '--report-date', $ReportDate,
    '--mode', $(if ($Mode -eq 'Production') { 'PRODUCTION' } elseif ($Mode -eq 'SmokeTest') { 'SMOKE_TEST' } else { 'DRY_RUN' })
)
if ($Resume) { $arguments += '--resume' }
if ($ScopeDecision) { $arguments += @('--scope-decision', $ScopeDecision) }
if ($DataDecision) { $arguments += @('--data-decision', $DataDecision) }

& $PythonPath @arguments
exit $LASTEXITCODE
