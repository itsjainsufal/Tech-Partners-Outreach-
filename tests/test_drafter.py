from __future__ import annotations

from types import SimpleNamespace

from tech_partners_outreach.drafter import draft_email
from tech_partners_outreach.models import PartnerProject, TechPartner


class FakeClient:
    def __init__(self, payload: str):
        self.payload = payload
        self.messages = self

    def create(self, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.payload)])


def _partner() -> TechPartner:
    return TechPartner(
        name="Jane Smith",
        email="jane@example.com",
        company="Acme Cloud",
        role="Partnerships",
        partnership_focus="building embedded integrations for AI workflows",
    )


def _project() -> PartnerProject:
    return PartnerProject(
        name="ConnectFlow",
        one_liner="workflow automation for partner ecosystems",
        integration_value="faster joint onboarding and referral routing",
        traction=["32 active design partners"],
        offer="a 15-minute pilot scoping call next week",
        founder_name="Sufal Jain",
        founder_email="sufal@example.com",
    )


def test_draft_email_falls_back_without_client():
    draft = draft_email(_partner(), _project(), client=None)
    assert draft.partner_email == "jane@example.com"
    assert "tech partnership" in draft.body.lower()


def test_draft_email_uses_model_json_payload():
    client = FakeClient('{"subject":"Partner intro","body":"Hi Jane\\n\\nPilot?\\n\\n— Sufal\\nsufal@example.com"}')
    draft = draft_email(_partner(), _project(), client=client)
    assert draft.subject == "Partner intro"
    assert "Pilot?" in draft.body
