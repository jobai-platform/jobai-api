import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class CandidateEmbeddingModel(Base):
    __tablename__ = "candidate_embeddings"
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_candidate_embeddings_candidate_id"),
        Index(
            "idx_candidate_embeddings_vector_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    vector: Mapped[list] = mapped_column(Vector(768), nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobEmbeddingModel(Base):
    __tablename__ = "job_embeddings"
    __table_args__ = (
        UniqueConstraint("job_posting_id", name="uq_job_embeddings_job_posting_id"),
        Index(
            "idx_job_embeddings_vector_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    vector: Mapped[list] = mapped_column(Vector(768), nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
