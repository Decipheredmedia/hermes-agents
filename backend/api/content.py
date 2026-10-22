"""Content, approval, calendar, and analytics endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.integrations.instagram.client import MockInstagramClient
from backend.ollama_client import OllamaClient, OllamaError
from backend.models.content import ContentItem
from orchestrator.orchestrator import (
    record_approval,
    run_pipeline,
    schedule_after_approval,
)
from orchestrator.schema import ApprovalRequest, ContentPipeline, PipelineRequest

router = APIRouter(prefix="/api", tags=["content"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_content(content_id: str, db: Session) -> ContentItem:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content item not found")
    return item


@router.post("/pipeline/run", response_model=ContentPipeline, status_code=201)
def create_pipeline(request: PipelineRequest, db: Session = Depends(get_db)):
    inference = OllamaClient()
    generator = inference.generate if inference.host and inference.model else None
    if not request.brand_voice:
        request = request.model_copy(
            update={"brand_voice": os.getenv("BRAND_VOICE", "")}
        )
    try:
        content = run_pipeline(request, text_generator=generator)
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    item = ContentItem.from_pipeline(content)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item.to_pipeline()


@router.get("/content", response_model=list[ContentPipeline])
def list_content(db: Session = Depends(get_db)):
    return [item.to_pipeline() for item in db.scalars(select(ContentItem)).all()]


@router.get("/content/{content_id}", response_model=ContentPipeline)
def get_content(content_id: str, db: Session = Depends(get_db)):
    return _get_content(content_id, db).to_pipeline()


@router.post("/content/{content_id}/approval", response_model=ContentPipeline)
def approve_content(
    content_id: str,
    decision: ApprovalRequest,
    db: Session = Depends(get_db),
):
    item = _get_content(content_id, db)
    try:
        content = record_approval(
            item.to_pipeline(),
            approved=decision.approved,
            approved_by=decision.approved_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    item.approval_status = content.approval_status
    item.approval_by = content.approval_by
    db.commit()
    db.refresh(item)
    return item.to_pipeline()


@router.post("/content/{content_id}/schedule", response_model=ContentPipeline)
def schedule_content(content_id: str, db: Session = Depends(get_db)):
    item = _get_content(content_id, db)
    try:
        content = schedule_after_approval(item.to_pipeline(), MockInstagramClient())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    item.approval_status = content.approval_status
    item.scheduled_publish_date = content.scheduled_publish_date
    item.agent_activity = content.agent_activity
    db.commit()
    db.refresh(item)
    return item.to_pipeline()


@router.get("/calendar", response_model=list[ContentPipeline])
def get_calendar(db: Session = Depends(get_db)):
    items = db.scalars(
        select(ContentItem).order_by(ContentItem.scheduled_publish_date)
    ).all()
    return [item.to_pipeline() for item in items]


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    items = db.scalars(select(ContentItem)).all()
    return {
        "data_origin": "mocked_or_owner_supplied",
        "content_items": len(items),
        "approval_counts": {
            status: sum(item.approval_status == status for item in items)
            for status in ("pending", "approved", "rejected", "scheduled", "published")
        },
        "performance_metrics": {
            key: sum(item.performance_metrics.get(key, 0.0) for item in items)
            for key in ("reach", "views", "saves", "shares", "profile_visits")
        },
    }


@router.get("/activity")
def get_activity(db: Session = Depends(get_db)):
    items = db.scalars(select(ContentItem)).all()
    return [
        {"content_id": item.content_id, "events": item.agent_activity}
        for item in items
    ]
