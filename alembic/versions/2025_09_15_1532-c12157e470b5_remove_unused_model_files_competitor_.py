"""remove_unused_model_files_competitor_analysis_suggestion

Revision ID: c12157e470b5
Revises: 73ee379373d6
Create Date: 2025-09-15 15:32:53.887062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c12157e470b5'
down_revision: Union[str, None] = '73ee379373d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Note: The following tables (competitor_data, analysis_reports, optimization_suggestions)
    have already been removed from the database in previous migrations. This migration
    documents the removal of their corresponding model files from the codebase.
    No database changes are needed.
    """
    pass


def downgrade() -> None:
    """Downgrade schema.

    Note: This would require recreating the tables and model files.
    Since these were unused tables, downgrade is not implemented.
    """
    pass
