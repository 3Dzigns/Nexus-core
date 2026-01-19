# Integration Test Scripts

PowerShell scripts for end-to-end integration testing of the Nexus Core ingestion pipeline.

## Overview

These scripts test the complete ingestion workflow:
1. Source file discovery
2. Admin approval workflow
3. Dual extraction (Docling + Unstructured)
4. Normalization, enrichment, and chunking
5. Storage and indexing (chunks, embeddings, FTS, vector)
6. Validation and certification
7. Cleanup and environment restoration

## Prerequisites

### Required Services

All Docker containers must be running:
```powershell
docker-compose up -d
```

Verify containers are healthy:
```powershell
docker ps
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

## Usage

### End-to-End Integration Test

Run the complete integration test:
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

### Cleanup Test Data

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

## Test Workflow Example

Complete test cycle with cleanup:

```powershell
# Step 1: Start Docker services
docker-compose up -d

# Step 2: Wait for services to be healthy (30-60 seconds)
docker ps

# Step 3: Run E2E test
.\scripts\tests\test_ingestion_e2e.ps1

# Step 4: Review results
# - Check console output for success/failure
# - Review validation report in Transfer_Station/artifacts/reports/

# Step 5: Clean up test data
.\scripts\tests\cleanup_test_data.ps1 -DocId "test_pathfinder_rulebook.pdf__..."

# Step 6 (Optional): Run additional tests with different PDFs
# - Place new PDF in test_data/
# - Update $TEST_PDF variable in test_ingestion_e2e.ps1
# - Re-run test

# Step 7: Stop Docker services (when done testing)
docker-compose down
```

## Troubleshooting

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
# Manual database cleanup (CAUTION: DESTRUCTIVE)
docker exec nexus_db psql -U nexus -d nexus_core -c "DELETE FROM sources WHERE doc_id = '...';"

# Manual filesystem cleanup
Remove-Item -Path "E:\Transfer_Station\artifacts\manifests\..." -Recurse -Force
Remove-Item -Path "E:\Transfer_Station\artifacts\chunks\..." -Recurse -Force
```

## Aligned Documentation

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
