# Start Nexus Core Environment
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Environment Control
# Test ID: PS-TEST-001
#
# Purpose: Start all required Docker containers with health verification
#
# Usage:
#   .\Start-NexusEnv.ps1           # Start and wait for health checks
#   .\Start-NexusEnv.ps1 -Wait     # Explicit wait flag
#
# Requirements from spec:
# - Load docker-compose configuration from project root
# - Start containers in correct dependency order
# - Wait for health checks to pass
# - Display container status and health
# - Exit with appropriate codes (0 = success, 1 = failure)

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Wait = $true
)

# Import common helper functions
. $PSScriptRoot/Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$TRANSFER_STATION = "E:\Transfer_Station"
$HEALTH_CHECK_TIMEOUT = 120  # seconds
$REQUIRED_CONTAINERS = @(
    "nexus_db",
    "nexus_api",
    "nexus_ingestion_worker",
    "nexus_validator"
)

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Starting Nexus Core environment..."

# Step 1: Verify Docker Desktop is running
if (-not (Test-DockerRunning)) {
    Write-Error "Docker Desktop is not running"
    Write-Host "  Please start Docker Desktop and try again"
    exit 1
}
Write-Success "Docker Desktop running"

# Step 2: Get docker-compose.yml path
$dockerComposePath = Get-DockerComposePath

if (-not (Test-Path $dockerComposePath)) {
    Write-Error "docker-compose.yml not found at: $dockerComposePath"
    exit 1
}
Write-Success "docker-compose.yml found"

# Step 3: Check if containers already running
$runningContainers = docker ps --format "{{.Names}}" 2>$null

$alreadyRunning = @()
foreach ($container in $REQUIRED_CONTAINERS) {
    if ($runningContainers -contains $container) {
        $alreadyRunning += $container
    }
}

if ($alreadyRunning.Count -gt 0) {
    Write-Warning "Some containers already running:"
    foreach ($container in $alreadyRunning) {
        Write-Host "    - $container"
    }
    Write-Host ""
    $response = Read-Host "Restart containers? (yes/no)"
    if ($response -ne "yes") {
        Write-Host "Startup cancelled"
        exit 0
    }

    # Stop existing containers first
    Write-Step "Stopping existing containers..."
    $composeDir = Split-Path -Parent $dockerComposePath
    Push-Location $composeDir
    try {
        docker-compose down 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Error stopping containers (continuing anyway)"
        } else {
            Write-Success "Existing containers stopped"
        }
    } finally {
        Pop-Location
    }
}

# Step 4: Verify Transfer Station exists
if (-not (Test-TransferStationAccessible -TransferStationPath $TRANSFER_STATION)) {
    Write-Error "Transfer Station not accessible at: $TRANSFER_STATION"
    Write-Host "  Please ensure the Transfer Station directory exists"
    exit 1
}
Write-Success "Transfer Station accessible"

# Step 5: Start Docker Compose services
Write-Step "Starting services..."

$composeDir = Split-Path -Parent $dockerComposePath
Push-Location $composeDir
try {
    $output = docker-compose up -d 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services"
        Write-Host "  Error output:"
        Write-Host $output
        exit 1
    }
} finally {
    Pop-Location
}

Write-Success "Services starting..."

# Step 6: Wait for health checks (if -Wait flag)
if ($Wait) {
    Write-Host ""
    Write-Host "  Waiting for health checks (timeout: $HEALTH_CHECK_TIMEOUT seconds)..."
    Write-Host ""

    $startTime = Get-Date
    $allHealthy = $false

    while (-not $allHealthy) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds

        if ($elapsed -gt $HEALTH_CHECK_TIMEOUT) {
            Write-Host ""
            Write-Error "Health check timeout exceeded ($HEALTH_CHECK_TIMEOUT seconds)"
            Write-Host ""
            Write-Host "  Checking individual container status:"

            foreach ($container in $REQUIRED_CONTAINERS) {
                $status = Get-ContainerStatus -ContainerName $container
                Write-Host "    - $container : Status=$($status.Status), Health=$($status.Health)"

                if ($status.Status -eq "exited" -or $status.Status -eq "dead") {
                    Write-Host "      Logs:"
                    docker logs $container --tail 20 2>&1 | ForEach-Object { Write-Host "        $_" }
                }
            }

            Write-Host ""
            exit 1
        }

        # Check each container
        $healthyCount = 0

        foreach ($container in $REQUIRED_CONTAINERS) {
            $status = Get-ContainerStatus -ContainerName $container

            if ($status.Health -eq "healthy" -or
                ($status.Status -eq "running" -and $status.Health -eq "none")) {
                $healthyCount++
            } elseif ($status.Status -in @("exited", "dead")) {
                Write-Host ""
                Write-Error "Container $container failed to start"
                Write-Host "  Logs:"
                docker logs $container --tail 20 2>&1 | ForEach-Object { Write-Host "    $_" }
                Write-Host ""
                exit 1
            }
        }

        if ($healthyCount -eq $REQUIRED_CONTAINERS.Count) {
            $allHealthy = $true
        } else {
            Start-Sleep -Seconds 2
        }
    }

    # Display final status
    Write-Host ""
    foreach ($container in $REQUIRED_CONTAINERS) {
        $status = Get-ContainerStatus -ContainerName $container
        $uptime = Get-ContainerUptime -ContainerName $container

        $healthIndicator = if ($status.Health -eq "healthy" -or
                               ($status.Status -eq "running" -and $status.Health -eq "none")) {
            "✓"
        } else {
            "⏳"
        }

        Write-Host "  $healthIndicator $container`: healthy ($uptime)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Step "All services started successfully"
Write-Host ""

exit 0
