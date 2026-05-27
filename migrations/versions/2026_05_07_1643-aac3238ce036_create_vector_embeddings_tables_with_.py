"""create vector embeddings tables with pgvectorscale and ai_analyses

Revision ID: aac3238ce036
Revises: cc9efd2af8eb
Create Date: 2026-05-07 16:43:18.703447

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'aac3238ce036'
down_revision: Union[str, Sequence[str], None] = 'cc9efd2af8eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # --- candidate_embeddings ---
    op.create_table(
        'candidate_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', UUID(as_uuid=True), sa.ForeignKey('public.candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vector', sa.Text(), nullable=False),  # stored as text, cast by pgvector
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('candidate_id', name='uq_candidate_embeddings_candidate_id'),
        schema='public',
    )
    op.execute("""
        ALTER TABLE public.candidate_embeddings
        ALTER COLUMN vector TYPE vector(768) USING vector::vector(768)
    """)
    op.execute("""
        CREATE INDEX idx_candidate_embeddings_vector_hnsw
        ON public.candidate_embeddings
        USING hnsw (vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # --- job_embeddings ---
    op.create_table(
        'job_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('job_posting_id', UUID(as_uuid=True), sa.ForeignKey('public.job_postings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vector', sa.Text(), nullable=False),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('job_posting_id', name='uq_job_embeddings_job_posting_id'),
        schema='public',
    )
    op.execute("""
        ALTER TABLE public.job_embeddings
        ALTER COLUMN vector TYPE vector(768) USING vector::vector(768)
    """)
    op.execute("""
        CREATE INDEX idx_job_embeddings_vector_hnsw
        ON public.job_embeddings
        USING hnsw (vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # --- ai_analyses ---
    op.create_table(
        'ai_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', UUID(as_uuid=True), sa.ForeignKey('public.candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_posting_id', UUID(as_uuid=True), sa.ForeignKey('public.job_postings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('quality_tier', sa.String(20), nullable=False, server_default='balanced'),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('skills_score', sa.Float(), nullable=True),
        sa.Column('experience_score', sa.Float(), nullable=True),
        sa.Column('location_score', sa.Float(), nullable=True),
        sa.Column('salary_score', sa.Float(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('tokens_consumed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('candidate_id', 'job_posting_id', name='uq_ai_analyses_candidate_job'),
        schema='public',
    )
    op.create_index('idx_ai_analyses_candidate_id', 'ai_analyses', ['candidate_id'], schema='public')
    op.create_index('idx_ai_analyses_status', 'ai_analyses', ['status'], schema='public')


def downgrade() -> None:
    op.drop_table('ai_analyses', schema='public')

    op.execute("DROP INDEX IF EXISTS public.idx_job_embeddings_vector_hnsw")
    op.drop_table('job_embeddings', schema='public')

    op.execute("DROP INDEX IF EXISTS public.idx_candidate_embeddings_vector_hnsw")
    op.drop_table('candidate_embeddings', schema='public')

    op.execute("DROP EXTENSION IF EXISTS vector;")
