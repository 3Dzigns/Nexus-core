# Nexus Core Test Scripts

PowerShell scripts for environment control, integration testing, validation, and cleanup of the Nexus Core ingestion pipeline.

## Overview

This test suite provides comprehensive tooling for:
1. **Environment Control** - Start/stop/status Docker containers
2. **Integration Testing** - End-to-end ingestion pipeline validation
3. **Validation Execution** - Post-ingestion certification
4. **Cleanup & Reset** - Test data removal and environment restoration

### Test Workflow Coverage

Complete ingestion pipeline testing:
1. Source file discovery
2. Admin approval workflow
3. Dual extraction (Docling + Unstructured)
4. Normalization, enrichment, and chunking
5. Storage and indexing (chunks, embeddings, FTS, vector)
6. Validation and certification
7. Cleanup and environment restoration

## Prerequisites

### Docker Desktop

Docker Desktop must be running on Windows before executing any test scripts.

### Required Services

All Docker containers must be running. Use the environment control scripts:

```powershell
# Start all services
.\scripts\Start-NexusEnv.ps1

# Verify containers are healthy
.\scripts\Status-NexusEnv.ps1
```

Required containers:
- `nexus_db` - PostgreSQL with pgvector
- `nexus_api` - FastAPI application
- `nexus_ingestion_worker` - Ingestion pipeline worker
- `nexus_validator` - Validation service

### Test Data

Place a test PDF in `scripts/tests/test_data/` directory:
```
scripts/tests/test_data/
└── test_pathfinder_rulebook.pdf
```

Recommended test PDFs:
- Pathfinder 1e Core Rulebook (small section, 5-10 pages)
- Cyberpunk RED Quick Start Guide
- Any TTRPG rulebook PDF (avoid full core books for faster testing)

## Quick Start

Complete test workflow with new orchestration scripts:

```powershell
# 1. Start environment
.\scripts\Start-NexusEnv.ps1

# 2. Check status
.\scripts\Status-NexusEnv.ps1

# 3. Run integration test (orchestrated wrapper)
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test_pathfinder_rulebook.pdf"

# 4. Reset environment (clean all test data)
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force

# 5. Stop environment
.\scripts\Stop-NexusEnv.ps1
```

## Available Scripts

### Environment Control (scripts/)

| Script | Purpose | Location |
|--------|---------|----------|
| `Start-NexusEnv.ps1` | Start all Docker containers with health checks | `scripts/Start-NexusEnv.ps1` |
| `Stop-NexusEnv.ps1` | Gracefully stop all containers | `scripts/Stop-NexusEnv.ps1` |
| `Status-NexusEnv.ps1` | Display container status dashboard | `scripts/Status-NexusEnv.ps1` |

### Test Execution (scripts/tests/)

| Script | Purpose | Location |
|--------|---------|----------|
| `Run-IngestionTests.ps1` | Orchestrated integration test wrapper | `scripts/tests/Run-IngestionTests.ps1` |
| `test_ingestion_e2e.ps1` | Direct E2E integration test | `scripts/tests/test_ingestion_e2e.ps1` |
| `Run-Validation.ps1` | Validation execution and reporting | `scripts/tests/Run-Validation.ps1` |

### Cleanup (scripts/tests/)

| Script | Purpose | Location |
|--------|---------|----------|
| `cleanup_test_data.ps1` | Remove single doc_id test data | `scripts/tests/cleanup_test_data.ps1` |
| `Reset-NexusTestEnv.ps1` | Full environment reset | `scripts/tests/Reset-NexusTestEnv.ps1` |

## Usage

### Environment Control Scripts

#### Start-NexusEnv.ps1

Start all required Docker containers with automated health verification.

```powershell
# Start and wait for all containers to be healthy
.\scripts\Start-NexusEnv.ps1

# Start without waiting for health checks
.\scripts\Start-NexusEnv.ps1 -Wait:$false
```

**Features:**
- Verifies Docker Desktop is running
- Checks if containers already running (prompts for restart)
- Executes `docker-compose up -d`
- Polls container health status with 120s timeout
- Displays startup progress for each service
- Surfaces container logs on startup failure
- Verifies Transfer Station mount path exists

**Exit Codes:**
- `0` - All services started and healthy
- `1` - Startup failed (Docker not running, health check timeout, etc.)

**Expected Output:**
```
[HH:mm:ss] Starting Nexus Core environment...
  ✓ Docker Desktop running
  ✓ docker-compose.yml found
  ✓ Transfer Station accessible
  ⏳ Starting services...
  ✓ nexus_db: healthy (5s)
  ✓ nexus_api: healthy (12s)
  ✓ nexus_ingestion_worker: healthy (15s)
  ✓ nexus_validator: healthy (18s)

[HH:mm:ss] All services started successfully
```

---

#### Stop-NexusEnv.ps1

Gracefully stop all running Docker containers.

```powershell
# Graceful shutdown (default, 30s timeout)
.\scripts\Stop-NexusEnv.ps1

# Force stop (skip graceful shutdown)
.\scripts\Stop-NexusEnv.ps1 -Force

# Stop but preserve Docker volumes
.\scripts\Stop-NexusEnv.ps1 -PreserveData
```

**Features:**
- Checks if containers are running
- Executes `docker-compose down` with configurable timeout
- Displays shutdown progress for each service
- Verifies all containers stopped
- Optional force stop and volume preservation

**Exit Codes:**
- `0` - All services stopped successfully
- `1` - Shutdown failed or containers still running

**Expected Output:**
```
[HH:mm:ss] Stopping Nexus Core environment...
  Stopping containers:
    - nexus_validator
    - nexus_ingestion_worker
    - nexus_api
    - nexus_db

  Gracefully stopping containers...
  ✓ All services stopped

[HH:mm:ss] Environment shutdown complete
```

---

#### Status-NexusEnv.ps1

Display current container health and status dashboard.

```powershell
# Show container status
.\scripts\Status-NexusEnv.ps1

# Include recent logs (last 20 lines per container)
.\scripts\Status-NexusEnv.ps1 -Logs

# Show detailed diagnostics
.\scripts\Status-NexusEnv.ps1 -Verbose
```

**Features:**
- Shows container status (running/stopped/unhealthy)
- Displays health check results
- Shows container uptime and port mappings
- Color-coded output (green=healthy, yellow=starting, red=unhealthy)
- Optional recent logs display
- Optional verbose diagnostics (container ID, image, environment, mounts)

**Exit Codes:**
- `0` - All services healthy
- `1` - Containers stopped
- `2` - Containers unhealthy

**Expected Output:**
```
[HH:mm:ss] Nexus Core Environment Status

Service                  Status      Health      Uptime      Ports
─────────────────────────────────────────────────────────────────────
nexus_db                 running     healthy     5m 23s      5432:5432
nexus_api                running     healthy     5m 18s      8000:8000
nexus_ingestion_worker   running     healthy     5m 12s      8001:8001
nexus_validator          running     healthy     5m 8s       8004:8004

Transfer Station: E:\Transfer_Station ✓ accessible

Overall Status: ✓ All services healthy
```

---

### Test Execution Scripts

#### Run-IngestionTests.ps1 (Orchestrated Wrapper)

Standardized wrapper for ingestion test execution with configurable parameters.

```powershell
# Basic usage (uses defaults: pathfinder_1e, PREMIUM, 600s timeout)
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test_pathfinder_rulebook.pdf"

# With custom system and tier
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "cyberpunk_guide.pdf" -System "cyberpunk_red" -Tier "BASIC"

# With custom timeout and verbose output
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test.pdf" -Timeout 900 -Verbose

# Skip cleanup after test
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test.pdf" -SkipCleanup

# Save execution logs to file
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test.pdf" -SaveLogs
```

**Parameters:**
- `-TestPDF` (Required) - Path to test PDF file (relative or absolute)
- `-System` (Optional) - System ID: `pathfinder_1e`, `cyberpunk_red`, `starfinder`, `dnd_5e` (default: `pathfinder_1e`)
- `-Tier` (Optional) - Tier: `FREE`, `BASIC`, `PREMIUM` (default: `PREMIUM`)
- `-Timeout` (Optional) - Overall test timeout in seconds (default: 600)
- `-SkipCleanup` (Optional) - Don't run cleanup after test
- `-SaveLogs` (Optional) - Save logs to `scripts/tests/logs/test_results_<timestamp>.log`
- `-Verbose` (Optional) - Enable detailed logging

**Features:**
- Pre-flight checks (containers healthy, PDF exists, Transfer Station accessible)
- Places PDF in Transfer Station sources directory
- Waits for discovery and approval
- Monitors ingestion pipeline execution
- Parses validation report and displays results
- Captures test timing and generates summary report
- Optional automatic cleanup via `cleanup_test_data.ps1`

**Exit Codes:**
- `0` - Test passed (source status: INGESTED, validation: PASS)
- `1` - Test failed (ingestion failed, validation failed, or timeout)
- `2` - Pre-flight check failed (containers not running, PDF not found, etc.)

**Expected Output:**
```
[HH:mm:ss] Running Ingestion Tests

  Configuration:
  - Test PDF: test_pathfinder_rulebook.pdf
  - System: pathfinder_1e
  - Tier: PREMIUM
  - Timeout: 600 seconds

[HH:mm:ss] Pre-flight checks
  ✓ Docker Desktop running
  ✓ All containers healthy
  ✓ API is healthy: ok
  ✓ Transfer Station accessible

[HH:mm:ss] Verifying test PDF
  ✓ Test PDF found (5.2 MB)
  - Name: test_pathfinder_rulebook.pdf
  - SHA-256: 1A2B3C4D...
  - Expected doc_id: test_pathfinder_rulebook.pdf__1A2B3C4D...

[HH:mm:ss] Executing E2E ingestion test
  ✓ Test PDF placed in Transfer Station
  Waiting for discovery...
  ✓ Source discovered
  Approving source...
  ✓ Source approved: APPROVED
  Waiting for ingestion pipeline...
  ✓ Ingestion completed: INGESTED
  ✓ Validation passed: 9 checks

[HH:mm:ss] Test Summary

  Status: PASSED ✓
  Duration: 124 seconds
  doc_id: test_pathfinder_rulebook.pdf__1A2B3C4D...
  Chunks: 87
  Validation: PASS

[HH:mm:ss] Cleaning up test data
  ✓ Test data cleaned up

[HH:mm:ss] Test execution complete ✓
```

---

#### test_ingestion_e2e.ps1 (Direct Execution)

Run the complete integration test directly (legacy approach):
```powershell
cd E:\Nexus_Core
.\scripts\tests\test_ingestion_e2e.ps1
```

**Expected runtime:** 5-15 minutes (depending on PDF size and extraction speed)

**What it does:**
1. Validates prerequisites (Docker, API health, Transfer Station)
2. Places test PDF in Transfer Station sources directory
3. Waits for discovery scanner to detect source (max 120s)
4. Verifies source status is `PENDING_APPROVAL`
5. Approves source via admin API
6. Waits for ingestion pipeline to complete (max 600s)
7. Verifies final status is `INGESTED`
8. Checks validation report exists and passed
9. Verifies dual artifacts (manifests, chunks) were created
10. Queries database to confirm chunks and embeddings stored

**Success criteria:**
- Exit code: 0
- Source status: `INGESTED`
- Validation status: `PASS`
- All artifacts present (raw manifests, normalized manifests, enriched manifests, chunks)
- Database records created (chunks, embeddings, FTS index entries)

**Failure scenarios:**
- Exit code: 1
- Logs error details to console
- Check Docker logs for stack traces:
  ```powershell
  docker logs nexus_ingestion_worker
  docker logs nexus_validator
  ```

---

#### Run-Validation.ps1

Invoke validation agent and parse results for a specific document.

```powershell
# Run validation for a specific doc_id
.\scripts\tests\Run-Validation.ps1 -DocId "test_pathfinder_rulebook.pdf__1A2B3C4D..."

# Run validation with detailed output
.\scripts\tests\Run-Validation.ps1 -DocId "..." -Verbose

# Run validation and save report copy
.\scripts\tests\Run-Validation.ps1 -DocId "..." -OutputPath "C:\Reports"
```

**Parameters:**
- `-DocId` (Required) - Document identifier to validate
- `-OutputPath` (Optional) - Directory to save validation report copy
- `-Verbose` (Optional) - Show detailed check results with JSON details

**Features:**
- Executes validator via Docker container
- Waits for validation completion (max 60s)
- Parses validation report JSON from Transfer Station
- Displays overall status (PASS/FAIL)
- Shows all validation checks with pass/fail indicators
- Reports warnings if present
- Optional copy of validation report to custom location

**Exit Codes:**
- `0` - Validation PASS
- `1` - Validation FAIL
- `2` - Validation error (report not found, validator failed, etc.)

**Expected Output:**
```
[HH:mm:ss] Running Validation for doc_id: test_pathfinder_rulebook.pdf__1A2B3C4D...

  Executing validator...
  ⏳ Running 9 validation checks...

[HH:mm:ss] Validation Report

Status: PASS ✓

Checks:
  ✓ source_exists                : Source record exists in database
  ✓ dual_manifests_present       : Docling and Unstructured manifests found
  ✓ dual_chunks_present          : Chunk sets exist for both extractors
  ✓ chunks_in_database           : All chunks stored in database
  ✓ embeddings_present           : Embeddings generated for all chunks
  ✓ fts_index_entries            : FTS index entries created
  ✓ no_orphaned_chunks           : No orphaned chunks in database
  ✓ chunk_id_format              : All chunk IDs follow format spec
  ✓ artifact_integrity           : All artifact checksums valid

Summary:
  Total Checks: 9
  Passed: 9
  Failed: 0

Report saved to: E:\Transfer_Station\artifacts\reports\<doc_id>\validation_report.json
```

---

### Cleanup Scripts

#### cleanup_test_data.ps1

Remove test data for a specific document identifier.

After testing, clean up all test data:
```powershell
.\scripts\tests\cleanup_test_data.ps1 -DocId "test_pathfinder_rulebook.pdf__ABC123..."
```

**Safety confirmation:**
- Script prompts for confirmation (unless `-Force` flag used)
- Shows doc_id, filename, and current status before deletion

**What it deletes:**
1. Source file from Transfer Station
2. All database records:
   - FTS index entries
   - Embeddings
   - Chunks
   - Manifests
   - Validation reports
   - Governance events
   - Source links
   - Source record
3. All artifacts:
   - Raw manifests
   - Normalized manifests
   - Enriched manifests
   - Chunks (JSONL files)
   - Assets (extracted images)
   - Validation reports

**Force cleanup (no confirmation):**
```powershell
.\scripts\tests\cleanup_test_data.ps1 -DocId "..." -Force
```

---

#### Reset-NexusTestEnv.ps1

Comprehensive cleanup and reset to clean state - removes ALL test data and artifacts.

```powershell
# Interactive reset (shows summary and prompts for confirmation)
.\scripts\tests\Reset-NexusTestEnv.ps1

# Force reset without confirmation
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force

# Reset but keep Docker volumes
.\scripts\tests\Reset-NexusTestEnv.ps1 -KeepVolumes

# Dry run (show what would be deleted without executing)
.\scripts\tests\Reset-NexusTestEnv.ps1 -DryRun
```

**Parameters:**
- `-Force` (Optional) - Skip confirmation prompts
- `-KeepVolumes` (Optional) - Don't delete Docker volumes
- `-DryRun` (Optional) - Show what would be deleted without executing

**Features:**
- Pre-reset statistics (database counts, artifact sizes)
- Safety confirmation prompt (shows exactly what will be deleted)
- Database cleanup in dependency order (per CLEANUP_STRATEGY_v1.0.md)
- Filesystem cleanup (sources + artifacts)
- Optional Docker volume deletion
- Automatic container restart after cleanup
- Post-reset verification (confirms empty state)

**What it deletes:**
1. **Database records** (all tables in dependency order):
   - FTS index entries
   - Embeddings
   - Chunks
   - Manifests
   - Validation reports
   - Governance events
   - Source links
   - Sources
2. **Filesystem artifacts**:
   - All files in `E:\Transfer_Station\sources\*`
   - All files in `E:\Transfer_Station\artifacts\*`
3. **Docker volumes** (optional):
   - Database volume (if `-KeepVolumes` not specified)

**Exit Codes:**
- `0` - Reset completed successfully
- `1` - Reset failed or verification failed

**Expected Output:**
```
[HH:mm:ss] Nexus Core Environment Reset

[HH:mm:ss] Pre-reset status:
  Database:
    - Sources: 5 records
    - Chunks: 423 records
    - Embeddings: 423 records
    - FTS Index: 423 records
    - Governance Events: 15 records
    - Manifests: 10 records
    - Validation Reports: 5 records
    - Source Links: 8 records
  Artifacts:
    - Size: 1.2 GB
    - Files: 1,847

⚠ WARNING: This will DELETE all test data!

Database Records:
  - Sources: 5
  - Chunks: 423
  - Embeddings: 423
  - Other records: 461

Filesystem:
  - Artifacts: 1.2 GB (1,847 files)

Are you sure you want to continue? (yes/no): yes

[HH:mm:ss] Stopping containers...
  ✓ All containers stopped

[HH:mm:ss] Cleaning database...
  ✓ All database records deleted

[HH:mm:ss] Cleaning artifacts...
  ✓ Deleted E:\Transfer_Station\sources\ (5 files)
  ✓ Deleted E:\Transfer_Station\artifacts\ (1,847 files, 1.2 GB)

[HH:mm:ss] Restarting containers...
  ✓ All services started and healthy

[HH:mm:ss] Verification:
  ✓ Database tables empty
  ✓ Artifact directories clean
  ✓ All containers healthy

[HH:mm:ss] Environment reset complete ✓
```

---

### Finding doc_id for Cleanup

The E2E test script outputs the doc_id at the end:
```
Summary:
- doc_id: test_pathfinder_rulebook.pdf__1A2B3C4D...
```

Or query the API:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/sources" -Method Get
```

## Test Workflow Examples

### Example 1: Quick Test Cycle (Recommended)

Complete test cycle using orchestration scripts:

```powershell
# Step 1: Start Docker services
.\scripts\Start-NexusEnv.ps1

# Step 2: Verify all services healthy
.\scripts\Status-NexusEnv.ps1

# Step 3: Run orchestrated integration test (automatic cleanup)
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test_pathfinder_rulebook.pdf"

# Step 4: Run another test with different parameters (automatic cleanup)
.\scripts\tests\Run-IngestionTests.ps1 -TestPDF "cyberpunk_guide.pdf" -System "cyberpunk_red" -Tier "BASIC"

# Step 5: Full environment reset (clean ALL test data)
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force

# Step 6: Stop Docker services
.\scripts\Stop-NexusEnv.ps1
```

---

### Example 2: Manual Test Cycle (Legacy)

Traditional workflow using direct test scripts:

```powershell
# Step 1: Start Docker services
.\scripts\Start-NexusEnv.ps1

# Step 2: Verify all services healthy
.\scripts\Status-NexusEnv.ps1

# Step 3: Run E2E test directly
.\scripts\tests\test_ingestion_e2e.ps1

# Step 4: Review results
# - Check console output for success/failure
# - Review validation report in Transfer_Station/artifacts/reports/

# Step 5: Run standalone validation
.\scripts\tests\Run-Validation.ps1 -DocId "test_pathfinder_rulebook.pdf__..." -Verbose

# Step 6: Clean up single test data
.\scripts\tests\cleanup_test_data.ps1 -DocId "test_pathfinder_rulebook.pdf__..."

# Step 7 (Optional): Run additional tests
# - Place new PDF in test_data/
# - Re-run test_ingestion_e2e.ps1

# Step 8: Full environment reset when done
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force

# Step 9: Stop Docker services
.\scripts\Stop-NexusEnv.ps1
```

---

### Example 3: Development Iteration

Rapid iteration during development:

```powershell
# One-time setup
.\scripts\Start-NexusEnv.ps1

# Development loop
while ($true) {
    # Make code changes...

    # Test with automatic cleanup
    .\scripts\tests\Run-IngestionTests.ps1 -TestPDF "test.pdf"

    # Review results, fix bugs, repeat
}

# When done for the day
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force
.\scripts\Stop-NexusEnv.ps1
```

## Troubleshooting

### Environment issues

**Symptom:** Scripts fail with "Docker Desktop is not running" or container errors

**Solutions:**
```powershell
# Check environment status
.\scripts\Status-NexusEnv.ps1

# Check detailed diagnostics
.\scripts\Status-NexusEnv.ps1 -Verbose

# View recent container logs
.\scripts\Status-NexusEnv.ps1 -Logs

# Restart environment
.\scripts\Stop-NexusEnv.ps1 -Force
.\scripts\Start-NexusEnv.ps1
```

---

### Discovery timeout (source not detected)

**Symptom:** Test fails with "Discovery timeout - source not detected within 120 seconds"

**Causes:**
- Discovery scanner not running
- Transfer Station mount path incorrect
- File permissions issue

**Solutions:**
```powershell
# Check worker logs
docker logs nexus_ingestion_worker

# Verify Transfer Station mount
docker exec nexus_ingestion_worker ls /transfer_station/sources

# Check discovery scanner is polling
docker logs nexus_ingestion_worker | Select-String "scanning"

# Verify containers healthy
.\scripts\Status-NexusEnv.ps1
```

### Ingestion timeout (pipeline did not complete)

**Symptom:** Test fails with "Ingestion timeout - pipeline did not complete within 600 seconds"

**Causes:**
- Extraction libraries not installed (placeholder implementations)
- Worker crashed during processing
- Database connection issue

**Solutions:**
```powershell
# Check worker logs for errors
docker logs nexus_ingestion_worker --tail 100

# Check validator logs
docker logs nexus_validator

# Verify database connectivity
docker exec nexus_db psql -U nexus -d nexus_core -c "SELECT COUNT(*) FROM sources;"
```

### Validation failed

**Symptom:** Test completes but validation status is `FAIL`

**Causes:**
- Missing artifacts (extraction failed)
- Incomplete chunking
- Database records missing

**Solutions:**
```powershell
# Read validation report
$docId = "..." # Replace with actual doc_id
$reportPath = "E:\Transfer_Station\artifacts\reports\$docId\validation_report.json"
Get-Content $reportPath | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Check failed checks
(Get-Content $reportPath | ConvertFrom-Json).checks | Where-Object { -not $_.passed }
```

### Cleanup fails

**Symptom:** Cleanup script errors or verification fails

**Causes:**
- Database foreign key constraints
- File permissions
- Concurrent access

**Solutions:**
```powershell
# For single doc_id cleanup failures
.\scripts\tests\cleanup_test_data.ps1 -DocId "..." -Force

# For complete environment reset
.\scripts\tests\Reset-NexusTestEnv.ps1 -Force

# Manual database cleanup (CAUTION: DESTRUCTIVE)
docker exec nexus_db psql -U nexus -d nexus_core -c "DELETE FROM sources WHERE doc_id = '...';"

# Manual filesystem cleanup
Remove-Item -Path "E:\Transfer_Station\artifacts\manifests\..." -Recurse -Force
Remove-Item -Path "E:\Transfer_Station\artifacts\chunks\..." -Recurse -Force
```

---

### Reset environment fails

**Symptom:** Reset-NexusTestEnv.ps1 errors or verification fails

**Causes:**
- Containers not stopping properly
- Database not accessible
- File system permissions

**Solutions:**
```powershell
# Try dry run first to see what would be deleted
.\scripts\tests\Reset-NexusTestEnv.ps1 -DryRun

# Force stop all containers
.\scripts\Stop-NexusEnv.ps1 -Force

# Manual database reset (CAUTION: DESTRUCTIVE)
docker exec nexus_db psql -U nexus -d nexus_core << EOF
TRUNCATE TABLE fts_index CASCADE;
TRUNCATE TABLE embeddings CASCADE;
TRUNCATE TABLE chunks CASCADE;
TRUNCATE TABLE manifests CASCADE;
TRUNCATE TABLE validation_reports CASCADE;
TRUNCATE TABLE governance_events CASCADE;
TRUNCATE TABLE source_links CASCADE;
TRUNCATE TABLE sources CASCADE;
EOF

# Restart environment
.\scripts\Start-NexusEnv.ps1
```

## Aligned Documentation

All scripts implement requirements from:

- **`POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md`** - PowerShell test runner specification
- `TEST_PLAN_v1.0.md` - Testing strategy and execution rules
- `TEST_CASES_v1.0.md` - Concrete test case definitions (T-ING-001 through T-ING-014)
- `CLEANUP_STRATEGY_v1.0.md` - Deactivation and cleanup semantics
- `INGESTION_ARCHITECTURE_v1.0.md` - Complete pipeline architecture
- `VALIDATION_PLAN_v1.0.md` - Post-ingestion certification requirements

## Notes

### Container-Only Execution

Per `TEST_PLAN_v1.0.md`, **all business logic executes inside Docker containers**. PowerShell scripts only:
- Invoke container commands
- Place files in Transfer Station
- Call API endpoints
- Read results from filesystem/API

### Test Data Lifecycle

Test data follows strict lifecycle per `CLEANUP_STRATEGY_v1.0.md`:
1. **Creation**: PDF placed in Transfer Station
2. **Processing**: Ingestion pipeline creates artifacts
3. **Verification**: Validation certifies correctness
4. **Cleanup**: All records and artifacts deleted
5. **Restoration**: Environment returned to clean state

### No Synthetic Data

Per `TEST_PLAN_v1.0.md`, **no synthetic test data** is used. All tests use real TTRPG PDFs manually placed in test_data directory.

### Phase-Gated Testing

Tests execute according to phase boundaries:
- Phase 1: Discovery and approval
- Phase 2: Extraction
- Phase 3: Normalization, enrichment, chunking
- Phase 4: Storage, indexing, validation
- Phase 5: Deactivation (tested separately)

See `PHASE_MAP_v1.0.md` for phase-to-requirement-to-test mapping.
