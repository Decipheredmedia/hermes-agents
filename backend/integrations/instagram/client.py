"""Mock-only Meta/Instagram adapter."""

from datetime import UTC, datetime, timedelta


class InstagramNotConfiguredError(RuntimeError):
    """Raised when a caller requests a live integration that Stage 1 does not provide."""


class MockInstagramClient:
    """Return deterministic fake results; this class makes no network requests."""

    def schedule(self, content):
        if content.approval_status != "approved":
            raise ValueError("Human approval is required before scheduling")
        return {
            "mock": True,
            "schedule_id": f"mock-{content.content_id}",
            "scheduled_publish_date": content.scheduled_publish_date
            or datetime.now(UTC) + timedelta(minutes=5),
        }

    def read_messages(self):
        raise InstagramNotConfiguredError(
            "Reading Instagram messages requires Meta App review and an authorized Business account"
        )

    def send_message(self, *_args, **_kwargs):
        raise InstagramNotConfiguredError(
            "Sending Instagram messages is not implemented; human approval and supported Meta permissions are required"
        )

    def publish(self, *_args, **_kwargs):
        raise InstagramNotConfiguredError(
            "Live publishing is not implemented; Meta App review and an authorized Business account are required"
        )


def retry_after_seconds(response_headers: dict[str, str]) -> int | None:
    """Rate-limit integration seam; a real client must honor Meta's response headers."""
    value = response_headers.get("Retry-After")
    return int(value) if value and value.isdigit() else None
