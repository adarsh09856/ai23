"""add billing tables

Revision ID: a1b2c3d4e003
Revises: a1b2c3d4e002
Create Date: 2026-08-13 16:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e003'
down_revision = 'a1b2c3d4e002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credit_packages table
    op.create_table(
        'credit_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('price_usd', sa.Float(), nullable=False),
        sa.Column('badge', sa.String(length=50), nullable=True),
        sa.Column('features_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credit_packages_enabled', 'credit_packages', ['enabled'], unique=False)
    op.create_index('ix_credit_packages_display_order', 'credit_packages', ['display_order'], unique=False)

    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('max_workflows', sa.Integer(), nullable=True),
        sa.Column('max_phone_numbers', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_calls', sa.Integer(), nullable=True),
        sa.Column('included_credits_monthly', sa.Integer(), nullable=False),
        sa.Column('allow_custom_models', sa.Boolean(), nullable=False),
        sa.Column('support_tier', sa.String(length=50), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_plans_key', 'plans', ['key'], unique=True)
    op.create_index('ix_plans_enabled', 'plans', ['enabled'], unique=False)
    op.create_index('ix_plans_display_order', 'plans', ['display_order'], unique=False)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('credits_delta', sa.Integer(), nullable=False),
        sa.Column('currency_amount_usd', sa.Float(), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'], unique=False)
    op.create_index('ix_transactions_org_id', 'transactions', ['org_id'], unique=False)
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'], unique=False, postgresql_using='btree')
    op.create_index('ix_transactions_type', 'transactions', ['type'], unique=False)
    op.create_index('ix_transactions_reference', 'transactions', ['reference_type', 'reference_id'], unique=False)

    # Seed default plans
    op.execute("""
        INSERT INTO plans (key, display_name, max_workflows, max_phone_numbers, max_concurrent_calls, 
                          included_credits_monthly, allow_custom_models, support_tier, enabled, display_order)
        VALUES 
            ('free', 'Free', 3, 1, 1, 100, false, 'none', true, 1),
            ('pro', 'Pro', 25, 5, 5, 1000, true, 'standard', true, 2),
            ('enterprise', 'Enterprise', null, null, null, 5000, true, 'priority', true, 3)
    """)


def downgrade() -> None:
    # Drop transactions table
    op.drop_index('ix_transactions_reference', table_name='transactions')
    op.drop_index('ix_transactions_type', table_name='transactions')
    op.drop_index('ix_transactions_created_at', table_name='transactions')
    op.drop_index('ix_transactions_org_id', table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_table('transactions')

    # Drop plans table
    op.drop_index('ix_plans_display_order', table_name='plans')
    op.drop_index('ix_plans_enabled', table_name='plans')
    op.drop_index('ix_plans_key', table_name='plans')
    op.drop_table('plans')

    # Drop credit_packages table
    op.drop_index('ix_credit_packages_display_order', table_name='credit_packages')
    op.drop_index('ix_credit_packages_enabled', table_name='credit_packages')
    op.drop_table('credit_packages')
