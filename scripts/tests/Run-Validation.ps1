# Run Validation for Nexus Core
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Validation Execution
# Test ID: PS-TEST-002
#
# Purpose: Invoke validation agent and parse results
#
# Usage:
#   .\Run-Validation.ps1 -DocId "test.pdf__ABC123..."
#   .\Run-Validation.ps1 -DocId "test.pdf__ABC123..." -OutputPath "C:\Reports"
#   .\Run-Validation.ps1 -DocId "test.pdf__ABC123..." -Verbose
#
# Requirements from spec:
# - Invoke Docker validation container with specific doc_id
# - Monitor validation execution
# - Parse validation report (JSON)
# - Surface PASS/FAIL determination
# - Extract and display validation checks
# - Exit code: 0 (PASS), 1 (FAIL), 2 (validation error)

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,

    [Parameter(Mandatory=$false)]
    [string]$OutputPath,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Import common helper functions
. $PSScriptRoot\..\Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$TRANSFER_STATION = "E:\Transfer_Station"
$VALIDATION_TIMEOUT = 60  # seconds

# ==========================================================================
# Helper Functions
# ==========================================================================

function Get-ValidationReport {
    param([string]$DocId)

    $reportPath = Join-Path $TRANSFER_STATION "artifacts\reports\$DocId\validation_report.json"

    if (-not (Test-Path $reportPath)) {
        return $null
    }

    try {
        $reportContent = Get-Content $reportPath -Raw | ConvertFrom-Json
        return $reportContent
    } catch {
        Write-Error "Failed to parse validation report: $_"
        return $null
    }
}

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Running Validation for doc_id: $DocId"
Write-Host ""

# Step 1: Verify Docker is running
if (-not (Test-DockerRunning)) {
    Write-Error "Docker Desktop is not running"
    exit 2
}

# Step 2: Check if nexus_validator container is running
$validatorStatus = Get-ContainerStatus -ContainerName "nexus_validator"

if ($validatorStatus.Status -ne "running") {
    Write-Error "nexus_validator container is not running"
    Write-Host "  Status: $($validatorStatus.Status)"
    Write-Host "  Please start the environment with: .\Start-NexusEnv.ps1"
    exit 2
}

# Step 3: Execute validator via Docker
Write-Host "  Executing validator..."
Write-Host "  ⏳ Running 9 validation checks..."
Write-Host ""

try {
    $output = docker exec nexus_validator python -m nexus_core.validation.cli --doc-id $DocId 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Validation execution failed"
        Write-Host "  Docker exit code: $LASTEXITCODE"
        Write-Host "  Output:"
        Write-Host $output
        exit 2
    }
} catch {
    Write-Error "Failed to execute validator: $_"
    exit 2
}

# Step 4: Wait for validation report to be written
Start-Sleep -Seconds 2

# Step 5: Parse validation report
$report = Get-ValidationReport -DocId $DocId

if ($null -eq $report) {
    Write-Error "Validation report not found"
    Write-Host "  Expected location: $TRANSFER_STATION\artifacts\reports\$DocId\validation_report.json"
    exit 2
}

# Step 6: Display validation results
Write-Step "Validation Report"
Write-Host ""

$status = $report.status
$statusDisplay = if ($status -eq "PASS") {
    "$status ✓"
} else {
    "$status ✗"
}

$statusColor = if ($status -eq "PASS") { "Green" } else { "Red" }

Write-Host "Status: $statusDisplay" -ForegroundColor $statusColor
Write-Host ""

# Display checks
Write-Host "Checks:"
foreach ($check in $report.checks) {
    $checkIndicator = if ($check.passed) { "✓" } else { "✗" }
    $checkColor = if ($check.passed) { "Green" } else { "Red" }

    $checkName = $check.check_name.PadRight(30)
    $message = $check.message

    Write-Host "  $checkIndicator $checkName`: $message" -ForegroundColor $checkColor
}

# Display summary
Write-Host ""
Write-Host "Summary:"
$passedCount = ($report.checks | Where-Object { $_.passed }).Count
$failedCount = ($report.checks | Where-Object { -not $_.passed }).Count
$totalCount = $report.checks.Count

Write-Host "  Total Checks: $totalCount"
Write-Host "  Passed: $passedCount" -ForegroundColor Green
if ($failedCount -gt 0) {
    Write-Host "  Failed: $failedCount" -ForegroundColor Red
} else {
    Write-Host "  Failed: $failedCount"
}

# Check for warnings
if ($report.PSObject.Properties.Name -contains "warnings" -and $report.warnings.Count -gt 0) {
    Write-Host "  Warnings: $($report.warnings.Count)" -ForegroundColor Yellow
}

Write-Host ""

# Step 7: Show verbose output if requested
if ($Verbose) {
    Write-Step "Detailed Check Results"
    Write-Host ""

    foreach ($check in $report.checks) {
        Write-Host "  === $($check.check_name) ===" -ForegroundColor Cyan
        Write-Host "  Passed: $($check.passed)"
        Write-Host "  Message: $($check.message)"

        if ($check.PSObject.Properties.Name -contains "details" -and $null -ne $check.details) {
            Write-Host "  Details:"
            Write-Host "    $($check.details | ConvertTo-Json -Depth 3)"
        }

        Write-Host ""
    }
}

# Step 8: Copy report to output path if specified
if ($OutputPath) {
    if (-not (Test-Path $OutputPath)) {
        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    }

    $sourceReport = Join-Path $TRANSFER_STATION "artifacts\reports\$DocId\validation_report.json"
    $destReport = Join-Path $OutputPath "validation_report_$DocId.json"

    Copy-Item -Path $sourceReport -Destination $destReport -Force
    Write-Success "Report copied to: $destReport"
    Write-Host ""
}

# Step 9: Display report location
$reportPath = Join-Path $TRANSFER_STATION "artifacts\reports\$DocId\validation_report.json"
Write-Host "Report saved to: $reportPath"
Write-Host ""

# Exit with appropriate code
if ($status -eq "PASS") {
    exit 0  # PASS
} elseif ($status -eq "FAIL") {
    exit 1  # FAIL
} else {
    exit 2  # Validation error/unknown status
}
