"""Blue/white, video-led home should not regress to hidden NASA footage or red branding."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "deploy" / "vercel"


class HomeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.details_depth = 0
        self.videos = []
        self.sources = []
        self.styles = []
        self.sections = []
        self.video_depth = 0

    def handle_starttag(self, tag, attributes):
        attr = dict(attributes)
        if tag == "details":
            self.details_depth += 1
        if tag == "section":
            self.sections.append(attr.get("class", ""))
        if tag == "video":
            self.videos.append((attr, self.details_depth))
            self.video_depth += 1
        if tag == "source" and self.video_depth:
            self.sources.append(attr)
        if tag == "link" and attr.get("rel") == "stylesheet":
            self.styles.append(attr.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "details":
            self.details_depth -= 1
        if tag == "video":
            self.video_depth -= 1


def test_visible_film_and_video_formats_are_real_local_assets():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    parser = HomeParser()
    parser.feed(home)
    assert len(parser.videos) >= 2
    for video, details in parser.videos:
        assert not details, "Footage must not be hidden in collapsed details"
        assert {"muted", "playsinline", "autoplay", "controls"} <= video.keys()
        assert video.get("poster", "").startswith("/film/")
        assert (ROOT / video["poster"].lstrip("/")).is_file()
    for source in parser.sources:
        assert (ROOT / source["src"].lstrip("/")).is_file()
    assert {s["type"] for s in parser.sources} >= {"video/mp4", "video/webm"}


def test_interactive_explorer_stays_separate_from_film_hero():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert home.count('id="home-comparison"') == 1
    assert home.index('class="home-film-hero"') < home.index('class="home-comparison-feature"')
    assert 'id="home-show-boxes"' in home
    assert all(f'data-home-condition="{key}"' in home
               for key in ("clean", "blur", "low_light", "noise", "occlusion", "mixed"))
    assert "Illustrative reused KIOS frame" in home
    assert "No flight-safety claim" in home
    assert "not a calibrated probability of a safe landing" in home


def test_home_is_blue_and_css_loads_last():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "home-film-restore.css").read_text(encoding="utf-8")
    js = (ROOT / "home-film-restore.js").read_text(encoding="utf-8")
    assert "/home-film-restore.css" in home
    assert home.index("/aegisland-unified.css") < home.index("/home-film-restore.css")
    assert "/home-film-restore.js" in home
    assert "#1673c9" in css
    assert "IntersectionObserver" in js
    assert "prefers-reduced-motion" in js
    assert "saveData" in js
    assert "#e82127" not in css.lower()
    assert "#e82127" not in (ROOT / "aegisland-unified.css").read_text().lower()
    assert "#e82127" not in (ROOT / "aegisland-brand.css").read_text().lower()
