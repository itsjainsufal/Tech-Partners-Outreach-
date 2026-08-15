from __future__ import annotations

import os
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    print(
        "tech-partners-outreach-mcp requires the `mcp` package. Install with: pip install 'tech-partners-outreach[mcp]'",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from .drafter import draft_email as _draft_email
from .models import PartnerProject, TechPartner
from .queue import APPROVED, PENDING, list_queue, queue_draft

mcp = FastMCP("tech-partners-outreach")


@mcp.tool()
def draft_email(
    partner_name: str,
    partner_email: str,
    project_name: str,
    one_liner: str,
    partner_company: str = "",
    partnership_focus: str = "",
    integration_value: str = "",
    traction: list[str] | None = None,
    ideal_partner_profile: str = "",
    offer: str = "",
    founder_name: str = "",
    founder_email: str = "",
    website_url: str = "",
    demo_url: str = "",
    save_to_queue: bool = False,
) -> str:
    partner = TechPartner(
        name=partner_name,
        email=partner_email,
        company=partner_company,
        partnership_focus=partnership_focus,
    )
    project = PartnerProject(
        name=project_name,
        one_liner=one_liner,
        integration_value=integration_value,
        traction=traction or [],
        ideal_partner_profile=ideal_partner_profile,
        offer=offer,
        founder_name=founder_name,
        founder_email=founder_email,
        website_url=website_url,
        demo_url=demo_url,
    )
    draft = _draft_email(partner, project)
    out = [f"### To: {draft.partner_email}", f"### Subject: {draft.subject}", "", draft.body]
    if save_to_queue:
        path = queue_draft(draft, status=PENDING)
        out.extend(["", f"📥 saved to HITL queue: `{path}`"])
    if draft.raw_response and "fell back" in draft.raw_response:
        out.extend(["", f"_{draft.raw_response}_"])
    return "\n".join(out)


@mcp.tool()
def list_pending() -> str:
    paths = list_queue(status=PENDING)
    if not paths:
        return "No drafts pending review."
    return "Pending drafts:\n" + "\n".join(f"- {path}" for path in paths)


@mcp.tool()
def list_approved() -> str:
    paths = list_queue(status=APPROVED)
    if not paths:
        return "No approved drafts ready to send."
    return "Approved drafts:\n" + "\n".join(f"- {path}" for path in paths)


def main() -> None:
    if os.getenv("TECH_PARTNERS_SKIP") == "1":
        return
    mcp.run()
