from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tech_partners_outreach.sender import _extract_section, _parse_frontmatter, send_approved_queue, send_one


@pytest.fixture(autouse=True)
def _redirect_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_PARTNERS_QUEUE", str(tmp_path / "queue"))


def _approved_draft(tmp_path, *, body="Hi, let's partner.", partner_email="partner@example.com", subject="Hi"):
    approved_dir = tmp_path / "queue" / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    path = approved_dir / "20260815T100000Z-connectflow-to-partner.md"
    path.write_text(
        f"""---
project: connectflow
partner_name: Partner
partner_email: {partner_email}
subject: {subject}
status: approved
drafted_at: 2026-08-15T10:00:00Z
---

# Subject
{subject}

# Body
{body}

---
"""
    )
    return path


def test_parse_frontmatter_returns_dict():
    assert _parse_frontmatter("---\nfoo: bar\n---\nbody") == {"foo": "bar"}


def test_extract_section_returns_body():
    md = "# Subject\nHello\n\n# Body\nWorld\n"
    assert _extract_section(md, "Subject") == "Hello"
    assert _extract_section(md, "Body") == "World"


def test_send_one_missing_smtp_env(tmp_path, monkeypatch):
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.delenv(key, raising=False)
    ok, reason = send_one(_approved_draft(tmp_path))
    assert ok is False
    assert "SMTP env vars" in reason


def test_send_one_dry_run_skips_smtp(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "me@example.com")
    with patch("smtplib.SMTP") as smtp:
        ok, reason = send_one(_approved_draft(tmp_path), dry_run=True)
    assert ok is True
    assert "dry-run OK" in reason
    smtp.assert_not_called()


def test_send_one_smtp_success(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "me@example.com")
    fake_smtp = MagicMock()
    fake_smtp.__enter__ = MagicMock(return_value=fake_smtp)
    fake_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP", return_value=fake_smtp):
        ok, reason = send_one(_approved_draft(tmp_path))
    assert ok is True
    assert reason == "sent"
    fake_smtp.starttls.assert_called_once()
    fake_smtp.login.assert_called_once_with("me@example.com", "secret")
    fake_smtp.send_message.assert_called_once()


def test_send_approved_queue_dry_run_moves_files(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "me@example.com")
    path = _approved_draft(tmp_path)
    summary = send_approved_queue(dry_run=True)
    assert len(summary["sent"]) == 1
    assert not path.exists()
    assert any((tmp_path / "queue" / "sent").glob("*.md"))
