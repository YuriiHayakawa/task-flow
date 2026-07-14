import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAtMixin
from app.enums.notification_type import NotificationType


class Notification(Base, CreatedAtMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_recipient_id_is_read_created_at",
            "recipient_id",
            "is_read",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
