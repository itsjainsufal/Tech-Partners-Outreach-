from __future__ import annotations

import os
import pathlib
import re
import smtplib
import ssl
import sys
import time
from email.mime.text import MIMEText

from .queue import APPROVED, SENT, list_queue, move_draft, parse_frontmatter

DEFAULT_RATE_LIMIT_PER_MIN = 10
_parse_frontmatter = parse_frontmatter


def _extract_section(md_text: str, header: str) -> str:
    pattern = rf"^# {re.escape(header)}\s*\n(.*?)(?=\n#\s|\n---\s|\Z)"
    match = re.search(pattern, md_text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def send_one(path: pathlib.Path, *, dry_run: bool = False) -> tuple[bool, str]:
    md = path.read_text()
    fm = parse_frontmatter(md)
    to_email = fm.get("partner_email", "").strip()
    if not to_email:
        return False, "missing partner_email in frontmatter"

    subject = fm.get("subject", "").strip() or _extract_section(md, "Subject")
    body = _extract_section(md, "Body")
    if not subject or not body:
        return False, "missing subject or body section"

    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM") or smtp_user
    if not smtp_host or not smtp_user or not smtp_pass or not from_addr:
        return False, "missing SMTP env vars (SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM)"

    if dry_run or os.getenv("SENDER_DRY_RUN") == "1":
        return True, f"dry-run OK (would send to {to_email})"

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_email

    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as smtp:
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(message)
    except Exception as exc:
        return False, f"SMTP error: {exc}"

    return True, "sent"


def send_approved_queue(*, dry_run: bool = False, rate_limit_per_min: int | None = None, sleep_fn=time.sleep) -> dict[str, list]:
    if rate_limit_per_min is None:
        rate_limit_per_min = int(os.getenv("SENDER_RATE_LIMIT_PER_MIN", str(DEFAULT_RATE_LIMIT_PER_MIN)))
    sleep_seconds = 60.0 / rate_limit_per_min if rate_limit_per_min > 0 else 0.0

    summary: dict[str, list] = {"sent": [], "failed": [], "skipped": []}
    paths = list_queue(status=APPROVED)
    if not paths:
        return summary

    for index, path in enumerate(paths):
        ok, reason = send_one(path, dry_run=dry_run)
        if ok:
            try:
                new_path = move_draft(path, to_status=SENT)
            except Exception:
                summary["sent"].append(str(path))
                print(f"⚠ sent but couldn't move {path.name}: {reason}", file=sys.stderr)
                continue
            summary["sent"].append(str(new_path))
            print(f"✓ sent {path.name} → {new_path.name}", file=sys.stderr)
            if sleep_seconds > 0 and index < len(paths) - 1 and not dry_run:
                sleep_fn(sleep_seconds)
        else:
            summary["failed"].append((str(path), reason))
            print(f"✗ {path.name}: {reason}", file=sys.stderr)
    return summary
