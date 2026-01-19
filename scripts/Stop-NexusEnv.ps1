# Stop Nexus Core Environment
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Environment Control
# Test ID: PS-TEST-001
#
# Purpose: Gracefully stop all running Docker containers
#
# Usage:
#   .\Stop-NexusEnv.ps1                 # Graceful shutdown
#   .\Stop-NexusEnv.ps1 -Force          # Force stop (skip graceful shutdown)
#   .\Stop-NexusEnv.ps1 -PreserveData   # Keep Docker volumes
#
# Requirements from spec:
# - Gracefully shutdown in reverse dependency order
# - Wait for containers to stop (timeout 30s)
# - Force stop if timeout exceeded
# - Display shutdown status
# - Exit with appropriate codes

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$PreserveData
)

# Import common helper functions
. $PSScriptRoot/Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$SHUTDOWN_TIMEOUT = 30  # seconds
$REQUIRED_CONTAINERS = @(
    "nexus_validator",
    "nexus_ingestion_worker",
    "nexus_api",
    "nexus_db"
)

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Stopping Nexus Core environment..."

# Step 1: Verify Docker Desktop is running
if (-not (Test-DockerRunning)) {
    Write-Warning "Docker Desktop is not running"
    Write-Host "  No containers to stop"
    exit 0
}

# Step 2: Check if any containers are running
$runningContainers = docker ps --format "{{.Names}}" 2>$null

if ($null -eq $runningContainers -or $runningContainers.Count -eq 0) {
    Write-Warning "No containers are currently running"
    exit 0
}

$nexusContainersRunning = @()
foreach ($container in $REQUIRED_CONTAINERS) {
    if ($runningContainers -contains $container) {
        $nexusContainersRunning += $container
    }
}

if ($nexusContainersRunning.Count -eq 0) {
    Write-Warning "No Nexus Core containers are currently running"
    exit 0
}

Write-Host "  Stopping containers:"
foreach ($container in $nexusContainersRunning) {
    Write-Host "    - $container"
}

# Step 3: Get docker-compose.yml path
$dockerComposePath = Get-DockerComposePath

if (-not (Test-Path $dockerComposePath)) {
    Write-Error "docker-compose.yml not found at: $dockerComposePath"
    exit 1
}

# Step 4: Stop containers using docker-compose
$composeDir = Split-Path -Parent $dockerComposePath
Push-Location $composeDir

try {
    Write-Host ""

    if ($Force) {
        Write-Host "  Force stopping containers..."
        $output = docker-compose down -t 0 2>&1
    } elseif ($PreserveData) {
        Write-Host "  Gracefully stopping containers (preserving volumes)..."
        $output = docker-compose stop -t $SHUTDOWN_TIMEOUT 2>&1
    } else {
        Write-Host "  Gracefully stopping containers..."
        $output = docker-compose down -t $SHUTDOWN_TIMEOUT 2>&1
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to stop containers"
        Write-Host "  Error output:"
        Write-Host $output
        exit 1
    }

} finally {
    Pop-Location
}

Write-Success "All services stopped"

# Step 5: Verify containers stopped
Start-Sleep -Seconds 2

$stillRunning = @()
foreach ($container in $REQUIRED_CONTAINERS) {
    $status = Get-ContainerStatus -ContainerName $container

    if ($status.Status -eq "running") {
        $stillRunning += $container
    }
}

if ($stillRunning.Count -gt 0) {
    Write-Warning "Some containers still running:"
    foreach ($container in $stillRunning) {
        Write-Host "    - $container"
    }
    Write-Host "  You may need to force stop these containers manually:"
    Write-Host "  docker stop $($stillRunning -join ' ')"
    exit 1
}

Write-Host ""
Write-Step "Environment shutdown complete"
Write-Host ""

exit 0
