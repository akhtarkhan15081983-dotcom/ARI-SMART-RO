from django.test import TestCase


class HealthcheckTests(TestCase):
    def test_healthcheck_reports_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_healthcheck_rejects_post(self):
        response = self.client.post("/health/")
        self.assertEqual(response.status_code, 405)
