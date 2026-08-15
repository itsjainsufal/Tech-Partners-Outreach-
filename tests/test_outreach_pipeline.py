import json
import tempfile
import unittest
from pathlib import Path

from outreach_pipeline import build_outreach_job, queue_outreach_jobs


class OutreachPipelineTests(unittest.TestCase):
    def test_build_outreach_job_includes_personalized_email_and_fit_summary(self):
        partner = {
            "name": "Acme APIs",
            "contact_name": "Sam",
            "product_ecosystem": "Developer tools and analytics",
            "api_capabilities": "REST API with OAuth2 webhooks",
            "api_features": ["rate limits", "webhooks"],
        }

        job = build_outreach_job(partner, ["OAuth2", "SAML"])

        self.assertEqual(job["job_type"], "tech_partner_outreach")
        self.assertEqual(job["status"], "queued")
        self.assertIn("Acme APIs", job["email_draft"]["subject"])
        self.assertIn("Hi Sam", job["email_draft"]["body"])
        self.assertEqual(job["fit_summary"][0]["status"], "aligned")
        self.assertEqual(job["fit_summary"][1]["status"], "requires_discovery")

    def test_queue_outreach_jobs_writes_durable_json_jobs_to_mail_queue(self):
        prospects = [{"name": "Nova Systems", "contact_name": "Taylor"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "data" / "mail_queue" / "queued"
            queued = queue_outreach_jobs(prospects, ["webhooks"], output_dir)

            self.assertEqual(len(queued), 1)
            self.assertTrue(queued[0].exists())
            self.assertIn(str(output_dir), str(queued[0]))

            payload = json.loads(queued[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["partner"]["name"], "Nova Systems")
            self.assertEqual(payload["status"], "queued")


if __name__ == "__main__":
    unittest.main()
