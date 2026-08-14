"""add status columns

Revision ID: a1b2c3d4e005
Revises: a1b2c3d4e004
Create Date: 2026-08-13 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e005'
down_revision = 'a1b2c3d4e004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to workflows table
    op.add_column('workflows', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))

    # Add columns to organizations table
    op.add_column('organizations', sa.Column('status', sa.String(length=20), server_default='active', nullable=False))

    # Add columns to users table
    op.add_column('users', sa.Column('status', sa.String(length=20), server_default='active', nullable=False))
    op.add_column('users', sa.Column('plan_type', sa.String(length=50), server_default='free', nullable=False))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_ip', sa.String(length=45), nullable=True))

    # Create indexes for performance
    op.create_index('ix_workflows_is_active', 'workflows', ['is_active'], unique=False)
    op.create_index('ix_organizations_status', 'organizations', ['status'], unique=False)
    op.create_index('ix_users_status', 'users', ['status'], unique=False)
    op.create_index('ix_users_plan_type', 'users', ['plan_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_plan_type', table_name='users')
    op.drop_index('ix_users_status', table_name='users')
    op.drop_index('ix_organizations_status', table_name='organizations')
    op.drop_index('ix_workflows_is_active', table_name='workflows')

    # Remove columns from users table
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'plan_type')
    op.drop_column('users', 'status')

    # Remove columns from organizations table
    op.drop_column('organizations', 'status')

    # Remove columns from workflows table
    op.drop_column('workflows', 'is_active')
