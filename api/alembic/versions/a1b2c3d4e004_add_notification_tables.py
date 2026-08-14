"""add notification tables

Revision ID: a1b2c3d4e004
Revises: a1b2c3d4e003
Create Date: 2026-08-13 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e004'
down_revision = 'a1b2c3d4e003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('display_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('dismissible', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'], unique=False, postgresql_using='btree')
    op.create_index('ix_notifications_expires_at', 'notifications', ['expires_at'], unique=False)
    op.create_index('ix_notifications_display_type', 'notifications', ['display_type'], unique=False)

    # Create notification_deliveries table
    op.create_table(
        'notification_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notification_id', 'user_id', name='uq_notification_user')
    )
    op.create_index('ix_notification_deliveries_user_id', 'notification_deliveries', ['user_id'], unique=False)
    op.create_index('ix_notification_deliveries_notification_id', 'notification_deliveries', ['notification_id'], unique=False)

    # Create lead_stages table
    op.create_table(
        'lead_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lead_stages_org_id', 'lead_stages', ['org_id'], unique=False)
    op.create_index('ix_lead_stages_display_order', 'lead_stages', ['display_order'], unique=False)


def downgrade() -> None:
    # Drop lead_stages table
    op.drop_index('ix_lead_stages_display_order', table_name='lead_stages')
    op.drop_index('ix_lead_stages_org_id', table_name='lead_stages')
    op.drop_table('lead_stages')

    # Drop notification_deliveries table
    op.drop_index('ix_notification_deliveries_notification_id', table_name='notification_deliveries')
    op.drop_index('ix_notification_deliveries_user_id', table_name='notification_deliveries')
    op.drop_table('notification_deliveries')

    # Drop notifications table
    op.drop_index('ix_notifications_display_type', table_name='notifications')
    op.drop_index('ix_notifications_expires_at', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_table('notifications')
