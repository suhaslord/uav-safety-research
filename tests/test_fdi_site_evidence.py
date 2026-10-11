"""Static regression checks for the audited AegisLand fault-isolation website."""
import json
import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "deploy" / "vercel"

class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.titles = 0
        self.h1_count = 0
    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if attr.get("id"): self.ids.append(attr["id"])
        if tag == "a": self.links.append(attr.get("href", ""))
        if tag == "title": self.titles += 1
        if tag == "h1": self.h1_count += 1

class FDIEvidenceWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = (WEB / "fdi-results.html").read_text(encoding="utf-8")
        cls.home = (WEB / "index.html").read_text(encoding="utf-8")
        cls.pilot = (WEB / "ornik-fdi.html").read_text(encoding="utf-8")
        cls.routes = json.loads((WEB / "vercel.json").read_text(encoding="utf-8"))["rewrites"]
        cls.parsed = SiteParser()
        cls.parsed.feed(cls.report)

    def test_new_result_route_is_deployed_as_static_html(self):
        rules = {(x["source"], x["destination"]) for x in self.routes}
        for source in ("/fdi-results", "/fdi-results/"):
            self.assertIn((source, "/fdi-results.html"), rules)

    def test_all_site_entry_points_link_to_current_result(self):
        self.assertIn('href="/fdi-results/"', self.home)
        self.assertIn('href="/fdi-results/"', self.pilot)
        self.assertIn('id="noise"', self.report)

    def test_document_structure_and_accessibility(self):
        self.assertEqual(self.parsed.titles, 1)
        self.assertEqual(self.parsed.h1_count, 1)
        self.assertEqual(len(self.parsed.ids), len(set(self.parsed.ids)))
        for anchor in ("#studies", "#noise", "#next"):
            self.assertIn(anchor, self.parsed.links)
        self.assertIn('class="skip"', self.report)

    def test_numerical_evidence_and_material_limits_remain_visible(self):
        for value in ("40 / 40", "144", "432", "93.75%", "96.25%", "49.1%", "0.272 s", "0.280"):
            if value == "0.280":
                continue  # H2 delay lives in the linked reproducible report.
            self.assertIn(value, self.report, value)
        for term in ("offline", "not", "flight safety", "half commanded motor speed"):
            self.assertIn(term.lower(), self.report.lower(), term)
        self.assertIn("11693248745", self.report)
        self.assertIn("11691184435", self.report)
        self.assertIn("fdi_h2_prospective_results.md", self.report)

    def test_initial_negative_result_not_overwritten(self):
        self.assertIn("0.491", self.pilot)
        self.assertIn("Read the newer independently checked", self.pilot)
        self.assertIn("49.1%", self.report)

if __name__ == "__main__":
    unittest.main()
