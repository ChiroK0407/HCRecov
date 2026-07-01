import json
import os
import tempfile
import unittest

from generate_report_data import build_report_payload, write_payload_file


class ReportPayloadTests(unittest.TestCase):
    def test_payload_contains_pdf_required_sections(self):
        payload = build_report_payload()

        self.assertIn("summary", payload)
        self.assertIn("project", payload)
        self.assertIn("version", payload)
        self.assertIn("feed", payload)
        self.assertIn("chart_data", payload)
        self.assertIn("matrix", payload)
        self.assertIn("ledgers", payload)

        self.assertIn("prepared_by", payload["summary"])
        self.assertIn("plant", payload["summary"])
        self.assertIn("findings", payload["summary"])
        self.assertIn("recommendation", payload["summary"])

        self.assertIn("efficiencies", payload["chart_data"])
        self.assertIn("capex_inr", payload["chart_data"])
        self.assertIn("target_pct", payload["chart_data"])

        self.assertIn("headers", payload["matrix"])
        self.assertIn("rows", payload["matrix"])

        self.assertIn("membrane", payload["ledgers"])
        self.assertIn("adsorption", payload["ledgers"])
        self.assertIn("absorption", payload["ledgers"])

        first_ledger_rows = payload["ledgers"]["membrane"]["rows"]
        self.assertTrue(first_ledger_rows)
        self.assertIn("pressure_drop", first_ledger_rows[0])
        self.assertIn("flow_rate", first_ledger_rows[0])

    def test_bridge_payload_file_contains_component_fields(self):
        payload = build_report_payload()

        with tempfile.TemporaryDirectory() as tmpdir:
            bridge_path = os.path.join(tmpdir, "_payload.json")
            write_payload_file(payload, bridge_path)

            with open(bridge_path, "r", encoding="utf-8") as handle:
                written_payload = json.load(handle)

            first_row = written_payload["ledgers"]["membrane"]["rows"][0]
            self.assertIn("pressure_drop", first_row)
            self.assertIn("flow_rate", first_row)
            self.assertIn("capex", first_row)
            self.assertIn("opex", first_row)


if __name__ == "__main__":
    unittest.main()
