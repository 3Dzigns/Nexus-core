"""Core validator orchestration.

Per INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md:
- Validator is an independent auditor
- Validates one source at a time
- Runs all 9 checks, generates reports, updates governance
- All-or-nothing: partial success is forbidden

Validation workflow:
1. Check preconditions (source in INGESTING state)
2. Run all 9 validation checks
3. Determine PASS (all checks pass) or FAIL (any check fails)
4. Generate reports (JSON + Markdown)
5. Write reports to disk
6. Create ValidationReport DB record
7. Update governance state (INGESTING → INGESTED or ERROR)
8. Return ValidationResult
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings
from nexus_core.governance.state_machine import GovernanceStateMachine
from nexus_core.models.source import (
    GovernanceStatus,
    Source,
    ValidationReport,
    ValidationStatus,
)
from nexus_core.validation.artifacts import get_artifact_structure
from nexus_core.validation.checks import (
    ArtifactPresenceCheck,
    CheckResult,
    ChunkIntegrityCheck,
    DeactivationCheck,
    DualExtractorCheck,
    GovernanceIntegrityCheck,
    OrphanedArtifactCheck,
    ProvenanceMetadataCheck,
    StorageIndexCheck,
    ToolVersionCheck,
)
from nexus_core.validation.exceptions import ValidationError, ValidationPreconditionError
from nexus_core.validation.reports import (
    generate_json_report,
    generate_markdown_report,
    write_reports,
)


@dataclass
class ValidationResult:
    """Result of validation run.

    Attributes:
        doc_id: Document identifier
        run_id: Validation run identifier (UUID)
        status: PASS or FAIL
        checks: List of check results
        report_path: Path to JSON report on disk
    """

    doc_id: str
    run_id: str
    status: ValidationStatus
    checks: list[CheckResult]
    report_path: str


class Validator:
    """Core validation orchestrator.

    Per VALIDATION_PLAN_v1.0.md, the validator:
    - Verifies all 9 mandatory checks
    - Generates reports
    - Updates governance state
    - Creates ValidationReport DB records

    The validator is non-destructive and deterministic.
    """

    # Validator version (semantic versioning)
    VERSION = "1.0.0"

    def __init__(self, session: AsyncSession, settings: Settings):
        """Initialize validator.

        Args:
            session: Async database session
            settings: Application settings (for transfer_station_path)
        """
        self.session = session
        self.settings = settings
        self.state_machine = GovernanceStateMachine(session)

    async def validate(self, doc_id: str) -> ValidationResult:
        """Run complete validation for a source.

        Per VALIDATION_PLAN_v1.0.md:
        - All checks must pass for PASS result
        - Any check failure results in FAIL
        - Reports generated regardless of outcome
        - Governance state updated appropriately

        Args:
            doc_id: Document identifier to validate

        Returns:
            ValidationResult with status and details

        Raises:
            ValidationPreconditionError: If preconditions not met
            ValidationError: If validation process fails
        """
        # Step 1: Check preconditions
        await self._check_preconditions(doc_id)

        # Generate run ID for this validation
        run_id = str(uuid.uuid4())

        # Step 2: Resolve artifact paths
        paths = get_artifact_structure(doc_id, self.settings.transfer_station_path)

        # Step 3: Run all 9 validation checks
        check_results = await self._run_all_checks(doc_id, paths)

        # Step 4: Determine overall status
        all_passed = all(check.passed for check in check_results)
        status = ValidationStatus.PASS if all_passed else ValidationStatus.FAIL

        # Step 5: Generate reports
        json_report = generate_json_report(
            doc_id=doc_id,
            run_id=run_id,
            status=status,
            checks=check_results,
            validator_version=self.VERSION,
        )

        md_report = generate_markdown_report(
            doc_id=doc_id,
            run_id=run_id,
            status=status,
            checks=check_results,
            validator_version=self.VERSION,
        )

        # Step 6: Write reports to disk
        reports_dir = Path(self.settings.transfer_station_path) / "artifacts" / "reports"
        json_path, md_path = write_reports(
            reports_dir=reports_dir,
            doc_id=doc_id,
            run_id=run_id,
            json_content=json_report,
            md_content=md_report,
        )

        # Step 7: Save validation record to database
        await self._save_validation_record(
            doc_id=doc_id,
            run_id=run_id,
            status=status,
            report_path=str(json_path),
            report_json=json_report,
        )

        # Step 8: Update governance state
        await self._update_governance_state(doc_id, status)

        # Step 9: Commit database changes
        await self.session.commit()

        return ValidationResult(
            doc_id=doc_id,
            run_id=run_id,
            status=status,
            checks=check_results,
            report_path=str(json_path),
        )

    async def _check_preconditions(self, doc_id: str) -> None:
        """Verify validation preconditions.

        Per VALIDATION_PLAN_v1.0.md Section 3:
        - Source must exist in governance
        - Source state must be INGESTING
        - Artifact directories must exist

        Args:
            doc_id: Document identifier

        Raises:
            ValidationPreconditionError: If preconditions not met
        """
        # Check source exists
        result = await self.session.execute(
            select(Source).where(Source.doc_id == doc_id)
        )
        source = result.scalar_one_or_none()

        if not source:
            raise ValidationPreconditionError(
                message=f"Source not found: {doc_id}",
                details={"doc_id": doc_id, "reason": "source_not_found"},
            )

        # Check source is in INGESTING state
        if source.status != GovernanceStatus.INGESTING:
            raise ValidationPreconditionError(
                message=f"Source state is {source.status.value}, expected INGESTING",
                details={
                    "doc_id": doc_id,
                    "current_state": source.status.value,
                    "expected_state": "INGESTING",
                },
            )

        # Check artifact directories exist
        paths = get_artifact_structure(doc_id, self.settings.transfer_station_path)
        if not paths.manifests_dir.exists():
            raise ValidationPreconditionError(
                message=f"Manifests directory does not exist: {paths.manifests_dir}",
                details={
                    "doc_id": doc_id,
                    "manifests_dir": str(paths.manifests_dir),
                },
            )

    async def _run_all_checks(
        self, doc_id: str, paths
    ) -> list[CheckResult]:
        """Execute all 9 validation checks.

        Per VALIDATION_PLAN_v1.0.md Section 5, all checks are mandatory.

        Args:
            doc_id: Document identifier
            paths: Resolved artifact paths

        Returns:
            List of CheckResult instances (one per check)
        """
        # Define all 9 checks in order
        check_classes = [
            GovernanceIntegrityCheck,        # Check 1
            ArtifactPresenceCheck,           # Check 2
            ProvenanceMetadataCheck,         # Check 3
            DualExtractorCheck,              # Check 4
            ChunkIntegrityCheck,             # Check 5
            StorageIndexCheck,               # Check 6
            ToolVersionCheck,                # Check 7
            DeactivationCheck,               # Check 8
            OrphanedArtifactCheck,           # Check 9
        ]

        results = []
        for check_class in check_classes:
            check = check_class(
                session=self.session,
                paths=paths,
                doc_id=doc_id,
            )
            result = await check.run()
            results.append(result)

        return results

    async def _save_validation_record(
        self,
        doc_id: str,
        run_id: str,
        status: ValidationStatus,
        report_path: str,
        report_json: dict,
    ) -> None:
        """Create ValidationReport database record.

        Args:
            doc_id: Document identifier
            run_id: Validation run identifier
            status: PASS or FAIL
            report_path: Path to JSON report file
            report_json: Report content as dict
        """
        validation_report = ValidationReport(
            doc_id=doc_id,
            run_id=run_id,
            status=status,
            report_path=report_path,
            report_json=report_json,
        )
        self.session.add(validation_report)

    async def _update_governance_state(
        self, doc_id: str, status: ValidationStatus
    ) -> None:
        """Update governance state based on validation result.

        Per VALIDATION_PLAN_v1.0.md Section 6:
        - PASS → transition to INGESTED
        - FAIL → transition to ERROR

        Args:
            doc_id: Document identifier
            status: Validation status

        Raises:
            ValidationError: If state transition fails
        """
        target_state = (
            GovernanceStatus.INGESTED
            if status == ValidationStatus.PASS
            else GovernanceStatus.ERROR
        )

        try:
            # Use governance state machine for transition
            await self.state_machine.transition(
                doc_id=doc_id,
                to_state=target_state,
                triggered_by="validator",
            )
        except Exception as e:
            raise ValidationError(
                message=f"Failed to update governance state: {str(e)}",
                details={
                    "doc_id": doc_id,
                    "target_state": target_state.value,
                    "error": str(e),
                },
            ) from e
