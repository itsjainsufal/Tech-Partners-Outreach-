# Tech-Partners-Outreach-

Draft personalized tech partner outreach emails into a human-review queue, then optionally send approved drafts over SMTP.

## What it does

```text
partners.csv + project.yml
            ↓
       Draft generator
            ↓
queue/pending/<timestamp>-<project>-to-<partner>.md
            ↓
  Human review / edit / approve
            ↓
queue/approved/ → SMTP send
queue/rejected/ → archive
```

The flow is adapted from `vc-outreach-agent`, but the prompt and data model are tuned for technology partnerships instead of investor outreach.

## Install

```bash
pip install -e .
cp .env.example .env
```

Optional extras:

```bash
pip install -e '.[anthropic,mcp,dev]'
```

## Usage

```bash
tech-partners-outreach draft --project examples/project.yml --partners examples/partners.csv
tech-partners-outreach queue --status pending
tech-partners-outreach send --dry-run
```

Expected CSV columns:
- `name,email,company,role,partnership_focus,website,linkedin,notes`

Project file fields:
- `name`, `one_liner`, `integration_value`, `traction`, `ideal_partner_profile`, `offer`, `proof_points`, `founder_name`, `founder_email`, `website_url`, `demo_url`

## Queue

By default drafts are written to `~/.tech-partners-outreach/queue/`.
Set `TECH_PARTNERS_QUEUE` to override the queue root.

## SMTP

Set:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

Use `SENDER_DRY_RUN=1` or `tech-partners-outreach send --dry-run` to test without delivering mail.

## MCP

```bash
tech-partners-outreach-mcp
```

Install the `mcp` extra first if you want to run the MCP server.
