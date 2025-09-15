"""remove_competitor_set_tables

Revision ID: bda912b2771b
Revises: c12157e470b5
Create Date: 2025-09-15 15:57:39.326054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bda912b2771b'
down_revision: Union[str, None] = 'c12157e470b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop CompetitorSet related tables.

    These tables were implemented but not exposed via API endpoints:
    - competitor_analysis_snapshots
    - competitor_relationships
    - competitor_sets
    """
    # Drop in dependency order (child tables first)
    op.drop_table('competitor_analysis_snapshots')
    op.drop_table('competitor_relationships')
    op.drop_table('competitor_sets')


def downgrade() -> None:
    """Recreate CompetitorSet related tables."""
    # Recreate competitor_sets table
    op.create_table('competitor_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('main_product_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ARCHIVED', name='competitorsetstatus'), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('analysis_frequency', sa.Enum('HOURLY', 'EVERY_6_HOURS', 'DAILY', 'WEEKLY', 'MONTHLY', name='trackingfrequency'), nullable=False),
        sa.Column('auto_update_competitors', sa.Boolean(), nullable=False),
        sa.Column('max_competitors', sa.Integer(), nullable=False),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('last_analysis_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_analysis_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['main_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'main_product_id', 'name', name='uq_competitor_set_tenant_product_name')
    )

    # Recreate competitor_relationships table
    op.create_table('competitor_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competitor_set_id', sa.Integer(), nullable=False),
        sa.Column('competitor_product_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.Enum('DIRECT', 'SUBSTITUTE', 'COMPLEMENTARY', 'CATEGORY', name='competitorrelationshiptype'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('auto_discovered', sa.Boolean(), nullable=False),
        sa.Column('manually_added', sa.Boolean(), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('competitive_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('last_compared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('added_by_url', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['competitor_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['competitor_set_id'], ['competitor_sets.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competitor_set_id', 'competitor_product_id', name='uq_competitor_relationship_set_product')
    )

    # Recreate competitor_analysis_snapshots table
    op.create_table('competitor_analysis_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.String(length=100), nullable=False),
        sa.Column('competitor_set_id', sa.Integer(), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('insights', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('market_position', sa.String(length=50), nullable=True),
        sa.Column('competitive_matrix', sa.JSON(), nullable=True),
        sa.Column('ai_report', sa.JSON(), nullable=True),
        sa.Column('optimization_suggestions', sa.JSON(), nullable=True),
        sa.Column('analysis_metadata', sa.JSON(), nullable=True),
        sa.Column('competitor_count', sa.Integer(), nullable=False),
        sa.Column('analysis_duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['competitor_set_id'], ['competitor_sets.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
