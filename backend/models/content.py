"""Persisted content-pipeline records."""

from datetime import datetime

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ContentItem(Base):
    __tablename__ = "content_items"

    content_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_name: Mapped[str] = mapped_column(String(240), default="")
    content_pillar: Mapped[str] = mapped_column(String(120), default="")
    target_audience: Mapped[str] = mapped_column(String(240), default="")
    caption: Mapped[str] = mapped_column(String, default="")
    script: Mapped[str] = mapped_column(String, default="")
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list)
    creative_assets: Mapped[list[str]] = mapped_column(JSON, default=list)
    approval_status: Mapped[str] = mapped_column(String(24), default="draft")
    scheduled_publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_url: Mapped[str | None] = mapped_column(String, nullable=True)
    performance_metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    content_format: Mapped[str] = mapped_column(String(24), default="post")
    agent_activity: Mapped[list[str]] = mapped_column(JSON, default=list)
    approval_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    feedback_for_next_cycle: Mapped[list[str]] = mapped_column(JSON, default=list)

    def to_pipeline(self):
        from orchestrator.schema import ContentPipeline

        return ContentPipeline.model_validate(
            {column.name: getattr(self, column.name) for column in self.__table__.columns}
        )

    @classmethod
    def from_pipeline(cls, content):
        return cls(**content.model_dump())
