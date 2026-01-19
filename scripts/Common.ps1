# Common Helper Functions for Nexus Core PowerShell Scripts
# Reference: POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md
#
# Purpose: Shared functions for status output, Docker operations, and utilities
# Used by: All Nexus Core PowerShell test runner scripts

# ==========================================================================
# Status Output Helpers
# ==========================================================================

function Write-Step {
    <#
    .SYNOPSIS
    Outputs a step message with timestamp

    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Write-Success {
    <#
    .SYNOPSIS
    Outputs a success message with checkmark

    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Error {
    <#
    .SYNOPSIS
    Outputs an error message with X mark

    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    <#
    .SYNOPSIS
    Outputs a warning message with warning symbol

    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-Host "  ⚠ $Message" -ForegroundColor Yellow
}

# ==========================================================================
# Docker Helpers
# ==========================================================================

function Test-DockerRunning {
    <#
    .SYNOPSIS
    Checks if Docker Desktop is running

    .OUTPUTS
    Boolean - True if Docker is running, False otherwise
    #>
    try {
        $result = docker version 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-ContainerStatus {
    <#
    .SYNOPSIS
    Gets the status of a Docker container

    .PARAMETER ContainerName
    Name of the container to check

    .OUTPUTS
    PSCustomObject with Status and Health properties
    #>
    param([string]$ContainerName)

    try {
        $inspect = docker inspect $ContainerName 2>$null | ConvertFrom-Json

        if ($null -eq $inspect) {
            return @{
                Status = "not found"
                Health = "unknown"
            }
        }

        $status = $inspect[0].State.Status
        $health = if ($inspect[0].State.Health) {
            $inspect[0].State.Health.Status
        } else {
            "none"
        }

        return @{
            Status = $status
            Health = $health
        }
    } catch {
        return @{
            Status = "error"
            Health = "unknown"
        }
    }
}

function Wait-ContainerHealthy {
    <#
    .SYNOPSIS
    Waits for a container to become healthy

    .PARAMETER ContainerName
    Name of the container to wait for

    .PARAMETER TimeoutSeconds
    Maximum time to wait in seconds (default 120)

    .OUTPUTS
    Boolean - True if container became healthy, False if timeout
    #>
    param(
        [string]$ContainerName,
        [int]$TimeoutSeconds = 120
    )

    $elapsed = 0
    $checkInterval = 2

    while ($elapsed -lt $TimeoutSeconds) {
        $containerStatus = Get-ContainerStatus -ContainerName $ContainerName

        # Container is healthy
        if ($containerStatus.Health -eq "healthy") {
            return $true
        }

        # Container is running but has no health check
        if ($containerStatus.Status -eq "running" -and $containerStatus.Health -eq "none") {
            return $true
        }

        # Container failed
        if ($containerStatus.Status -in @("exited", "dead")) {
            return $false
        }

        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval
    }

    return $false
}

# ==========================================================================
# Path Helpers
# ==========================================================================

function Test-TransferStationAccessible {
    <#
    .SYNOPSIS
    Checks if Transfer Station path is accessible

    .PARAMETER TransferStationPath
    Path to Transfer Station (default: E:\Transfer_Station)

    .OUTPUTS
    Boolean - True if accessible, False otherwise
    #>
    param([string]$TransferStationPath = "E:\Transfer_Station")

    return Test-Path -Path $TransferStationPath
}

function Get-DockerComposePath {
    <#
    .SYNOPSIS
    Gets the path to docker-compose.yml in the project root

    .OUTPUTS
    String - Full path to docker-compose.yml
    #>
    # Navigate up from scripts directory to project root
    $scriptDir = Split-Path -Parent $PSScriptRoot
    $dockerComposePath = Join-Path $scriptDir "docker-compose.yml"

    return $dockerComposePath
}

# ==========================================================================
# Confirmation Helpers
# ==========================================================================

function Confirm-DestructiveAction {
    <#
    .SYNOPSIS
    Prompts user for confirmation before destructive action

    .PARAMETER Message
    The warning message to display

    .PARAMETER Force
    If true, skips confirmation prompt

    .OUTPUTS
    Boolean - True if user confirmed or Force is true, False otherwise
    #>
    param(
        [string]$Message,
        [switch]$Force
    )

    if ($Force) {
        return $true
    }

    Write-Host ""
    Write-Warning $Message
    Write-Host ""
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"

    return $confirmation -eq "yes"
}

# ==========================================================================
# Formatting Helpers
# ==========================================================================

function Format-ContainerTable {
    <#
    .SYNOPSIS
    Formats container status information as a table

    .PARAMETER Containers
    Array of container status objects

    .OUTPUTS
    Formatted table string
    #>
    param([array]$Containers)

    if ($Containers.Count -eq 0) {
        return "No containers found"
    }

    # Create header
    $output = "`nService                  Status      Health      Uptime      Ports`n"
    $output += "─────────────────────────────────────────────────────────────────────`n"

    foreach ($container in $Containers) {
        $name = $container.Name.PadRight(24)
        $status = $container.Status.PadRight(11)
        $health = $container.Health.PadRight(11)
        $uptime = $container.Uptime.PadRight(11)
        $ports = $container.Ports

        $output += "$name $status $health $uptime $ports`n"
    }

    return $output
}

function Get-ContainerUptime {
    <#
    .SYNOPSIS
    Gets the uptime of a container in human-readable format

    .PARAMETER ContainerName
    Name of the container

    .OUTPUTS
    String - Uptime in format like "5m 23s"
    #>
    param([string]$ContainerName)

    try {
        $inspect = docker inspect $ContainerName 2>$null | ConvertFrom-Json

        if ($null -eq $inspect) {
            return "unknown"
        }

        $startedAt = [DateTime]::Parse($inspect[0].State.StartedAt)
        $uptime = (Get-Date) - $startedAt

        if ($uptime.TotalHours -ge 1) {
            return "{0}h {1}m" -f [Math]::Floor($uptime.TotalHours), $uptime.Minutes
        } elseif ($uptime.TotalMinutes -ge 1) {
            return "{0}m {1}s" -f [Math]::Floor($uptime.TotalMinutes), $uptime.Seconds
        } else {
            return "{0}s" -f [Math]::Floor($uptime.TotalSeconds)
        }
    } catch {
        return "unknown"
    }
}

function Get-ContainerPorts {
    <#
    .SYNOPSIS
    Gets the port mappings of a container

    .PARAMETER ContainerName
    Name of the container

    .OUTPUTS
    String - Port mappings in format like "8000:8000"
    #>
    param([string]$ContainerName)

    try {
        $inspect = docker inspect $ContainerName 2>$null | ConvertFrom-Json

        if ($null -eq $inspect) {
            return "-"
        }

        $ports = $inspect[0].NetworkSettings.Ports

        if ($null -eq $ports -or $ports.PSObject.Properties.Count -eq 0) {
            return "-"
        }

        $portMappings = @()
        foreach ($portKey in $ports.PSObject.Properties.Name) {
            $portBindings = $ports.$portKey
            if ($null -ne $portBindings -and $portBindings.Count -gt 0) {
                $hostPort = $portBindings[0].HostPort
                $containerPort = $portKey -replace '/tcp', '' -replace '/udp', ''
                $portMappings += "$hostPort:$containerPort"
            }
        }

        if ($portMappings.Count -gt 0) {
            return $portMappings -join ", "
        } else {
            return "-"
        }
    } catch {
        return "-"
    }
}

# ==========================================================================
# Export Functions
# ==========================================================================

# Make all functions available when this file is dot-sourced
Export-ModuleMember -Function *
