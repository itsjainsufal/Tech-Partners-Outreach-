from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tech_partners_outreach.models import Draft


@pytest.fixture(autouse=True)
def _redirect_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_PARTNERS_QUEUE", str(tmp_path / "queue"))
    import importlib
    from tech_partners_outreach import queue as q

    importlib.reload(q)


def _draft() -> Draft:
    return Draft(
        partner_email="partner@example.com",
        partner_name="Jane Smith",
        project_name="connectflow",
        subject="Tech partnership",
        body="Quick intro.",
        drafted_at=datetime.now(timezone.utc),
        raw_prompt="(prompt)",
        raw_response="(response)",
    )


def test_queue_writes_pending_by_default():
    from tech_partners_outreach import queue as q

    path = q.queue_draft(_draft())
    assert path.exists()
    assert "pending" in str(path)
    text = path.read_text()
    assert "partner_email: partner@example.com" in text
    assert "Quick intro." in text


def test_queue_filename_is_sanitized():
    from tech_partners_outreach import queue as q

    draft = _draft()
    draft.partner_name = "First/Name <weird>"
    draft.project_name = "weird::name"
    path = q.queue_draft(draft)
    assert "/" not in path.name
    assert "<" not in path.name
    assert ":" not in path.name


def test_list_queue_per_status():
    from tech_partners_outreach import queue as q

    q.queue_draft(_draft(), status="approved")
    assert len(q.list_queue(status="approved")) == 1
    assert q.list_queue(status="pending") == []
