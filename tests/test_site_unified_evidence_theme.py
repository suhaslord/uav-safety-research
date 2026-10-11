"""Guard the unified AegisLand website theme and published research boundaries.

Static checks only: no new experiments, data downloads, or inferred flight safety.
"""
from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERCEL = ROOT / "deploy" / "vercel"
DASHBOARD = ROOT / "dashboard"
THEME = "/aegisland-unified.css?v=1"


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self.links = []
        self.ids = []
        self.head_count = 0
        self.title_count = 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "title":
            self.title_count += 1
        if tag == "h1":
            self.headings.append(tag)
        if tag == "a":
            self.links.append(data.get("href"))
        if "id" in data:
            self.ids.append(data["id"])


class UnifiedWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = (VERCEL / "aegisland-unified.css").read_text(encoding="utf-8")
        cls.home = (VERCEL / "index.html").read_text(encoding="utf-8")
        cls.audit = (VERCEL / "confidence-audit.html").read_text(encoding="utf-8")
        cls.faults = (VERCEL / "fdi-results.html").read_text(encoding="utf-8")
        cls.routes = json.loads((VERCEL / "vercel.json").read_text(encoding="utf-8"))["rewrites"]

    def test_every_published_template_uses_exact_same_last_theme_layer(self):
        # The original Failure Atlas HTML is in the research freeze SHA-256
        # manifest: it must not be edited by a site-only theme change.
        main_templates = [p for p in VERCEL.glob("*.html") if p.name not in {"failure-atlas.html", "model-vase.html"}]
        brand = (VERCEL / "aegisland-brand.css").read_text(encoding="utf-8")
        atlas = (VERCEL / "failure-atlas.html").read_text(encoding="utf-8")
        self.assertIn('@import url("/aegisland-unified.css?v=1");', brand)
        self.assertIn('/aegisland-brand.css', atlas)
        self.assertIn('/aegisland-brand.css', (VERCEL / "model-vase.html").read_text(encoding="utf-8"))
        dashboard_templates = list(DASHBOARD.glob("*.html"))
        phase_templates = list((DASHBOARD / "phases").glob("*.html"))
        phase_templates += list((DASHBOARD / "phases").glob("phase*/index.html"))
        self.assertGreaterEqual(len(main_templates), 12)
        self.assertGreaterEqual(len(dashboard_templates), 3)
        self.assertGreaterEqual(len(phase_templates), 14)
        for path in main_templates + dashboard_templates + phase_templates:
            with self.subTest(path=str(path.relative_to(ROOT))):
                s = path.read_text(encoding="utf-8")
                self.assertEqual(s.count(THEME), 1, "shared stylesheet should load exactly once")
                self.assertIn("</head>", s)
                self.assertLess(s.index(THEME), s.index("</head>"))
                # Last stylesheet takes precedence over the older page-specific
                # CSS without modifying the frozen simulator/archive scripts.
                head = s.split("</head>", 1)[0]
                self.assertNotIn("<link rel=\"stylesheet\"", head.split(THEME, 1)[1])

    def test_new_route_works_under_vercel_and_pages(self):
        rewrite_pairs = {(r["source"], r["destination"]) for r in self.routes}
        self.assertIn(("/confidence-audit/", "/confidence-audit.html"), rewrite_pairs)
        self.assertIn(("/confidence-audit", "/confidence-audit.html"), rewrite_pairs)
        self.assertIn(("/fdi-results/", "/fdi-results.html"), rewrite_pairs)

    def test_audited_scientific_failures_are_prominent_and_attributed(self):
        for value in ("86", "135", "two original video sessions", "43 / 86", "23 / 86",
                      "44 / 86", "22 / 86", "NO_DATASET_ADMITTED",
                      "2 accepted.", "2 incorrect.", "0 / 86",
                      "previously used protected data", "11691644582"):
            with self.subTest(value=value):
                self.assertIn(value.lower(), self.audit.lower())
        for value in ("93.75%", "96.25%", "40 / 40", "49.1%",
                      "offline", "not", "flight safety", "11693248745"):
            with self.subTest(value=value):
                self.assertIn(value.lower(), self.faults.lower())
        self.assertIn('href="/confidence-audit/"', self.home)
        self.assertIn('id="confidence-findings"', self.home)
        self.assertIn("NO DATASET", self.home)

    def test_accessibility_and_mobile_contract(self):
        d = Document()
        d.feed(self.audit)
        self.assertEqual(d.title_count, 1)
        self.assertEqual(len(d.headings), 1)
        self.assertEqual(len(d.ids), len(set(d.ids)))
        self.assertIn("#main", d.links)
        self.assertIn("#results", d.links)
        self.assertIn("#boundaries", d.links)
        self.assertNotIn("onfocus=", self.audit)
        self.assertIn(".report-skip:focus", self.theme)
        self.assertIn("prefers-reduced-motion", self.theme)
        self.assertIn("@media(max-width:560px)", self.theme)
        self.assertIn("min-height:44px", self.theme)

    def test_shared_theme_uses_graphite_white_and_single_clear_accent(self):
        for literal in ("--vase-ink:#171a20", "--vase-red:#e82127",
                        "--vase-paper:#fff", "--vase-soft:#f4f4f4",
                        "--blue:#e82127"):
            self.assertIn(literal, self.theme)
        self.assertIn(".aegis-home-spotlight", self.theme)
        self.assertIn(".aegis-report", self.theme)
        self.assertIn(".fdi-hero", self.theme)
        self.assertIn(".atlas-hero", self.theme)
        self.assertIn(".vase-hero", self.theme)

    def test_camera_report_is_not_misrepresented_as_motor_fault_study(self):
        self.assertIn("H1/H2 motor-fault simulations do not answer", self.audit)
        self.assertIn("not a calibrated", self.home)
        # The signed Failure Atlas HTML is unchanged. The audit is linked
        # from the main page, Phase 25 and VASE instead of altering the freeze.
        self.assertIn('href="/confidence-audit/"',
                      (VERCEL / "phase25.html").read_text(encoding="utf-8"))
        self.assertIn('href="/confidence-audit/"', self.home)
        self.assertIn("Phase 26", self.audit)


if __name__ == "__main__":
    unittest.main()
