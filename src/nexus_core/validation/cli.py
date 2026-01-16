"""CLI tool for running validation manually.

Usage:
    python -m nexus_core.validation.cli validate <doc_id>
    python -m nexus_core.validation.cli validate-all

Per INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md:
- Validator can be run manually for testing
- CLI provides immediate feedback on validation status
- Useful for debugging and manual operations
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from nexus_core.config import get_settings
from nexus_core.db.session import get_async_session_context
from nexus_core.models.source import GovernanceStatus, Source
from nexus_core.validation import Validator, ValidationPreconditionError, ValidationError


async def validate_single(doc_id: str) -> int:
    """Validate a single source.

    Args:
        doc_id: Document identifier to validate

    Returns:
        Exit code: 0 for success (PASS), 1 for failure (FAIL), 2 for error
    """
    print(f"Validating source: {doc_id}")
    print("-" * 60)

    settings = get_settings()

    try:
        async with get_async_session_context() as session:
            validator = Validator(session=session, settings=settings)
            result = await validator.validate(doc_id)

        print(f"\nValidation Result: {result.status.value}")
        print(f"Run ID: {result.run_id}")
        print(f"Report: {result.report_path}")
        print()

        # Print check results
        passed_count = sum(1 for check in result.checks if check.passed)
        failed_count = sum(1 for check in result.checks if not check.passed)

        print(f"Checks: {passed_count} passed, {failed_count} failed")
        print()

        for check in result.checks:
            status_symbol = "✓" if check.passed else "✗"
            print(f"  {status_symbol} {check.check_name}: {check.message}")

        print()

        if result.status.value == "PASS":
            print("✅ Validation PASSED - Source certified as INGESTED")
            return 0
        else:
            print("❌ Validation FAILED - Source marked as ERROR")
            return 1

    except ValidationPreconditionError as e:
        print(f"\n❌ Precondition error: {e.message}")
        print(f"   Details: {e.details}")
        return 2

    except ValidationError as e:
        print(f"\n❌ Validation error: {e.message}")
        print(f"   Details: {e.details}")
        return 2

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


async def validate_all() -> int:
    """Validate all sources in INGESTING state.

    Returns:
        Exit code: 0 for all success, 1 if any failed
    """
    print("Validating all sources in INGESTING state...")
    print("-" * 60)

    settings = get_settings()

    try:
        async with get_async_session_context() as session:
            # Find all sources in INGESTING state
            result = await session.execute(
                select(Source).where(Source.status == GovernanceStatus.INGESTING)
            )
            sources = result.scalars().all()

            if not sources:
                print("No sources found in INGESTING state.")
                return 0

            print(f"Found {len(sources)} source(s) to validate\n")

            success_count = 0
            failure_count = 0
            error_count = 0

            for source in sources:
                doc_id = source.doc_id
                print(f"\nValidating: {doc_id}")

                try:
                    validator = Validator(session=session, settings=settings)
                    validation_result = await validator.validate(doc_id)

                    if validation_result.status.value == "PASS":
                        print(f"  ✅ PASS")
                        success_count += 1
                    else:
                        print(f"  ❌ FAIL")
                        failure_count += 1

                except Exception as e:
                    print(f"  ❌ ERROR: {str(e)}")
                    error_count += 1

            print()
            print("-" * 60)
            print(f"Summary:")
            print(f"  ✅ Passed: {success_count}")
            print(f"  ❌ Failed: {failure_count}")
            print(f"  ⚠️  Errors: {error_count}")

            return 0 if (failure_count == 0 and error_count == 0) else 1

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


def main() -> int:
    """CLI entry point.

    Returns:
        Exit code: 0 for success, non-zero for failure
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m nexus_core.validation.cli validate <doc_id>")
        print("  python -m nexus_core.validation.cli validate-all")
        return 2

    command = sys.argv[1]

    if command == "validate":
        if len(sys.argv) < 3:
            print("Error: doc_id argument required")
            print("Usage: python -m nexus_core.validation.cli validate <doc_id>")
            return 2
        doc_id = sys.argv[2]
        return asyncio.run(validate_single(doc_id))

    elif command == "validate-all":
        return asyncio.run(validate_all())

    else:
        print(f"Unknown command: {command}")
        print("Available commands: validate, validate-all")
        return 2


if __name__ == "__main__":
    sys.exit(main())
