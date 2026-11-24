"""Add reservation leases and concurrency safeguards

Revision ID: 34b8ae662833
Revises: aa52e888c946
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "34b8ae662833"
down_revision: Union[str, Sequence[str], None] = "aa52e888c946"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Agent reservation fields
    op.add_column(
        "agents",
        sa.Column("reservation_token", sa.Uuid(), nullable=True)
    )

    op.add_column(
        "agents",
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_unique_constraint(
        "uq_agent_reservation_token",
        "agents",
        ["reservation_token"]
    )

    op.create_check_constraint(
        "ck_agent_reservation_fields",
        "agents",
        """
        (reservation_token IS NULL AND reserved_until IS NULL)
        OR
        (reservation_token IS NOT NULL AND reserved_until IS NOT NULL)
        """
    )

    # Borrower reservation fields
    op.add_column(
        "borrowers",
        sa.Column("reservation_token", sa.Uuid(), nullable=True)
    )

    op.add_column(
        "borrowers",
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_unique_constraint(
        "uq_borrower_reservation_token",
        "borrowers",
        ["reservation_token"]
    )

    op.create_check_constraint(
        "ck_borrower_reservation_fields",
        "borrowers",
        """
        (reservation_token IS NULL AND reserved_until IS NULL)
        OR
        (reservation_token IS NOT NULL AND reserved_until IS NOT NULL)
        """
    )

    # Call validation
    op.create_check_constraint(
        "ck_call_attempt_number",
        "calls",
        "attempt_number > 0"
    )

    # Only one active call per agent
    op.create_index(
        "uq_calls_active_agent",
        "calls",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text(
            """
            agent_id IS NOT NULL
            AND status IN (
                'RESERVED',
                'INITIATED',
                'RINGING',
                'ANSWERED',
                'CONNECTED'
            )
            """
        )
    )

    # Only one active call per borrower
    op.create_index(
        "uq_calls_active_borrower",
        "calls",
        ["borrower_id"],
        unique=True,
        postgresql_where=sa.text(
            """
            status IN (
                'RESERVED',
                'INITIATED',
                'RINGING',
                'ANSWERED',
                'CONNECTED'
            )
            """
        )
    )


def downgrade() -> None:

    op.drop_index(
        "uq_calls_active_borrower",
        table_name="calls"
    )

    op.drop_index(
        "uq_calls_active_agent",
        table_name="calls"
    )

    op.drop_constraint(
        "ck_call_attempt_number",
        "calls",
        type_="check"
    )

    op.drop_constraint(
        "ck_borrower_reservation_fields",
        "borrowers",
        type_="check"
    )

    op.drop_constraint(
        "uq_borrower_reservation_token",
        "borrowers",
        type_="unique"
    )

    op.drop_column("borrowers", "reserved_until")
    op.drop_column("borrowers", "reservation_token")

    op.drop_constraint(
        "ck_agent_reservation_fields",
        "agents",
        type_="check"
    )

    op.drop_constraint(
        "uq_agent_reservation_token",
        "agents",
        type_="unique"
    )

    op.drop_column("agents", "reserved_until")
    op.drop_column("agents", "reservation_token")