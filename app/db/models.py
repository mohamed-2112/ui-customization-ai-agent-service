import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    page: Mapped[str] = mapped_column(String(100), index=True)

    model_provider: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(100), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)

    message_length: Mapped[int] = mapped_column(Integer)
    validation_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    drafts: Mapped[list["UITemplateDraftModel"]] = relationship(
        back_populates="agent_run",
        cascade="all, delete-orphan",
    )


class UITemplateDraftModel(Base):
    __tablename__ = "ui_template_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    page: Mapped[str] = mapped_column(String(100), index=True)

    status: Mapped[str] = mapped_column(String(100), index=True)

    template_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    agent_run: Mapped[AgentRunModel] = relationship(back_populates="drafts")
    
    
    
    
class UITemplateVersionModel(Base):
    __tablename__ = "ui_template_versions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "page",
            "version",
            name="uq_ui_template_user_page_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ui_template_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    page: Mapped[str] = mapped_column(String(100), index=True)

    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(100), index=True)

    template_json: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )