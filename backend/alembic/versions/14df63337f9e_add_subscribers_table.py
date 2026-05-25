"""add subscribers table

Revision ID: 14df63337f9e
Revises: 35ad2e474df6
Create Date: 2026-05-24

Adds the `subscribers` table used by scripts/daily_digest.py to fan out the
6:30 AM Pacific email. Email uniqueness is enforced case-insensitively via a
functional index on lower(email).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "14df63337f9e"
down_revision: Union[str, Sequence[str], None] = "35ad2e474df6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscribers",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "unsubscribed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Case-insensitive unique on email — uses a functional index on lower(email)
    # since SQLAlchemy's UniqueConstraint can't express it portably.
    op.execute(
        "CREATE UNIQUE INDEX uq_subscribers_email_lower "
        "ON subscribers (lower(email))"
    )
    op.create_index(
        "ix_subscribers_active",
        "subscribers",
        ["unsubscribed_at"],
        postgresql_where=sa.text("unsubscribed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_subscribers_active", table_name="subscribers")
    op.execute("DROP INDEX IF EXISTS uq_subscribers_email_lower")
    op.drop_table("subscribers")
