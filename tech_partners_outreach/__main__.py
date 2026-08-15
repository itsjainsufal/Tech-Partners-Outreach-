from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from .drafter import draft_email
from .models import PartnerProject, TechPartner
from .queue import APPROVED, PENDING, REJECTED, SENT, list_queue, queue_draft
from .sender import send_approved_queue


def _load_project(path: str) -> PartnerProject:
    raw = Path(path).read_text()
    if path.endswith(".json"):
        data = json.loads(raw)
    else:
        data = {}
        current_list_key: str | None = None
        for line in raw.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith("  - "):
                if current_list_key:
                    data.setdefault(current_list_key, []).append(line[4:].strip())
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value
                current_list_key = None
            else:
                data[key] = []
                current_list_key = key
    return PartnerProject(
        name=data.get("name", ""),
        one_liner=data.get("one_liner", ""),
        integration_value=data.get("integration_value", ""),
        traction=data.get("traction", []) if isinstance(data.get("traction"), list) else [data.get("traction", "")],
        ideal_partner_profile=data.get("ideal_partner_profile", ""),
        offer=data.get("offer", ""),
        proof_points=data.get("proof_points", []) if isinstance(data.get("proof_points"), list) else [data.get("proof_points", "")],
        founder_name=data.get("founder_name", ""),
        founder_email=data.get("founder_email", ""),
        website_url=data.get("website_url", ""),
        demo_url=data.get("demo_url", ""),
    )


def _load_partners(path: str) -> list[TechPartner]:
    partners: list[TechPartner] = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("email"):
                continue
            partners.append(
                TechPartner(
                    name=row.get("name", "").strip(),
                    email=row["email"].strip(),
                    company=row.get("company", "").strip(),
                    role=row.get("role", "").strip(),
                    partnership_focus=row.get("partnership_focus", "").strip(),
                    website=row.get("website", "").strip(),
                    linkedin=row.get("linkedin", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return partners


def cmd_draft(args) -> int:
    project = _load_project(args.project)
    partners = _load_partners(args.partners)
    if not partners:
        print(f"⚠ no tech partners loaded from {args.partners}", file=sys.stderr)
        return 1

    print(f"drafting {len(partners)} email(s) for {project.name} → HITL queue", file=sys.stderr)
    last_path = None
    for index, partner in enumerate(partners, 1):
        draft = draft_email(partner, project)
        last_path = queue_draft(draft)
        print(f"  [{index}/{len(partners)}] {partner.name or partner.email} → {last_path.name}", file=sys.stderr)
    if last_path:
        print("\n✓ done. review at:", file=sys.stderr)
        print(f"  {last_path.parent}/", file=sys.stderr)
    return 0


def cmd_queue(args) -> int:
    paths = list_queue(status=args.status)
    if not paths:
        print(f"(no drafts in queue/{args.status}/)", file=sys.stderr)
        return 0
    for path in paths:
        print(path)
    return 0


def cmd_send(args) -> int:
    summary = send_approved_queue(dry_run=args.dry_run, rate_limit_per_min=args.rate_limit)
    print(f"\n  sent:    {len(summary['sent'])}", file=sys.stderr)
    print(f"  failed:  {len(summary['failed'])}", file=sys.stderr)
    if summary["failed"]:
        for path, reason in summary["failed"]:
            print(f"    ✗ {path}: {reason}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    if os.getenv("TECH_PARTNERS_SKIP") == "1":
        return 0

    parser = argparse.ArgumentParser(
        prog="tech-partners-outreach",
        description="Draft personalized tech partner outreach emails into a HITL queue.",
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    draft_parser = subparsers.add_parser("draft", help="Draft emails for one project × N tech partners")
    draft_parser.add_argument("--project", required=True, help="Path to project file (.json or simple .yml)")
    draft_parser.add_argument("--partners", required=True, help="Path to partners CSV")

    queue_parser = subparsers.add_parser("queue", help="List queue entries")
    queue_parser.add_argument("--status", default=PENDING, choices=[PENDING, APPROVED, REJECTED, SENT])

    send_parser = subparsers.add_parser("send", help="Send approved drafts via SMTP")
    send_parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without delivering it")
    send_parser.add_argument("--rate-limit", type=int, default=None, help="Max sends per minute; 0 disables rate limiting")

    args = parser.parse_args(argv)
    if args.cmd == "draft":
        return cmd_draft(args)
    if args.cmd == "queue":
        return cmd_queue(args)
    if args.cmd == "send":
        return cmd_send(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
