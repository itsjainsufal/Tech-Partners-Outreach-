# Tech-Partners-Outreach-

Automated pipeline to research prospective technical pilot partners, synthesize API fit against integration needs, and draft personalized outreach emails.

## Queueing outreach jobs

Run the pipeline with JSON inputs:

```bash
python outreach_pipeline.py \
  --prospects /absolute/path/to/prospects.json \
  --integration-needs /absolute/path/to/integration_needs.json
```

Each run writes durable JSON jobs to:

`data/mail_queue/queued/`

These queued jobs are intended for review and later delivery by a mail-sender agent.
