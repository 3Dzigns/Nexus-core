"""Add feedback_score to chunks for feedback-based ranking adjustments.

Reference:
- REQUIREMENTS_v1.0.md FR-038
- DATABASE_SCHEMA_v1.0.md Section 3.2 (chunks)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add feedback_score column to chunks."""
    op.add_column(
        "chunks",
        sa.Column("feedback_score", sa.Float(), nullable=False, server_default="0.0"),
    )


def downgrade() -> None:
    """Remove feedback_score column from chunks."""
    op.drop_column("chunks", "feedback_score")
