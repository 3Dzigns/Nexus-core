# Cleanup Test Data Script
# Reference: CLEANUP_STRATEGY_v1.0.md, TEST_PLAN_v1.0.md
# Task ID: ING-IMPL-INFRA-003
#
# Purpose: Clean up test data after integration testing
#
# Per CLEANUP_STRATEGY_v1.0.md:
# - Remove source file from Transfer Station
# - Delete all database records for doc_id (sources, chunks, embeddings, governance_events, etc.)
# - Delete all artifacts from Transfer Station (manifests, chunks, reports)
# - Restore environment to clean state for next test run
#
# IMPORTANT: This is a destructive operation. Only use for test data!

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,

    [Parameter(Mandatory=$false)]
    [string]$TransferStation = "E:\Transfer_Station",

    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# ==========================================================================
# Configuration
# ==========================================================================

$API_BASE_URL = "http://localhost:8000"

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

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠ $Message" -ForegroundColor Yellow
}

# ==========================================================================
# Step 1: Verify Prerequisites
# ==========================================================================

Write-Step "Step 1: Verifying prerequisites"

# Check if Docker containers are running
Write-Host "  Checking Docker containers..."
$containers = docker ps --format "{{.Names}}" 2>$null
if (-not $containers) {
    Write-Error "Docker containers not running"
    exit 1
}
Write-Success "Docker containers running"

# Check if source exists
Write-Host "  Checking if doc_id exists..."
try {
    $source = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$DocId" -Method Get -ErrorAction Stop
    Write-Success "Source found: $($source.original_filename)"
} catch {
    Write-Warning "Source not found in database (may have been manually deleted)"
    $source = $null
}

# ==========================================================================
# Step 2: Confirm Deletion (unless -Force specified)
# ==========================================================================

if (-not $Force) {
    Write-Host ""
    Write-Warning "This will DELETE all data for doc_id: $DocId"
    if ($source) {
        Write-Host "  - Original filename: $($source.original_filename)"
        Write-Host "  - Status: $($source.status)"
        Write-Host "  - System: $($source.system_id)"
    }
    Write-Host ""
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
    if ($confirmation -ne "yes") {
        Write-Host "Cleanup cancelled"
        exit 0
    }
}

# ==========================================================================
# Step 3: Remove Source File from Transfer Station
# ==========================================================================

Write-Step "Step 3: Removing source file from Transfer Station"

if ($source) {
    $sourceFile = Join-Path $TransferStation "sources\$($source.original_filename)"
    if (Test-Path $sourceFile) {
        Remove-Item -Path $sourceFile -Force
        Write-Success "Source file removed: $sourceFile"
    } else {
        Write-Warning "Source file not found (may have been manually removed)"
    }
}

# ==========================================================================
# Step 4: Delete Database Records
# ==========================================================================

Write-Step "Step 4: Deleting database records for doc_id: $DocId"

# Per CLEANUP_STRATEGY_v1.0.md, delete in dependency order:
# 1. fts_index (references chunks)
# 2. embeddings (references chunks)
# 3. chunks (references sources)
# 4. manifests (references sources)
# 5. validation_reports (references sources)
# 6. governance_events (references sources)
# 7. source_links (references sources)
# 8. sources (primary record)

$deletionQueries = @(
    "DELETE FROM fts_index WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = '$DocId');",
    "DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = '$DocId');",
    "DELETE FROM chunks WHERE doc_id = '$DocId';",
    "DELETE FROM manifests WHERE doc_id = '$DocId';",
    "DELETE FROM validation_reports WHERE doc_id = '$DocId';",
    "DELETE FROM governance_events WHERE doc_id = '$DocId';",
    "DELETE FROM source_links WHERE doc_id = '$DocId';",
    "DELETE FROM sources WHERE doc_id = '$DocId';"
)

try {
    foreach ($query in $deletionQueries) {
        $result = docker exec nexus_db psql -U nexus -d nexus_core -t -c "$query" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Query failed: $query"
            Write-Host "  Error: $result"
        }
    }
    Write-Success "All database records deleted"
} catch {
    Write-Error "Database deletion failed: $_"
    exit 1
}

# ==========================================================================
# Step 5: Delete Artifacts from Transfer Station
# ==========================================================================

Write-Step "Step 5: Deleting artifacts from Transfer Station"

$artifactsRoot = Join-Path $TransferStation "artifacts"

# Delete manifests
$manifestsDir = Join-Path $artifactsRoot "manifests\$DocId"
if (Test-Path $manifestsDir) {
    Remove-Item -Path $manifestsDir -Recurse -Force
    Write-Success "Manifests deleted: $manifestsDir"
}

# Delete chunks
$chunksDir = Join-Path $artifactsRoot "chunks\$DocId"
if (Test-Path $chunksDir) {
    Remove-Item -Path $chunksDir -Recurse -Force
    Write-Success "Chunks deleted: $chunksDir"
}

# Delete assets
$assetsDir = Join-Path $artifactsRoot "assets\$DocId"
if (Test-Path $assetsDir) {
    Remove-Item -Path $assetsDir -Recurse -Force
    Write-Success "Assets deleted: $assetsDir"
}

# Delete validation reports
$reportsDir = Join-Path $artifactsRoot "reports\$DocId"
if (Test-Path $reportsDir) {
    Remove-Item -Path $reportsDir -Recurse -Force
    Write-Success "Reports deleted: $reportsDir"
}

# ==========================================================================
# Step 6: Verify Cleanup
# ==========================================================================

Write-Step "Step 6: Verifying cleanup completion"

# Check if source still exists in database
try {
    $verifySource = Invoke-RestMethod -Uri "$API_BASE_URL/sources/$DocId" -Method Get -ErrorAction Stop
    Write-Error "Source still exists in database after cleanup!"
    exit 1
} catch {
    Write-Success "Source deleted from database"
}

# Check if chunks still exist
$chunkCheck = docker exec nexus_db psql -U nexus -d nexus_core -t -c "SELECT COUNT(*) FROM chunks WHERE doc_id = '$DocId';"
$chunkCount = [int]($chunkCheck.Trim())
if ($chunkCount -gt 0) {
    Write-Error "Chunks still exist in database: $chunkCount"
    exit 1
}
Write-Success "All chunks deleted"

# Check if embeddings still exist
$embeddingCheck = docker exec nexus_db psql -U nexus -d nexus_core -t -c "SELECT COUNT(*) FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = '$DocId');"
$embeddingCount = [int]($embeddingCheck.Trim())
if ($embeddingCount -gt 0) {
    Write-Error "Embeddings still exist in database: $embeddingCount"
    exit 1
}
Write-Success "All embeddings deleted"

# ==========================================================================
# Step 7: Summary
# ==========================================================================

Write-Step "Cleanup Completed Successfully!"
Write-Host ""
Write-Host "  Summary:" -ForegroundColor Yellow
Write-Host "  - doc_id: $DocId"
Write-Host "  - Source file: Removed"
Write-Host "  - Database records: Deleted"
Write-Host "  - Artifacts: Deleted"
Write-Host ""
Write-Host "  Environment restored to clean state" -ForegroundColor Green
Write-Host ""

exit 0
