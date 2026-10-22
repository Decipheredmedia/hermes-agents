"""Behavior contracts for the Instagram Stage 1 pipeline and mock-only adapter."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.integrations.instagram.client import (
    InstagramNotConfiguredError,
    MockInstagramClient,
)
from backend.ollama_client import OllamaClient
from orchestrator.orchestrator import (
    record_approval,
    run_pipeline,
    schedule_after_approval,
)
from orchestrator.schema import ApprovalStatus, ContentPipeline, PipelineRequest


@pytest.fixture(scope="module")
def api_client():
    with tempfile.TemporaryDirectory(prefix="instagram-agent-test-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'test.sqlite'}"
        previous_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = database_url
        from backend.app.main import app

        with TestClient(app) as client:
            yield client
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def test_pipeline_schema_carries_required_handoff_fields():
    content = ContentPipeline.model_validate(
        {
            "campaign_name": "Launch",
            "content_pillar": "Education",
            "target_audience": "New customers",
            "caption": "A useful draft",
        }
    )

    assert content.content_id
    assert content.model_dump()["approval_status"] == "draft"
    assert content.creative_assets == []
    assert content.performance_metrics == {}


def test_mock_scheduler_rejects_unapproved_content_and_records_mock_schedule():
    content = run_pipeline(PipelineRequest(idea="Explain one practical tip"))
    scheduler = MockInstagramClient()

    with pytest.raises(ValueError, match="Human approval"):
        schedule_after_approval(content, scheduler)

    approved = record_approval(content, approved=True, approved_by="Reviewer")
    scheduled = schedule_after_approval(approved, scheduler)
    assert scheduled.approval_status == ApprovalStatus.SCHEDULED
    assert "engagement-loop-next-cycle" in scheduled.agent_activity


def test_integration_has_no_live_dm_or_publish_path():
    client = MockInstagramClient()

    with pytest.raises(InstagramNotConfiguredError, match="not implemented"):
        client.publish(object())
    with pytest.raises(InstagramNotConfiguredError, match="not implemented"):
        client.send_message("recipient", "message")
    with pytest.raises(InstagramNotConfiguredError, match="Meta App review"):
        client.read_messages()


def test_ollama_configuration_uses_yaml_then_environment(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        "inference:\n  host: http://ollama-from-file:11434\n  model: configured-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_FILE", str(config))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    from_file = OllamaClient()
    assert (from_file.host, from_file.model) == (
        "http://ollama-from-file:11434",
        "configured-model",
    )

    monkeypatch.setenv("OLLAMA_HOST", "http://ollama-from-env:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "environment-model")
    from_env = OllamaClient()
    assert (from_env.host, from_env.model) == (
        "http://ollama-from-env:11434",
        "environment-model",
    )


def test_api_requires_explicit_approval_before_mock_scheduling(api_client):
    response = api_client.post(
        "/api/pipeline/run",
        json={
            "campaign_name": "API test",
            "content_pillar": "Education",
            "target_audience": "Test audience",
            "idea": "A test idea",
        },
    )
    assert response.status_code == 201
    draft = response.json()
    assert draft["approval_status"] == "pending"

    blocked = api_client.post(f"/api/content/{draft['content_id']}/schedule")
    assert blocked.status_code == 409

    approved = api_client.post(
        f"/api/content/{draft['content_id']}/approval",
        json={"approved": True, "approved_by": "Test reviewer"},
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"

    scheduled = api_client.post(f"/api/content/{draft['content_id']}/schedule")
    assert scheduled.status_code == 200
    assert scheduled.json()["approval_status"] == "scheduled"
    assert "engagement-loop-next-cycle" in scheduled.json()["agent_activity"]
    assert api_client.get("/api/analytics").json()["data_origin"] == "mocked_or_owner_supplied"
