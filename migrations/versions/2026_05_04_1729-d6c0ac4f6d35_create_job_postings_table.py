"""create_job_postings_table

Revision ID: d6c0ac4f6d35
Revises: 7b5a7a039fe1
Create Date: 2026-05-04 17:29:35.472378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6c0ac4f6d35'
down_revision: Union[str, Sequence[str], None] = '7b5a7a039fe1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_postings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('apply_url', sa.String(length=2048), nullable=True),
        sa.Column('company_url', sa.String(length=2048), nullable=True),
        sa.Column('posted_at', sa.Date(), nullable=True),
        sa.Column('is_remote', sa.Boolean(), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=True),
        sa.Column('insights', sa.String(length=255), nullable=True),
        sa.Column('salary_min', sa.Float(), nullable=True),
        sa.Column('salary_max', sa.Float(), nullable=True),
        sa.Column('salary_currency', sa.String(length=10), nullable=True),
        sa.Column('skills_raw', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', 'source', name='uq_job_posting_external_id_source'),
    )
    op.create_index('ix_job_postings_posted_at', 'job_postings', ['posted_at'], unique=False)
    op.create_index('ix_job_postings_source', 'job_postings', ['source'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_job_postings_source', table_name='job_postings')
    op.drop_index('ix_job_postings_posted_at', table_name='job_postings')
    op.drop_table('job_postings')
