"""add search_agents table

Revision ID: 568ce812c1e5
Revises: 9cf37244a7c6
Create Date: 2026-05-06 20:43:58.002623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '568ce812c1e5'
down_revision: Union[str, Sequence[str], None] = '9cf37244a7c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'search_agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('keywords', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('remote_only', sa.Boolean(), nullable=False),
        sa.Column('date_posted_within_days', sa.Integer(), nullable=False),
        sa.Column('limit', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['public.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public',
    )
    op.create_index('ix_search_agents_candidate_id', 'search_agents', ['candidate_id'], schema='public')

    # Fix foreign keys on candidate_profiles and subscriptions
    op.drop_constraint('candidate_profiles_user_id_fkey', 'candidate_profiles', schema='public', type_='foreignkey')
    op.create_foreign_key(None, 'candidate_profiles', 'users', ['user_id'], ['id'], source_schema='public', referent_schema='public', ondelete='CASCADE')
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_constraint('subscriptions_billing_price_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key(None, 'subscriptions', 'billing_prices', ['billing_price_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')
    op.create_foreign_key(None, 'subscriptions', 'users', ['user_id'], ['id'], source_schema='public', referent_schema='public', ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(None, 'subscriptions', schema='public', type_='foreignkey')
    op.drop_constraint(None, 'subscriptions', schema='public', type_='foreignkey')
    op.create_foreign_key('subscriptions_billing_price_id_fkey', 'subscriptions', 'billing_prices', ['billing_price_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('subscriptions_user_id_fkey', 'subscriptions', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'candidate_profiles', schema='public', type_='foreignkey')
    op.create_foreign_key('candidate_profiles_user_id_fkey', 'candidate_profiles', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_index('ix_search_agents_candidate_id', table_name='search_agents', schema='public')
    op.drop_table('search_agents', schema='public')
