"""add moderation tables

Revision ID: a1b2c3d4e002
Revises: a1b2c3d4e001
Create Date: 2026-08-13 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e002'
down_revision = 'a1b2c3d4e001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('summary_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_admin_user_id', 'admin_audit_logs', ['admin_user_id'], unique=False)
    op.create_index('ix_audit_created_at', 'admin_audit_logs', ['created_at'], unique=False, postgresql_using='btree')
    op.create_index('ix_audit_target_type_id', 'admin_audit_logs', ['target_type', 'target_id'], unique=False)
    op.create_index('ix_audit_action_type', 'admin_audit_logs', ['action_type'], unique=False)

    # Create banned_words table
    op.create_table(
        'banned_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phrase', sa.String(length=200), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_banned_words_enabled', 'banned_words', ['enabled'], unique=False)
    op.create_index('ix_banned_words_phrase', 'banned_words', ['phrase'], unique=False)
    op.create_index('ix_banned_words_severity', 'banned_words', ['severity'], unique=False)

    # Create violations table
    op.create_table(
        'violations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('call_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('detected_phrase', sa.String(length=200), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_taken', sa.String(length=100), nullable=True),
        sa.Column('notes_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['workflow_runs.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_violations_status', 'violations', ['status'], unique=False)
    op.create_index('ix_violations_call_id', 'violations', ['call_id'], unique=False)
    op.create_index('ix_violations_user_id', 'violations', ['user_id'], unique=False)
    op.create_index('ix_violations_created_at', 'violations', ['created_at'], unique=False, postgresql_using='btree')
    op.create_index('ix_violations_severity', 'violations', ['severity'], unique=False)


def downgrade() -> None:
    # Drop violations table
    op.drop_index('ix_violations_severity', table_name='violations')
    op.drop_index('ix_violations_created_at', table_name='violations')
    op.drop_index('ix_violations_user_id', table_name='violations')
    op.drop_index('ix_violations_call_id', table_name='violations')
    op.drop_index('ix_violations_status', table_name='violations')
    op.drop_table('violations')

    # Drop banned_words table
    op.drop_index('ix_banned_words_severity', table_name='banned_words')
    op.drop_index('ix_banned_words_phrase', table_name='banned_words')
    op.drop_index('ix_banned_words_enabled', table_name='banned_words')
    op.drop_table('banned_words')

    # Drop admin_audit_logs table
    op.drop_index('ix_audit_action_type', table_name='admin_audit_logs')
    op.drop_index('ix_audit_target_type_id', table_name='admin_audit_logs')
    op.drop_index('ix_audit_created_at', table_name='admin_audit_logs')
    op.drop_index('ix_audit_admin_user_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
