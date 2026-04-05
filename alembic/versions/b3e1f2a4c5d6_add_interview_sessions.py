"""add interview sessions

Revision ID: b3e1f2a4c5d6
Revises: d6d79cb46f27
Create Date: 2026-04-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e1f2a4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd6d79cb46f27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old interviews table (had scheduling fields directly on it)
    op.drop_index('ix_interviews_application_id', table_name='interviews')
    op.drop_table('interviews')

    # 2. Create interview_sessions table
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.String(length=2000), nullable=True),
        sa.Column('result', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interview_sessions_job_id', 'interview_sessions', ['job_id'], unique=False)

    # 3. Create new interviews table (candidate slots linked to a session)
    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id']),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'application_id', name='uq_interview_session_application'),
    )
    op.create_index('ix_interviews_session_id', 'interviews', ['session_id'], unique=False)
    op.create_index('ix_interviews_application_id', 'interviews', ['application_id'], unique=False)


def downgrade() -> None:
    # 1. Drop new interviews table
    op.drop_index('ix_interviews_application_id', table_name='interviews')
    op.drop_index('ix_interviews_session_id', table_name='interviews')
    op.drop_table('interviews')

    # 2. Drop interview_sessions table
    op.drop_index('ix_interview_sessions_job_id', table_name='interview_sessions')
    op.drop_table('interview_sessions')

    # 3. Restore old interviews table
    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        sa.Column('result', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interviews_application_id', 'interviews', ['application_id'], unique=False)
