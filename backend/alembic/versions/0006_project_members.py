"""project_members

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    # FR-012 (spec.md) / research.md #4: migração de dados dos projetos já
    # existentes — todo membro atual do workspace de um projeto vira membro
    # explícito desse projeto, num único evento, para que ninguém perca
    # acesso com a introdução desta restrição. Evento único (não um
    # processo contínuo) — projetos criados depois desta migração começam
    # sem herdar automaticamente o restante do workspace (FR-003 cobre
    # esses via `ProjectService.create`).
    op.execute(
        "INSERT INTO project_members (id, project_id, user_id, created_at) "
        "SELECT gen_random_uuid(), p.id, wm.user_id, now() "
        "FROM projects p "
        "JOIN workspace_members wm ON wm.workspace_id = p.workspace_id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_table("project_members")
