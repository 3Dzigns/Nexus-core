# Reset Nexus Core Test Environment
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Cleanup & Reset
# Test ID: PS-TEST-002
#
# Purpose: Comprehensive cleanup and reset to clean state
#
# Usage:
#   .\Reset-NexusTestEnv.ps1                      # Interactive confirmation
#   .\Reset-NexusTestEnv.ps1 -Force               # Skip confirmation
#   .\Reset-NexusTestEnv.ps1 -KeepVolumes         # Don't delete Docker volumes
#   .\Reset-NexusTestEnv.ps1 -DryRun              # Show what would be deleted
#
# Requirements from spec:
# - Clean ALL test sources and artifacts
# - Reset database to clean state
# - Verify environment restoration
# - Require confirmation where destructive

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$KeepVolumes,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Import common helper functions
. $PSScriptRoot\..\Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$TRANSFER_STATION = "E:\Transfer_Station"

# ==========================================================================
# Helper Functions
# ==========================================================================

function Get-DatabaseCounts {
    <#
    .SYNOPSIS
    Gets row counts for all main tables
    #>
    try {
        $query = @"
SELECT
    (SELECT COUNT(*) FROM sources) as sources,
    (SELECT COUNT(*) FROM chunks) as chunks,
    (SELECT COUNT(*) FROM embeddings) as embeddings,
    (SELECT COUNT(*) FROM fts_index) as fts_index,
    (SELECT COUNT(*) FROM governance_events) as governance_events,
    (SELECT COUNT(*) FROM manifests) as manifests,
    (SELECT COUNT(*) FROM validation_reports) as validation_reports,
    (SELECT COUNT(*) FROM source_links) as source_links;
"@

        $result = docker exec nexus_db psql -U nexus -d nexus_core -t -c "$query" 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to query database counts"
            return $null
        }

        # Parse result (format: sources | chunks | embeddings | ...)
        $values = $result.Trim() -split '\|' | ForEach-Object { $_.Trim() }

        return @{
            Sources = [int]$values[0]
            Chunks = [int]$values[1]
            Embeddings = [int]$values[2]
            FTSIndex = [int]$values[3]
            GovernanceEvents = [int]$values[4]
            Manifests = [int]$values[5]
            ValidationReports = [int]$values[6]
            SourceLinks = [int]$values[7]
        }
    } catch {
        Write-Warning "Error querying database: $_"
        return $null
    }
}

function Get-ArtifactsSize {
    <#
    .SYNOPSIS
    Gets total size of artifacts directory
    #>
    try {
        $artifactsPath = Join-Path $TRANSFER_STATION "artifacts"

        if (-not (Test-Path $artifactsPath)) {
            return @{
                SizeBytes = 0
                SizeFormatted = "0 bytes"
                FileCount = 0
            }
        }

        $files = Get-ChildItem -Path $artifactsPath -Recurse -File

        $totalSize = ($files | Measure-Object -Property Length -Sum).Sum
        $fileCount = $files.Count

        $sizeFormatted = if ($totalSize -ge 1GB) {
            "{0:N2} GB" -f ($totalSize / 1GB)
        } elseif ($totalSize -ge 1MB) {
            "{0:N2} MB" -f ($totalSize / 1MB)
        } elseif ($totalSize -ge 1KB) {
            "{0:N2} KB" -f ($totalSize / 1KB)
        } else {
            "$totalSize bytes"
        }

        return @{
            SizeBytes = $totalSize
            SizeFormatted = $sizeFormatted
            FileCount = $fileCount
        }
    } catch {
        Write-Warning "Error calculating artifacts size: $_"
        return @{
            SizeBytes = 0
            SizeFormatted = "unknown"
            FileCount = 0
        }
    }
}

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Nexus Core Environment Reset"
Write-Host ""

# Step 1: Verify Docker is running
if (-not (Test-DockerRunning)) {
    Write-Error "Docker Desktop is not running"
    Write-Host "  Cannot proceed with reset"
    exit 1
}

# Step 2: Check if nexus_db container is running
$dbStatus = Get-ContainerStatus -ContainerName "nexus_db"

if ($dbStatus.Status -ne "running") {
    Write-Warning "nexus_db container is not running"
    Write-Host "  Starting environment to access database..."

    & "$PSScriptRoot\..\Start-NexusEnv.ps1"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start environment"
        exit 1
    }
}

# Step 3: Collect pre-reset statistics
Write-Step "Pre-reset status:"
Write-Host ""

$dbCounts = Get-DatabaseCounts
$artifactsInfo = Get-ArtifactsSize

Write-Host "  Database:"
if ($null -ne $dbCounts) {
    Write-Host "    - Sources: $($dbCounts.Sources) records"
    Write-Host "    - Chunks: $($dbCounts.Chunks) records"
    Write-Host "    - Embeddings: $($dbCounts.Embeddings) records"
    Write-Host "    - FTS Index: $($dbCounts.FTSIndex) records"
    Write-Host "    - Governance Events: $($dbCounts.GovernanceEvents) records"
    Write-Host "    - Manifests: $($dbCounts.Manifests) records"
    Write-Host "    - Validation Reports: $($dbCounts.ValidationReports) records"
    Write-Host "    - Source Links: $($dbCounts.SourceLinks) records"
} else {
    Write-Host "    - Unable to query database counts"
}

Write-Host "  Artifacts:"
Write-Host "    - Size: $($artifactsInfo.SizeFormatted)"
Write-Host "    - Files: $($artifactsInfo.FileCount)"

Write-Host ""

# Step 4: Dry run - show what would be deleted
if ($DryRun) {
    Write-Warning "DRY RUN MODE - Nothing will be deleted"
    Write-Host ""
    Write-Host "  Would delete:"
    Write-Host "    - All database records (sources, chunks, embeddings, etc.)"
    Write-Host "    - All Transfer Station sources: $TRANSFER_STATION\sources\*"
    Write-Host "    - All Transfer Station artifacts: $TRANSFER_STATION\artifacts\*"
    if (-not $KeepVolumes) {
        Write-Host "    - All Docker volumes"
    }
    Write-Host ""
    exit 0
}

# Step 5: Confirmation prompt (unless -Force)
$confirmMessage = @"
WARNING: This will DELETE all test data!

Database Records:
  - Sources: $($dbCounts.Sources)
  - Chunks: $($dbCounts.Chunks)
  - Embeddings: $($dbCounts.Embeddings)
  - Other records: $(($dbCounts.FTSIndex + $dbCounts.GovernanceEvents + $dbCounts.Manifests + $dbCounts.ValidationReports + $dbCounts.SourceLinks))

Filesystem:
  - Artifacts: $($artifactsInfo.SizeFormatted) ($($artifactsInfo.FileCount) files)
"@

if (-not (Confirm-DestructiveAction -Message $confirmMessage -Force:$Force)) {
    Write-Host "Reset cancelled"
    exit 0
}

# Step 6: Stop all containers
Write-Step "Stopping containers..."

& "$PSScriptRoot\..\Stop-NexusEnv.ps1" -Force

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Error stopping containers (continuing anyway)"
} else {
    Write-Success "All containers stopped"
}

Write-Host ""

# Step 7: Clean database
Write-Step "Cleaning database..."

# Restart only the database container for cleanup
docker start nexus_db 2>&1 | Out-Null
Start-Sleep -Seconds 3

# Delete all records in dependency order (per CLEANUP_STRATEGY_v1.0.md)
$deletionQueries = @(
    "TRUNCATE TABLE fts_index CASCADE;",
    "TRUNCATE TABLE embeddings CASCADE;",
    "TRUNCATE TABLE chunks CASCADE;",
    "TRUNCATE TABLE manifests CASCADE;",
    "TRUNCATE TABLE validation_reports CASCADE;",
    "TRUNCATE TABLE governance_events CASCADE;",
    "TRUNCATE TABLE source_links CASCADE;",
    "TRUNCATE TABLE sources CASCADE;"
)

foreach ($query in $deletionQueries) {
    $result = docker exec nexus_db psql -U nexus -d nexus_core -t -c "$query" 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Query failed: $query"
        Write-Host "  Error: $result"
    }
}

# Verify deletion
$postDeleteCounts = Get-DatabaseCounts

if ($null -ne $postDeleteCounts) {
    $totalRemaining = $postDeleteCounts.Sources + $postDeleteCounts.Chunks + $postDeleteCounts.Embeddings + $postDeleteCounts.FTSIndex

    if ($totalRemaining -eq 0) {
        Write-Success "All database records deleted"
    } else {
        Write-Warning "Some records remain in database (total: $totalRemaining)"
    }
} else {
    Write-Warning "Unable to verify database cleanup"
}

# Stop database
docker stop nexus_db 2>&1 | Out-Null

Write-Host ""

# Step 8: Clean Transfer Station artifacts
Write-Step "Cleaning artifacts..."

$sourcesPath = Join-Path $TRANSFER_STATION "sources"
$artifactsPath = Join-Path $TRANSFER_STATION "artifacts"

# Delete sources
if (Test-Path $sourcesPath) {
    $sourceFiles = Get-ChildItem -Path $sourcesPath -File

    if ($sourceFiles.Count -gt 0) {
        Remove-Item -Path (Join-Path $sourcesPath "*") -Force -Recurse
        Write-Success "Deleted $TRANSFER_STATION\sources\ ($($sourceFiles.Count) files)"
    } else {
        Write-Host "  No source files to delete"
    }
}

# Delete artifacts
if (Test-Path $artifactsPath) {
    $artifactDirs = Get-ChildItem -Path $artifactsPath -Directory

    if ($artifactDirs.Count -gt 0) {
        Remove-Item -Path (Join-Path $artifactsPath "*") -Force -Recurse
        Write-Success "Deleted $TRANSFER_STATION\artifacts\ ($($artifactsInfo.FileCount) files, $($artifactsInfo.SizeFormatted))"
    } else {
        Write-Host "  No artifacts to delete"
    }
}

Write-Host ""

# Step 9: Delete Docker volumes (optional)
if (-not $KeepVolumes) {
    Write-Step "Deleting Docker volumes..."

    $composeDir = Split-Path -Parent (Get-DockerComposePath)
    Push-Location $composeDir
    try {
        docker-compose down -v 2>&1 | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to delete Docker volumes"
        } else {
            Write-Success "Docker volumes deleted"
        }
    } finally {
        Pop-Location
    }

    Write-Host ""
}

# Step 10: Restart containers
Write-Step "Restarting containers..."

& "$PSScriptRoot\..\Start-NexusEnv.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to restart environment"
    exit 1
}

Write-Success "All services started and healthy"

Write-Host ""

# Step 11: Post-reset verification
Write-Step "Verification:"

# Verify database empty
$verifyDbCounts = Get-DatabaseCounts

if ($null -ne $verifyDbCounts) {
    $totalRecords = $verifyDbCounts.Sources + $verifyDbCounts.Chunks + $verifyDbCounts.Embeddings + $verifyDbCounts.FTSIndex

    if ($totalRecords -eq 0) {
        Write-Success "Database tables empty"
    } else {
        Write-Error "Database tables not empty (total: $totalRecords records)"
    }
} else {
    Write-Warning "Unable to verify database cleanup"
}

# Verify artifacts clean
$artifactsPathCheck = Join-Path $TRANSFER_STATION "artifacts"
$sourcesPathCheck = Join-Path $TRANSFER_STATION "sources"

$artifactFilesRemaining = if (Test-Path $artifactsPathCheck) {
    (Get-ChildItem -Path $artifactsPathCheck -Recurse -File).Count
} else {
    0
}

$sourceFilesRemaining = if (Test-Path $sourcesPathCheck) {
    (Get-ChildItem -Path $sourcesPathCheck -File).Count
} else {
    0
}

if ($artifactFilesRemaining -eq 0 -and $sourceFilesRemaining -eq 0) {
    Write-Success "Artifact directories clean"
} else {
    Write-Warning "Some files remain (artifacts: $artifactFilesRemaining, sources: $sourceFilesRemaining)"
}

# Verify containers healthy
$unhealthyContainers = @()
$requiredContainers = @("nexus_db", "nexus_api", "nexus_ingestion_worker", "nexus_validator")

foreach ($container in $requiredContainers) {
    $status = Get-ContainerStatus -ContainerName $container

    if ($status.Status -ne "running" -or
        ($status.Health -ne "healthy" -and $status.Health -ne "none")) {
        $unhealthyContainers += $container
    }
}

if ($unhealthyContainers.Count -eq 0) {
    Write-Success "All containers healthy"
} else {
    Write-Warning "Some containers unhealthy: $($unhealthyContainers -join ', ')"
}

Write-Host ""
Write-Step "Environment reset complete ✓"
Write-Host ""

exit 0
