# Status for Nexus Core Environment
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md - Environment Control
# Test ID: PS-TEST-001
#
# Purpose: Display current container health and status
#
# Usage:
#   .\Status-NexusEnv.ps1           # Show container status
#   .\Status-NexusEnv.ps1 -Logs     # Include recent logs
#   .\Status-NexusEnv.ps1 -Verbose  # Detailed diagnostics
#
# Requirements from spec:
# - Show container status (running/stopped/unhealthy)
# - Display container health check results
# - Show recent container logs (last 20 lines)
# - Check Transfer Station mount accessibility
# - Exit with appropriate codes

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Logs,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Import common helper functions
. $PSScriptRoot/Common.ps1

# ==========================================================================
# Configuration
# ==========================================================================

$TRANSFER_STATION = "E:\Transfer_Station"
$REQUIRED_CONTAINERS = @(
    "nexus_db",
    "nexus_api",
    "nexus_ingestion_worker",
    "nexus_validator"
)

# ==========================================================================
# Main Script
# ==========================================================================

Write-Step "Nexus Core Environment Status"
Write-Host ""

# Step 1: Check if Docker is running
if (-not (Test-DockerRunning)) {
    Write-Error "Docker Desktop is not running"
    exit 1
}

# Step 2: Collect container information
$containerInfo = @()
$unhealthyCount = 0
$stoppedCount = 0

foreach ($containerName in $REQUIRED_CONTAINERS) {
    $status = Get-ContainerStatus -ContainerName $containerName
    $uptime = Get-ContainerUptime -ContainerName $containerName
    $ports = Get-ContainerPorts -ContainerName $containerName

    # Determine health color
    $healthColor = "Green"
    if ($status.Health -in @("unhealthy", "starting")) {
        $healthColor = "Yellow"
        $unhealthyCount++
    } elseif ($status.Status -in @("exited", "dead", "not found")) {
        $healthColor = "Red"
        $stoppedCount++
    }

    $containerInfo += [PSCustomObject]@{
        Name = $containerName
        Status = $status.Status
        Health = $status.Health
        Uptime = $uptime
        Ports = $ports
        HealthColor = $healthColor
    }
}

# Step 3: Display container table
Write-Host "Service                  Status      Health      Uptime      Ports"
Write-Host "─────────────────────────────────────────────────────────────────────"

foreach ($container in $containerInfo) {
    $name = $container.Name.PadRight(24)
    $status = $container.Status.PadRight(11)
    $health = $container.Health.PadRight(11)
    $uptime = $container.Uptime.PadRight(11)
    $ports = $container.Ports

    Write-Host "$name $status $health $uptime $ports" -ForegroundColor $container.HealthColor
}

Write-Host ""

# Step 4: Check Transfer Station
$transferStationStatus = if (Test-TransferStationAccessible -TransferStationPath $TRANSFER_STATION) {
    "✓ accessible"
} else {
    "✗ not accessible"
}

$transferStationColor = if (Test-TransferStationAccessible -TransferStationPath $TRANSFER_STATION) {
    "Green"
} else {
    "Red"
}

Write-Host "Transfer Station: $TRANSFER_STATION $transferStationStatus" -ForegroundColor $transferStationColor
Write-Host ""

# Step 5: Overall status
$overallStatus = if ($stoppedCount -eq 0 -and $unhealthyCount -eq 0) {
    "✓ All services healthy"
} elseif ($stoppedCount -gt 0) {
    "✗ $stoppedCount service(s) stopped"
} else {
    "⚠ $unhealthyCount service(s) unhealthy or starting"
}

$overallColor = if ($stoppedCount -eq 0 -and $unhealthyCount -eq 0) {
    "Green"
} elseif ($stoppedCount -gt 0) {
    "Red"
} else {
    "Yellow"
}

Write-Host "Overall Status: $overallStatus" -ForegroundColor $overallColor
Write-Host ""

# Step 6: Show logs if requested
if ($Logs) {
    Write-Step "Recent Logs (last 20 lines per container)"
    Write-Host ""

    foreach ($container in $REQUIRED_CONTAINERS) {
        Write-Host "  === $container ===" -ForegroundColor Cyan
        docker logs $container --tail 20 2>&1 | ForEach-Object {
            Write-Host "  $_"
        }
        Write-Host ""
    }
}

# Step 7: Show verbose diagnostics if requested
if ($Verbose) {
    Write-Step "Verbose Diagnostics"
    Write-Host ""

    foreach ($containerName in $REQUIRED_CONTAINERS) {
        Write-Host "  === $containerName ===" -ForegroundColor Cyan

        try {
            $inspect = docker inspect $containerName 2>$null | ConvertFrom-Json

            if ($null -ne $inspect) {
                $details = $inspect[0]

                Write-Host "    Container ID: $($details.Id.Substring(0, 12))"
                Write-Host "    Image: $($details.Config.Image)"
                Write-Host "    Created: $($details.Created)"
                Write-Host "    Started: $($details.State.StartedAt)"
                Write-Host "    Status: $($details.State.Status)"

                if ($details.State.Health) {
                    Write-Host "    Health Status: $($details.State.Health.Status)"
                    Write-Host "    Failed Health Checks: $($details.State.Health.FailingStreak)"

                    if ($details.State.Health.Log -and $details.State.Health.Log.Count -gt 0) {
                        $lastCheck = $details.State.Health.Log[-1]
                        Write-Host "    Last Health Check:"
                        Write-Host "      Exit Code: $($lastCheck.ExitCode)"
                        Write-Host "      Output: $($lastCheck.Output)"
                    }
                }

                # Show environment variables
                if ($details.Config.Env) {
                    Write-Host "    Environment:"
                    foreach ($env in $details.Config.Env) {
                        if ($env -notlike "*PASSWORD*" -and $env -notlike "*SECRET*") {
                            Write-Host "      $env"
                        }
                    }
                }

                # Show mounts
                if ($details.Mounts) {
                    Write-Host "    Mounts:"
                    foreach ($mount in $details.Mounts) {
                        Write-Host "      $($mount.Source) → $($mount.Destination)"
                    }
                }
            }
        } catch {
            Write-Host "    Error retrieving details: $_" -ForegroundColor Red
        }

        Write-Host ""
    }
}

# Exit code based on status
if ($stoppedCount -gt 0) {
    exit 1  # Critical: containers stopped
} elseif ($unhealthyCount -gt 0) {
    exit 2  # Warning: containers unhealthy
} else {
    exit 0  # Success: all healthy
}
