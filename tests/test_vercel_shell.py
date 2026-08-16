from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_loader_has_no_embedded_raw_script_terminator() -> None:
    html = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")

    # The production shell intentionally has one real closing </script>: the
    # loader's own terminator. A raw </script> inside a JavaScript string makes
    # the HTML parser terminate the loader early and renders the remaining JS
    # as page text.
    assert html.lower().count("</script>") == 1


def test_phase10r_logic_is_loaded_by_the_shared_phase_template() -> None:
    html = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    phase10r = html.index('src="/phase10r-archive.js"')
    scenes = html.index('src="/phase-hero-scenes.js"')
    assert phase10r < scenes
