"""recurring_tasks

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.enums.recurrence_type import RecurrenceType


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recurring_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "recurrence_type",
            sa.Enum(
                RecurrenceType,
                name="recurrence_type",
                native_enum=False,
                validate_strings=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("month_day", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0", name="ck_recurring_tasks_title_not_blank"
        ),
        sa.CheckConstraint(
            "month_day IS NULL OR month_day BETWEEN 1 AND 31",
            name="ck_recurring_tasks_month_day_range",
        ),
    )
    op.create_index("ix_recurring_tasks_owner_id", "recurring_tasks", ["owner_id"])

    op.create_table(
        "recurring_task_weekdays",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "recurring_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recurring_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_recurring_task_weekdays_range"),
        sa.UniqueConstraint(
            "recurring_task_id", "weekday", name="uq_recurring_task_weekdays_task_weekday"
        ),
    )

    op.create_table(
        "recurring_task_completions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "recurring_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recurring_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "recurring_task_id",
            "occurrence_date",
            name="uq_recurring_task_completions_task_date",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("recurring_task_completions")
    op.drop_table("recurring_task_weekdays")
    op.drop_index("ix_recurring_tasks_owner_id", table_name="recurring_tasks")
    op.drop_table("recurring_tasks")
