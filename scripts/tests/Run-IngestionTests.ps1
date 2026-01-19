# Run Ingestion Tests for Nexus Core
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Test Orchestration
# Test ID: PS-TEST-003
#
# Purpose: Standardized wrapper for ingestion test execution
#
# Usage:
#   .\Run-IngestionTests.ps1 -TestPDF "test.pdf"
#   .\Run-IngestionTests.ps1 -TestPDF "test.pdf" -System "pathfinder_1e" -Tier "PREMIUM"
#   .\Run-IngestionTests.ps1 -TestPDF "test.pdf" -Timeout 600 -SkipCleanup
#   .\Run-IngestionTests.ps1 -TestPDF "test.pdf" -Verbose -SaveLogs
#
# Requirements from spec:
# - Provide consistent interface for running tests
# - Handle test phase selection
# - Manage test configuration
# - Aggregate logging
# - Surface exit codes

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$TestPDF,

    [Parameter(Mandatory=$false)]
    [string]$DocId,

    [Parameter(Mandatory=$false)]
    [ValidateSet("pathfinder_1e", "cyberpunk_red", "starfinder", "dnd_5e")]
    [string]$System = "pathfinder_1e",

    [Parameter(Mandatory=$false)]
    [ValidateSet("FREE", "BASIC", "PREMIUM")]
    [string]$Tier = "PREMIUM",

    [Parameter(Mandatory=$false)]
    [int]$Timeout = 600,

    [Parameter(Mandatory=$false)]
    [switch]$SkipCleanup,

    [Parameter(Mandatory=$false)]
    [switch]$SaveLogs,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Import common helper functions
. $PSScriptRoot\..\..\scripts\Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$API_BASE_URL = "http://localhost:8000"
$TRANSFER_STATION = "E:\Transfer_Station"
$ADMIN_USER_ID = "test_admin"
$LOG_DIR = Join-Path $PSScriptRoot "logs"

# ==========================================================================
# Helper Functions
# ==========================================================================

function Get-TestPdfInfo {
    param([string]$PdfPath)

    if (-not (Test-Path $PdfPath)) {
        return $null
    }

    $fileInfo = Get-Item $PdfPath
    $sha256 = (Get-FileHash -Path $PdfPath -Algorithm SHA256).Hash
    $sanitizedFilename = $fileInfo.Name -replace '[^A-Za-z0-9._-]', '_'
    $docId = "$sanitizedFilename`__$sha256".Substring(0, [Math]::Min(120, "$sanitizedFilename`__$sha256".Length))

    return @{
        Path = $PdfPath
        Name = $fileInfo.Name
        Size = $fileInfo.Length
        SHA256 = $sha256
        DocId = $docId
    }
}

function Wait-ForCondition {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds = 300,
        [int]$CheckIntervalSeconds = 5,
        [string]$TimeoutMessage = "Timeout waiting for condition"
    )

    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        if (& $Condition) {
            return $true
        }
        Start-Sleep -Seconds $CheckIntervalSeconds
        $elapsed += $CheckIntervalSeconds
        Write-Host "." -NoNewline
    }
    Write-Host
    Write-Warning $TimeoutMessage
    return $false
}

function Start-LogCapture {
    param([string]$LogPath)

    if ($SaveLogs) {
        if (-not (Test-Path (Split-Path $LogPath))) {
            New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null
        }
        Start-Transcript -Path $LogPath -Append
    }
}

function Stop-LogCapture {
    if ($SaveLogs) {
        Stop-Transcript
    }
}

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Running Ingestion Tests"
Write-Host ""

# Step 1: Configuration Display
Write-Host "  Configuration:" -ForegroundColor Yellow
Write-Host "  - Test PDF: $TestPDF"
Write-Host "  - System: $System"
Write-Host "  - Tier: $Tier"
Write-Host "  - Timeout: $Timeout seconds"
Write-Host "  - Skip Cleanup: $SkipCleanup"
Write-Host "  - Save Logs: $SaveLogs"
Write-Host ""

# Start log capture if requested
$logPath = Join-Path $LOG_DIR "test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-LogCapture -LogPath $logPath

# Step 2: Pre-flight Checks
Write-Step "Pre-flight checks"

# Check if Docker is running
if (-not (Test-DockerRunning)) {
    Write-Error "Docker Desktop is not running"
    Stop-LogCapture
    exit 2
}
Write-Success "Docker Desktop running"

# Check container health
$unhealthyContainers = @()
$requiredContainers = @("nexus_db", "nexus_api", "nexus_ingestion_worker", "nexus_validator")

foreach ($container in $requiredContainers) {
    $status = Get-ContainerStatus -ContainerName $container

    if ($status.Status -ne "running") {
        $unhealthyContainers += $container
    } elseif ($status.Health -notin @("healthy", "none")) {
        $unhealthyContainers += $container
    }
}

if ($unhealthyContainers.Count -gt 0) {
    Write-Error "Some containers not healthy: $($unhealthyContainers -join ', ')"
    Write-Host "  Run .\Status-NexusEnv.ps1 for details"
    Stop-LogCapture
    exit 2
}
Write-Success "All containers healthy"

# Check if API is healthy
Write-Host "  Checking API health..."
try {
    $health = Invoke-RestMethod -Uri "$API_BASE_URL/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Success "API is healthy: $($health.status)"
} catch {
    Write-Error "API health check failed: $_"
    Write-Host "  Check API logs: docker logs nexus_api"
    Stop-LogCapture
    exit 2
}

# Check if Transfer Station exists
if (-not (Test-TransferStationAccessible -TransferStationPath $TRANSFER_STATION)) {
    Write-Error "Transfer Station not accessible at: $TRANSFER_STATION"
    Stop-LogCapture
    exit 2
}
Write-Success "Transfer Station accessible"

# Step 3: Verify Test PDF
Write-Step "Verifying test PDF"

# Check if test PDF path is absolute or relative
if (-not [System.IO.Path]::IsPathRooted($TestPDF)) {
    # Try relative to test_data directory
    $testPdfPath = Join-Path $PSScriptRoot "test_data" $TestPDF

    if (-not (Test-Path $testPdfPath)) {
        # Try relative to current directory
        $testPdfPath = Join-Path (Get-Location) $TestPDF
    }
} else {
    $testPdfPath = $TestPDF
}

if (-not (Test-Path $testPdfPath)) {
    Write-Error "Test PDF not found at: $testPdfPath"
    Write-Host "  Please ensure the PDF exists in one of these locations:"
    Write-Host "    - scripts/tests/test_data/$TestPDF"
    Write-Host "    - $TestPDF (absolute path)"
    Stop-LogCapture
    exit 2
}

$pdfInfo = Get-TestPdfInfo -PdfPath $testPdfPath

$sizeFormatted = if ($pdfInfo.Size -ge 1MB) {
    "{0:N2} MB" -f ($pdfInfo.Size / 1MB)
} elseif ($pdfInfo.Size -ge 1KB) {
    "{0:N2} KB" -f ($pdfInfo.Size / 1KB)
} else {
    "$($pdfInfo.Size) bytes"
}

Write-Success "Test PDF found ($sizeFormatted)"
Write-Host "  - Name: $($pdfInfo.Name)"
Write-Host "  - SHA-256: $($pdfInfo.SHA256)"
Write-Host "  - Expected doc_id: $($pdfInfo.DocId)"
Write-Host ""

# Use provided DocId or calculated one
$expectedDocId = if ($DocId) { $DocId } else { $pdfInfo.DocId }

# Step 4: Execute E2E Test
Write-Step "Executing E2E ingestion test"
Write-Host ""

$testStartTime = Get-Date

# Place test PDF in sources directory
$sourcesDir = Join-Path $TRANSFER_STATION "sources"
if (-not (Test-Path $sourcesDir)) {
    New-Item -ItemType Directory -Path $sourcesDir -Force | Out-Null
}

$testPdfDest = Join-Path $sourcesDir $pdfInfo.Name
Copy-Item -Path $testPdfPath -Destination $testPdfDest -Force
Write-Success "Test PDF placed in Transfer Station"

# Wait for discovery
Write-Host "  Waiting for discovery..."
$discoverySuccess = Wait-ForCondition -TimeoutSeconds 120 -CheckIntervalSeconds 5 -Condition {
    try {
        $response = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get -ErrorAction SilentlyContinue
        return $response -ne $null
    } catch {
        return $false
    }
} -TimeoutMessage "Discovery timeout - source not detected within 120 seconds"

if (-not $discoverySuccess) {
    Write-Error "Discovery failed - check discovery scanner logs"
    Stop-LogCapture
    exit 1
}
Write-Success "Source discovered"

# Approve source via API
Write-Host "  Approving source..."
try {
    $source = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get -ErrorAction Stop

    $approvalBody = @{
        admin_user_id = $ADMIN_USER_ID
        expected_version = $source.state_version
        system_id = $System
        tier = $Tier
        notes = "Automated test approval via Run-IngestionTests.ps1"
    } | ConvertTo-Json

    $approvalResponse = Invoke-RestMethod `
        -Uri "$API_BASE_URL/governance/$expectedDocId/approve" `
        -Method Post `
        -Body $approvalBody `
        -ContentType "application/json" `
        -ErrorAction Stop

    Write-Success "Source approved: $($approvalResponse.status)"
} catch {
    Write-Error "Approval failed: $_"
    Stop-LogCapture
    exit 1
}

# Wait for ingestion pipeline completion
Write-Host "  Waiting for ingestion pipeline..."
$ingestionSuccess = Wait-ForCondition -TimeoutSeconds $Timeout -CheckIntervalSeconds 10 -Condition {
    try {
        $source = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get -ErrorAction SilentlyContinue
        return $source.status -in @("INGESTED", "ERROR", "DEACTIVATED")
    } catch {
        return $false
    }
} -TimeoutMessage "Ingestion timeout - pipeline did not complete within $Timeout seconds"

if (-not $ingestionSuccess) {
    Write-Error "Ingestion timeout - check worker logs"
    Write-Host "  docker logs nexus_ingestion_worker"
    Stop-LogCapture
    exit 1
}

# Verify ingestion success
$finalSource = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get

if ($finalSource.status -ne "INGESTED") {
    Write-Error "Ingestion failed - final status: $($finalSource.status)"
    Write-Host "  Check logs for errors"
    Stop-LogCapture
    exit 1
}
Write-Success "Ingestion completed: INGESTED"

# Verify validation report
$validationReportPath = Join-Path $TRANSFER_STATION "artifacts\reports\$expectedDocId\validation_report.json"
if (-not (Test-Path $validationReportPath)) {
    Write-Error "Validation report not found"
    Stop-LogCapture
    exit 1
}

$validationReport = Get-Content $validationReportPath -Raw | ConvertFrom-Json

if ($validationReport.status -ne "PASS") {
    Write-Error "Validation failed: $($validationReport.status)"
    Write-Host "  Failed checks:"
    $validationReport.checks | Where-Object { -not $_.passed } | ForEach-Object {
        Write-Host "    - $($_.check_name): $($_.message)" -ForegroundColor Red
    }
    Stop-LogCapture
    exit 1
}
Write-Success "Validation passed: $($validationReport.checks.Count) checks"

# Query database for chunk count
try {
    $dbCheckResult = docker exec nexus_db psql -U nexus -d nexus_core -t -c "SELECT COUNT(*) FROM chunks WHERE doc_id = '$expectedDocId' AND active = true;" 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to query database chunk count"
        $chunkCount = "unknown"
    } else {
        $chunkCount = [int]($dbCheckResult.Trim())
    }
} catch {
    Write-Warning "Failed to query database: $_"
    $chunkCount = "unknown"
}

$testEndTime = Get-Date
$testDuration = ($testEndTime - $testStartTime).TotalSeconds

Write-Host ""

# Step 5: Test Summary
Write-Step "Test Summary"
Write-Host ""

Write-Host "  Status: " -NoNewline
Write-Host "PASSED ✓" -ForegroundColor Green

Write-Host "  Duration: $([int]$testDuration) seconds"
Write-Host "  doc_id: $expectedDocId"
Write-Host "  Chunks: $chunkCount"
Write-Host "  Validation: $($validationReport.status)"

if ($Verbose) {
    Write-Host ""
    Write-Host "  Validation Checks:" -ForegroundColor Cyan
    foreach ($check in $validationReport.checks) {
        $checkIndicator = if ($check.passed) { "✓" } else { "✗" }
        $checkColor = if ($check.passed) { "Green" } else { "Red" }
        Write-Host "    $checkIndicator $($check.check_name): $($check.message)" -ForegroundColor $checkColor
    }
}

Write-Host ""

if ($SaveLogs) {
    Write-Success "Logs saved to: $logPath"
    Write-Host ""
}

# Step 6: Cleanup (optional)
if (-not $SkipCleanup) {
    Write-Step "Cleaning up test data"

    # Check if cleanup script exists
    $cleanupScript = Join-Path $PSScriptRoot "cleanup_test_data.ps1"

    if (Test-Path $cleanupScript) {
        Write-Host "  Running cleanup script..."
        & $cleanupScript -DocId $expectedDocId -Force

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Cleanup script failed (exit code: $LASTEXITCODE)"
        } else {
            Write-Success "Test data cleaned up"
        }
    } else {
        Write-Warning "Cleanup script not found at: $cleanupScript"
        Write-Host "  Manual cleanup required:"
        Write-Host "  .\cleanup_test_data.ps1 -DocId '$expectedDocId'"
    }
} else {
    Write-Host ""
    Write-Host "  Cleanup skipped. To cleanup manually, run:" -ForegroundColor Yellow
    Write-Host "  .\cleanup_test_data.ps1 -DocId '$expectedDocId'"
}

Write-Host ""
Write-Step "Test execution complete ✓"
Write-Host ""

Stop-LogCapture

exit 0
