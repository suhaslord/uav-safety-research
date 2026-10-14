"""One visible research question/hypothesis across GitHub and the public homepage."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.h1 = 0
        self.media = 0
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "video" and "data-home-film" in attributes:
            self.media += 1


def test_one_canonical_research_story_everywhere():
    story = json.loads((ROOT / "docs/research_story.json").read_text(encoding="utf-8"))
    contents = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in ("README.md", "PROJECT_SHOWCASE.md", "deploy/vercel/index.html")
    }
    for key in ("question", "hypothesis", "finding", "status"):
        assert story[key].strip()
        for path, content in contents.items():
            assert story[key] in content, (key, path)
    assert "43" in story["finding"] and "23" in story["finding"]
    assert "Phase 26" in contents["README.md"]
    assert "No flight-safety claim" in contents["deploy/vercel/index.html"]


def test_website_is_simple_film_first_and_has_a_falsifiable_plan():
    homepage = (ROOT / "deploy/vercel/index.html").read_text(encoding="utf-8")
    parsed = Tags()
    parsed.feed(homepage)
    assert parsed.h1 == 1
    assert len(parsed.ids) == len(set(parsed.ids))
    assert parsed.media == 2
    for anchor in ("question", "findings", "home-comparison", "next", "evidence"):
        assert anchor in parsed.ids
    assert homepage.index('id="question"') < homepage.index('id="findings"')
    assert homepage.index('id="findings"') < homepage.index('id="home-comparison"')
    assert homepage.index('id="home-comparison"') < homepage.index('id="next"')
    assert 'src="/home-evidence.js?v=' in homepage
    assert 'href="/research-story.css?v=' in homepage
    assert 'href="/fdi-results/"' in homepage
    assert "Independent camera validation is still pending." in homepage


def test_scientific_method_keeps_distinct_evaluation_sessions():
    showcase = (ROOT / "PROJECT_SHOWCASE.md").read_text(encoding="utf-8")
    protocol = (ROOT / "docs/phase26_protocol.md").read_text(encoding="utf-8")
    for text in ("development", "separate", "wrong", "coverage"):
        assert text in showcase.lower()
    assert "No threshold has been" in protocol
    assert "never-tested camera sessions" in showcase
    assert "not a new protocol" in showcase.lower()
