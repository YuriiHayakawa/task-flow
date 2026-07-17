import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.enums.workspace_role import WorkspaceRole


class WorkspaceMemberCreate(BaseModel):
    """Corpo de `POST /api/v1/workspaces/{workspace_id}/members` — `role` é
    restrito a `MEMBER` neste endpoint (contracts/workspaces.md); promoção a
    `ADMIN` é uma operação separada (`PATCH .../role`)."""

    user_id: uuid.UUID
    role: WorkspaceRole = WorkspaceRole.MEMBER

    @field_validator("role")
    @classmethod
    def role_must_be_member(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value != WorkspaceRole.MEMBER:
            raise ValueError("Este endpoint só permite adicionar membros com role MEMBER.")
        return value


class WorkspaceMemberRoleUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}/role`
    — `OWNER` não é um valor aceito aqui (FR-019); usar `transfer-ownership`."""

    role: WorkspaceRole

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value == WorkspaceRole.OWNER:
            raise ValueError("Use /transfer-ownership para alterar o Owner.")
        return value


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    role: WorkspaceRole
    joined_at: datetime


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: uuid.UUID
