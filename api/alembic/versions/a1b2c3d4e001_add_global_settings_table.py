"""add global_settings table

Revision ID: a1b2c3d4e001
Revises: fefdd1835b7d
Create Date: 2026-08-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e001'
down_revision = 'fefdd1835b7d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'global_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_global_settings_key', 'global_settings', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_global_settings_key', table_name='global_settings')
    op.drop_table('global_settings')
