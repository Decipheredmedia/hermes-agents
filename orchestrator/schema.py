"""Shared typed data contract for Instagram content handoffs."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class ContentPipeline(BaseModel):
    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    content_id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_name: str = ""
    content_pillar: str = ""
    target_audience: str = ""
    caption: str = ""
    script: str = ""
    hashtags: list[str] = Field(default_factory=list)
    creative_assets: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    scheduled_publish_date: datetime | None = None
    published_url: str | None = None
    performance_metrics: dict[str, float] = Field(default_factory=dict)
    content_format: str = "post"
    agent_activity: list[str] = Field(default_factory=list)
    approval_by: str | None = None
    feedback_for_next_cycle: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    approved: bool
    approved_by: str = Field(min_length=1, max_length=120)


class PipelineRequest(BaseModel):
    campaign_name: str = "New campaign"
    content_pillar: str = "Education"
    target_audience: str = "Audience not configured"
    idea: str = "Share one useful idea with the audience"
    content_format: str = "post"
    brand_voice: str = ""
