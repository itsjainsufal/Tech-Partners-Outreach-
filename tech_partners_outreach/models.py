from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TechPartner:
    name: str
    email: str
    company: str = ""
    role: str = ""
    partnership_focus: str = ""
    website: str = ""
    linkedin: str = ""
    notes: str = ""
    last_contacted: Optional[datetime] = None


@dataclass
class PartnerProject:
    name: str
    one_liner: str
    integration_value: str = ""
    traction: list[str] = field(default_factory=list)
    ideal_partner_profile: str = ""
    offer: str = ""
    proof_points: list[str] = field(default_factory=list)
    founder_name: str = ""
    founder_email: str = ""
    website_url: str = ""
    demo_url: str = ""


@dataclass
class Draft:
    partner_email: str
    subject: str
    body: str
    partner_name: str = ""
    project_name: str = ""
    drafted_at: Optional[datetime] = None
    raw_prompt: str = ""
    raw_response: str = ""
