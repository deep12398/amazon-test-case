"""recreate_all_tables_with_correct_structure

Revision ID: b69614c7697a
Revises: 52c225defbab
Create Date: 2025-09-13 00:10:35.462389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b69614c7697a'
down_revision: Union[str, None] = '52c225defbab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
