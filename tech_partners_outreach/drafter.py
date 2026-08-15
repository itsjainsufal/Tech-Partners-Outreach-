from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .models import Draft, PartnerProject, TechPartner

DEFAULT_MODEL = os.getenv("TECH_PARTNERS_MODEL", "claude-sonnet-4-5")
SYSTEM_PROMPT = """You are an operator writing one cold email to one technology partner.

Rules:
1. Open with one concrete line explaining why this partner is strategically relevant.
2. Focus on integration, distribution, or co-sell value before describing the product.
3. Include one traction or proof point if provided.
4. Make one specific ask for a short partnership conversation or pilot.
5. Keep the body under 120 words and the subject under 8 words.
6. No hype, no exclamation marks, no generic praise.
7. End with the founder's name and email.

Return valid JSON only:
{"subject":"...","body":"..."}
"""


def _build_user_prompt(partner: TechPartner, project: PartnerProject) -> str:
    traction = "\n".join(f"- {item}" for item in project.traction) or "(none)"
    proof_points = "\n".join(f"- {item}" for item in project.proof_points) or "(none)"
    return f"""Project: {project.name}
One-liner: {project.one_liner}
Integration value: {project.integration_value or '(none provided)'}
Ideal partner profile: {project.ideal_partner_profile or '(none provided)'}
Offer: {project.offer or '(none provided)'}
Traction:
{traction}
Proof points:
{proof_points}
Website: {project.website_url or '(none)'}
Demo: {project.demo_url or '(none)'}
Founder: {project.founder_name} <{project.founder_email}>

Partner: {partner.name} ({partner.role} at {partner.company})
Partnership focus: {partner.partnership_focus or '(none provided)'}
Website: {partner.website or '(none)'}
Notes: {partner.notes or '(none)'}

Write the email now."""


def _template_fallback(partner: TechPartner, project: PartnerProject) -> Draft:
    proof = project.traction[0] if project.traction else (project.proof_points[0] if project.proof_points else project.one_liner)
    opening = partner.partnership_focus or f"your work at {partner.company or partner.name}"
    ask = project.offer or "a 15-minute call to see if a pilot makes sense"
    body = (
        f"Hi {partner.name.split()[0] if partner.name else 'there'},\n\n"
        f"Saw {opening} and thought {project.name} could be a strong fit for a tech partnership.\n\n"
        f"We help with {project.integration_value or project.one_liner}. Proof point: {proof}.\n\n"
        f"Open to {ask}?\n\n"
        f"— {project.founder_name}\n{project.founder_email}"
    )
    return Draft(
        partner_email=partner.email,
        partner_name=partner.name,
        project_name=project.name,
        subject=f"{project.name} x {partner.company or partner.name}"[:60],
        body=body,
        drafted_at=datetime.now(timezone.utc),
        raw_prompt="(template mode — no API key)",
        raw_response="",
    )


def _extract_json_block(text: str) -> dict[str, str]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


def _anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    return Anthropic(api_key=api_key)


def draft_email(
    partner: TechPartner,
    project: PartnerProject,
    *,
    model: str = DEFAULT_MODEL,
    client=None,
) -> Draft:
    if client is None:
        client = _anthropic_client()
    if client is None:
        return _template_fallback(partner, project)

    user_prompt = _build_user_prompt(partner, project)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(
            block.text for block in getattr(response, "content", []) if getattr(block, "type", None) == "text"
        )
        payload = _extract_json_block(raw_text)
        subject = (payload.get("subject") or "").strip()
        body = (payload.get("body") or "").strip()
        if not subject or not body:
            raise ValueError("Model returned empty subject/body")
        return Draft(
            partner_email=partner.email,
            partner_name=partner.name,
            project_name=project.name,
            subject=subject,
            body=body,
            drafted_at=datetime.now(timezone.utc),
            raw_prompt=user_prompt,
            raw_response=raw_text,
        )
    except Exception as exc:
        draft = _template_fallback(partner, project)
        draft.raw_response = f"(LLM error, fell back to template: {exc})"
        return draft
