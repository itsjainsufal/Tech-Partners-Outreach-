from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "partner"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_fit_summary(partner: dict[str, Any], integration_needs: list[str]) -> list[dict[str, str]]:
    capabilities = " ".join(
        [
            str(partner.get("product_ecosystem", "")),
            str(partner.get("api_capabilities", "")),
            " ".join(map(str, partner.get("api_features", []))),
        ]
    ).lower()

    summary: list[dict[str, str]] = []
    for need in integration_needs:
        normalized_need = need.lower()
        if normalized_need and normalized_need in capabilities:
            status = "aligned"
            rationale = f"{partner.get('name', 'Partner')} explicitly mentions {need}."
        else:
            status = "requires_discovery"
            rationale = f"{need} is not clearly documented and should be confirmed during pilot scoping."
        summary.append({"integration_need": need, "status": status, "rationale": rationale})

    return summary


def _draft_email(partner: dict[str, Any], integration_needs: list[str], fit_summary: list[dict[str, str]]) -> dict[str, str]:
    name = partner.get("name", "there")
    contact_name = partner.get("contact_name", "Team")
    top_needs = ", ".join(integration_needs[:3]) if integration_needs else "our integration priorities"
    aligned = [item["integration_need"] for item in fit_summary if item["status"] == "aligned"]
    aligned_text = ", ".join(aligned) if aligned else "potential API alignment areas"

    subject = f"Pilot collaboration idea for {name}"
    body = (
        f"Hi {contact_name},\n\n"
        f"I have been following {name}'s product ecosystem and API roadmap and think there is a strong pilot fit. "
        f"We're currently prioritizing {top_needs}, and your team already appears aligned on {aligned_text}.\n\n"
        "Would you be open to a short working session to map a pilot integration plan and success metrics?\n\n"
        "Best,\n"
        "Tech Partnerships"
    )
    return {"subject": subject, "body": body}


def build_outreach_job(partner: dict[str, Any], integration_needs: list[str]) -> dict[str, Any]:
    fit_summary = _build_fit_summary(partner, integration_needs)
    email = _draft_email(partner, integration_needs, fit_summary)
    return {
        "job_type": "tech_partner_outreach",
        "status": "queued",
        "created_at": _utc_now_iso(),
        "partner": {
            "name": partner.get("name"),
            "website": partner.get("website"),
            "contact_name": partner.get("contact_name"),
            "contact_email": partner.get("contact_email"),
            "product_ecosystem": partner.get("product_ecosystem"),
            "api_capabilities": partner.get("api_capabilities"),
            "api_features": partner.get("api_features", []),
        },
        "integration_needs": integration_needs,
        "fit_summary": fit_summary,
        "email_draft": email,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as temp_file:
        json.dump(payload, temp_file, indent=2)
        temp_file.write("\n")
        temp_file.flush()
    Path(temp_file.name).replace(path)


def queue_outreach_jobs(
    prospects: list[dict[str, Any]],
    integration_needs: list[str],
    output_dir: str | Path = "data/mail_queue/queued",
) -> list[Path]:
    destination = Path(output_dir)
    queued_files: list[Path] = []

    for partner in prospects:
        if not partner.get("name"):
            raise ValueError("Each prospect must include a non-empty 'name'.")

        job = build_outreach_job(partner, integration_needs)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{timestamp}_{slugify(partner['name'])}.json"
        file_path = destination / filename
        counter = 1
        while file_path.exists():
            file_path = destination / f"{timestamp}_{slugify(partner['name'])}_{counter}.json"
            counter += 1

        _atomic_write_json(file_path, job)
        queued_files.append(file_path)

    return queued_files


def _load_json_list(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    if not isinstance(loaded, list):
        raise ValueError(f"Expected a JSON list in {path}.")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue personalized tech partner outreach jobs.")
    parser.add_argument("--prospects", required=True, help="Path to JSON array of prospect partner objects.")
    parser.add_argument(
        "--integration-needs",
        required=True,
        help="Path to JSON array of integration need strings.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/mail_queue/queued",
        help="Directory where durable queued JSON jobs are stored.",
    )

    args = parser.parse_args()
    prospects = _load_json_list(Path(args.prospects))
    integration_needs = _load_json_list(Path(args.integration_needs))

    queued = queue_outreach_jobs(prospects, [str(item) for item in integration_needs], args.output_dir)
    print(f"Queued {len(queued)} job(s) in {args.output_dir}")


if __name__ == "__main__":
    main()
