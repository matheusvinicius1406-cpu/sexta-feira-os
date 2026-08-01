"""teia automation platform (workflows, executions, node runs)

Revision ID: a1c7d2f4b8e0
Revises: 5a60d68e75fa
Create Date: 2026-08-01 09:40:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c7d2f4b8e0'
down_revision: str | Sequence[str] | None = '5a60d68e75fa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'automation_workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['owner.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'slug', name='uq_automation_workflows_owner_slug'),
    )
    with op.batch_alter_table('automation_workflows', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_automation_workflows_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_workflows_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_workflows_last_run_at'), ['last_run_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_workflows_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_workflows_slug'), ['slug'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_workflows_source'), ['source'], unique=False)

    op.create_table(
        'automation_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('workflow_slug', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=True),
        sa.Column('trigger_payload', sa.Text(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('nodes_executed', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['owner.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['automation_workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('automation_executions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_automation_executions_correlation_id'), ['correlation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_started_at'), ['started_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_trigger_type'), ['trigger_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_workflow_id'), ['workflow_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_executions_workflow_slug'), ['workflow_slug'], unique=False)

    op.create_table(
        'automation_node_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('execution_id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['automation_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['owner.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('automation_node_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_automation_node_runs_execution_id'), ['execution_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_node_runs_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_node_runs_node_id'), ['node_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_node_runs_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_node_runs_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('automation_node_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_automation_node_runs_status'))
        batch_op.drop_index(batch_op.f('ix_automation_node_runs_owner_id'))
        batch_op.drop_index(batch_op.f('ix_automation_node_runs_node_id'))
        batch_op.drop_index(batch_op.f('ix_automation_node_runs_id'))
        batch_op.drop_index(batch_op.f('ix_automation_node_runs_execution_id'))
    op.drop_table('automation_node_runs')

    with op.batch_alter_table('automation_executions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_automation_executions_workflow_slug'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_workflow_id'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_trigger_type'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_status'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_started_at'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_owner_id'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_id'))
        batch_op.drop_index(batch_op.f('ix_automation_executions_correlation_id'))
    op.drop_table('automation_executions')

    with op.batch_alter_table('automation_workflows', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_automation_workflows_source'))
        batch_op.drop_index(batch_op.f('ix_automation_workflows_slug'))
        batch_op.drop_index(batch_op.f('ix_automation_workflows_owner_id'))
        batch_op.drop_index(batch_op.f('ix_automation_workflows_last_run_at'))
        batch_op.drop_index(batch_op.f('ix_automation_workflows_id'))
        batch_op.drop_index(batch_op.f('ix_automation_workflows_created_at'))
    op.drop_table('automation_workflows')
