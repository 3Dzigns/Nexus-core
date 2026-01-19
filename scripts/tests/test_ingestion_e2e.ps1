# End-to-End Ingestion Pipeline Test
# Reference: TEST_PLAN_v1.0.md, INGESTION_ARCHITECTURE_v1.0.md
# Task ID: ING-IMPL-INFRA-003
#
# Purpose: Validate complete ingestion pipeline from source placement to validation
#
# Workflow:
# 1. Place test PDF in Transfer Station sources directory
# 2. Wait for discovery (source record created with PENDING_APPROVAL)
# 3. Invoke admin approval via API
# 4. Wait for ingestion pipeline completion
# 5. Verify validation passed and source status = INGESTED
# 6. Run cleanup script to restore environment
#
# Requirements: FR-001 through FR-026
# Test Cases: T-ING-001 through T-ING-013

# ==========================================================================
# Configuration
# ==========================================================================

$API_BASE_URL = "http://localhost:8000"
$TRANSFER_STATION = "E:\Transfer_Station"
$TEST_PDF = "test_pathfinder_rulebook.pdf"
$ADMIN_USER_ID = "test_admin"

# ==========================================================================
# Helper Functions
# ==========================================================================

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
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
    Write-Error $TimeoutMessage
    return $false
}

# ==========================================================================
# Step 1: Verify Prerequisites
# ==========================================================================

Write-Step "Step 1: Verifying prerequisites"

# Check if Docker containers are running
Write-Host "  Checking Docker containers..."
$containers = docker ps --format "{{.Names}}" 2>$null
if (-not $containers) {
    Write-Error "Docker containers not running. Please run 'docker-compose up -d' first."
    exit 1
}

$required_containers = @("nexus_db", "nexus_api", "nexus_ingestion_worker", "nexus_validator")
foreach ($container in $required_containers) {
    if ($containers -notcontains $container) {
        Write-Error "Required container '$container' not running"
        exit 1
    }
}
Write-Success "All required containers running"

# Check if API is healthy
Write-Host "  Checking API health..."
try {
    $health = Invoke-RestMethod -Uri "$API_BASE_URL/health" -Method Get -TimeoutSec 5
    Write-Success "API is healthy: $($health.status)"
} catch {
    Write-Error "API health check failed: $_"
    exit 1
}

# Check if Transfer Station exists
if (-not (Test-Path $TRANSFER_STATION)) {
    Write-Error "Transfer Station not found at: $TRANSFER_STATION"
    exit 1
}
Write-Success "Transfer Station found"

# ==========================================================================
# Step 2: Place Test PDF in Sources Directory
# ==========================================================================

Write-Step "Step 2: Placing test PDF in Transfer Station"

$sourcesDir = Join-Path $TRANSFER_STATION "sources"
if (-not (Test-Path $sourcesDir)) {
    New-Item -ItemType Directory -Path $sourcesDir -Force | Out-Null
}

# Check if test PDF exists in project
$testPdfSource = Join-Path $PSScriptRoot "test_data" $TEST_PDF
if (-not (Test-Path $testPdfSource)) {
    Write-Error "Test PDF not found at: $testPdfSource"
    Write-Host "  Please place a test PDF in scripts/tests/test_data/ directory"
    exit 1
}

# Copy test PDF to sources directory
$testPdfDest = Join-Path $sourcesDir $TEST_PDF
Copy-Item -Path $testPdfSource -Destination $testPdfDest -Force
Write-Success "Test PDF placed: $testPdfDest"

# Calculate SHA-256 for verification
$sha256 = (Get-FileHash -Path $testPdfDest -Algorithm SHA256).Hash
Write-Host "  SHA-256: $sha256"

# Generate expected doc_id
$sanitizedFilename = $TEST_PDF -replace '[^A-Za-z0-9._-]', '_'
$expectedDocId = "$sanitizedFilename`__$sha256".Substring(0, [Math]::Min(120, "$sanitizedFilename`__$sha256".Length))
Write-Host "  Expected doc_id: $expectedDocId"

# ==========================================================================
# Step 3: Wait for Discovery
# ==========================================================================

Write-Step "Step 3: Waiting for discovery scanner to detect source"

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
    exit 1
}

# Verify source status is PENDING_APPROVAL
$source = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get
if ($source.status -ne "PENDING_APPROVAL") {
    Write-Error "Source status incorrect: expected PENDING_APPROVAL, got $($source.status)"
    exit 1
}
Write-Success "Source discovered with status: $($source.status)"

# ==========================================================================
# Step 4: Approve Source via API
# ==========================================================================

Write-Step "Step 4: Approving source via admin API"

$approvalBody = @{
    admin_user_id = $ADMIN_USER_ID
    expected_version = $source.state_version
    system_id = "pathfinder_1e"
    tier = "PREMIUM"
    notes = "E2E test approval"
} | ConvertTo-Json

try {
    $approvalResponse = Invoke-RestMethod `
        -Uri "$API_BASE_URL/governance/$expectedDocId/approve" `
        -Method Post `
        -Body $approvalBody `
        -ContentType "application/json"
    Write-Success "Source approved: $($approvalResponse.status)"
} catch {
    Write-Error "Approval failed: $_"
    exit 1
}

# ==========================================================================
# Step 5: Wait for Ingestion Pipeline Completion
# ==========================================================================

Write-Step "Step 5: Waiting for ingestion pipeline to complete"

$ingestionSuccess = Wait-ForCondition -TimeoutSeconds 600 -CheckIntervalSeconds 10 -Condition {
    try {
        $source = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get -ErrorAction SilentlyContinue
        return $source.status -in @("INGESTED", "ERROR", "DEACTIVATED")
    } catch {
        return $false
    }
} -TimeoutMessage "Ingestion timeout - pipeline did not complete within 600 seconds"

if (-not $ingestionSuccess) {
    Write-Error "Ingestion timeout - check worker logs"
    exit 1
}

# ==========================================================================
# Step 6: Verify Ingestion Success
# ==========================================================================

Write-Step "Step 6: Verifying ingestion success"

$finalSource = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$expectedDocId" -Method Get

if ($finalSource.status -ne "INGESTED") {
    Write-Error "Ingestion failed - final status: $($finalSource.status)"
    Write-Host "  Check logs for errors"
    exit 1
}
Write-Success "Source status: INGESTED"

# Check for validation report
$validationReportPath = Join-Path $TRANSFER_STATION "artifacts\reports\$expectedDocId\validation_report.json"
if (-not (Test-Path $validationReportPath)) {
    Write-Error "Validation report not found at: $validationReportPath"
    exit 1
}
Write-Success "Validation report found"

# Parse validation report
$validationReport = Get-Content $validationReportPath | ConvertFrom-Json
if ($validationReport.status -ne "PASS") {
    Write-Error "Validation failed: $($validationReport.status)"
    Write-Host "  Failed checks:"
    $validationReport.checks | Where-Object { -not $_.passed } | ForEach-Object {
        Write-Host "    - $($_.check_name): $($_.message)"
    }
    exit 1
}
Write-Success "Validation passed: $($validationReport.checks.Count) checks"

# ==========================================================================
# Step 7: Verify Artifacts
# ==========================================================================

Write-Step "Step 7: Verifying artifacts created"

$artifactsRoot = Join-Path $TRANSFER_STATION "artifacts"

# Check for dual manifests
$doclingManifest = Join-Path $artifactsRoot "manifests\$expectedDocId\raw\docling_manifest.json"
$unstructuredManifest = Join-Path $artifactsRoot "manifests\$expectedDocId\raw\unstructured_manifest.json"

if (-not (Test-Path $doclingManifest)) {
    Write-Error "Docling manifest not found"
    exit 1
}
if (-not (Test-Path $unstructuredManifest)) {
    Write-Error "Unstructured manifest not found"
    exit 1
}
Write-Success "Dual raw manifests found"

# Check for dual chunk sets
$doclingChunks = Join-Path $artifactsRoot "chunks\$expectedDocId\docling_chunks.jsonl"
$unstructuredChunks = Join-Path $artifactsRoot "chunks\$expectedDocId\unstructured_chunks.jsonl"

if (-not (Test-Path $doclingChunks)) {
    Write-Error "Docling chunks not found"
    exit 1
}
if (-not (Test-Path $unstructuredChunks)) {
    Write-Error "Unstructured chunks not found"
    exit 1
}
Write-Success "Dual chunk sets found"

# Count chunks in database
try {
    $dbCheckResult = docker exec nexus_db psql -U nexus -d nexus_core -t -c "SELECT COUNT(*) FROM chunks WHERE doc_id = '$expectedDocId' AND active = true;"
    $chunkCount = [int]($dbCheckResult.Trim())
    Write-Success "Database chunks: $chunkCount"
} catch {
    Write-Error "Failed to query database: $_"
    exit 1
}

# ==========================================================================
# Step 8: Summary
# ==========================================================================

Write-Step "Test Completed Successfully!"
Write-Host ""
Write-Host "  Summary:" -ForegroundColor Yellow
Write-Host "  - doc_id: $expectedDocId"
Write-Host "  - Status: INGESTED"
Write-Host "  - Validation: PASS"
Write-Host "  - Chunks: $chunkCount"
Write-Host ""
Write-Host "  To cleanup test data, run:" -ForegroundColor Yellow
Write-Host "  .\scripts\tests\cleanup_test_data.ps1 -DocId '$expectedDocId'"
Write-Host ""

exit 0
