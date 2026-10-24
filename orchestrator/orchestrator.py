"""Deterministic Stage 1 agent pipeline with a required human approval state."""

from datetime import UTC, datetime, timedelta
from collections.abc import Callable

from orchestrator.schema import ApprovalStatus, ContentPipeline, PipelineRequest

MAIN_PIPELINE = (
    "trend-watcher",
    "content-planner",
    "hook-extractor",
    "virality-engine",
    "post-writer/reel-scripter",
    "grid-planner",
)


def run_pipeline(
    request: PipelineRequest, text_generator: Callable[[str], str] | None = None
) -> ContentPipeline:
    """Create one review-ready draft, optionally using configured local inference."""
    is_reel = request.content_format.lower() == "reel"
    hook = f"A practical idea for {request.target_audience}:"
    caption = f"{hook} {request.idea}\n\nWhat would you add?"
    script = (
        f"Opening: {hook}\n"
        f"Scene 1: Introduce the idea: {request.idea}\n"
        "Scene 2: Show one example and explain the takeaway.\n"
        "Close: Invite viewers to share their experience."
        if is_reel
        else ""
    )
    if text_generator:
        tone = request.brand_voice or "clear, natural, and helpful"
        caption = text_generator(
            "Write one original Instagram caption draft only. Be accurate, avoid "
            "unsupported claims, and use this tone. No hashtags unless they are "
            "clearly relevant.\n"
            f"Tone: {tone}\nAudience: {request.target_audience}\n"
            f"Pillar: {request.content_pillar}\nIdea: {request.idea}"
        ).strip()
        if is_reel:
            script = text_generator(
                "Write a concise scene-by-scene Instagram Reel script with voiceover, "
                "visuals, and on-screen text. Do not invent facts.\n"
                f"Tone: {tone}\nAudience: {request.target_audience}\nIdea: {request.idea}"
            ).strip()
    activity = [*MAIN_PIPELINE, "awaiting-human-approval"]
    return ContentPipeline(
        campaign_name=request.campaign_name,
        content_pillar=request.content_pillar,
        target_audience=request.target_audience,
        caption=caption,
        script=script,
        hashtags=[],
        creative_assets=[],
        approval_status=ApprovalStatus.PENDING,
        scheduled_publish_date=datetime.now(UTC) + timedelta(days=1),
        content_format="reel" if is_reel else "post",
        agent_activity=activity,
    )


def record_approval(
    content: ContentPipeline, *, approved: bool, approved_by: str
) -> ContentPipeline:
    """Apply a human decision to a draft that is awaiting review."""
    if content.approval_status != ApprovalStatus.PENDING:
        raise ValueError("Only pending drafts can receive an approval decision")
    reviewer = approved_by.strip()
    if not reviewer:
        raise ValueError("A human reviewer name is required")
    content.approval_status = (
        ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
    )
    content.approval_by = reviewer
    return content


def schedule_after_approval(
    content: ContentPipeline, scheduler
) -> ContentPipeline:
    """Run the mock scheduler only after the explicit approval state is set."""
    if content.approval_status != ApprovalStatus.APPROVED:
        raise ValueError("Human approval is required before scheduling")
    result = scheduler.schedule(content)
    content.approval_status = ApprovalStatus.SCHEDULED
    content.scheduled_publish_date = result["scheduled_publish_date"]
    content.agent_activity.append("mock-scheduler")
    content.agent_activity.append("engagement-loop-next-cycle")
    content.feedback_for_next_cycle.append(
        "Use only verified or owner-supplied performance and audience feedback in the next plan."
    )
    return content
