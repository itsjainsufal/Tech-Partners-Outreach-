from __future__ import annotations

import os
import pathlib
import re
import shutil
from datetime import datetime, timezone

from .models import Draft

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
SENT = "sent"
STATUSES = {PENDING, APPROVED, REJECTED, SENT}
DEFAULT_QUEUE_ROOT = pathlib.Path.home() / ".tech-partners-outreach" / "queue"


def queue_root() -> pathlib.Path:
    return pathlib.Path(os.getenv("TECH_PARTNERS_QUEUE", str(DEFAULT_QUEUE_ROOT))).expanduser()


def _status_dir(status: str) -> pathlib.Path:
    if status not in STATUSES:
        raise ValueError(f"unsupported status: {status}")
    path = queue_root() / status
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-._")
    return cleaned or "x"


def _timestamp(dt: datetime | None) -> str:
    actual = dt or datetime.now(timezone.utc)
    if actual.tzinfo is None:
        actual = actual.replace(tzinfo=timezone.utc)
    return actual.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _render_markdown(draft: Draft, status: str) -> str:
    drafted_at = draft.drafted_at.astimezone(timezone.utc).isoformat() if draft.drafted_at else ""
    return f"""---
project: {draft.project_name}
partner_name: {draft.partner_name}
partner_email: {draft.partner_email}
subject: {draft.subject}
status: {status}
drafted_at: {drafted_at}
---

# Subject
{draft.subject}

# Body
{draft.body}

---
<!-- Move this file to queue/approved/ to send, or queue/rejected/ to skip. -->

## Audit
- Prompt sent to LLM:
```
{draft.raw_prompt[:1500]}
```

- Raw LLM response:
```
{draft.raw_response[:1500]}
```
"""


def queue_draft(draft: Draft, *, status: str = PENDING) -> pathlib.Path:
    basename = f"{_timestamp(draft.drafted_at)}-{_slugify(draft.project_name)}-to-{_slugify(draft.partner_name or draft.partner_email.split('@')[0])}.md"
    path = _status_dir(status) / basename
    path.write_text(_render_markdown(draft, status))
    return path


def list_queue(*, status: str = PENDING) -> list[pathlib.Path]:
    return sorted(_status_dir(status).glob("*.md"))


def move_draft(path: pathlib.Path, *, to_status: str) -> pathlib.Path:
    destination = _status_dir(to_status) / path.name
    shutil.move(str(path), str(destination))
    return destination


def parse_frontmatter(md_text: str) -> dict[str, str]:
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out
