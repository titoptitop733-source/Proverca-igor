"""Static checks of the web frontend: every referenced file exists and is served."""

import re
from pathlib import Path

from game_tracker.web.app import STATIC_DIR

IMPORT_RE = re.compile(r'from\s+"(\.{1,2}/[^"]+)"')


def test_index_references_existing_assets():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    for asset in re.findall(r'(?:src|href)="/([^"]+\.(?:js|css))"', html):
        assert (STATIC_DIR / asset).is_file(), asset


def test_all_javascript_imports_resolve():
    for script in STATIC_DIR.rglob("*.js"):
        for relative in IMPORT_RE.findall(script.read_text(encoding="utf-8")):
            target = (script.parent / relative).resolve()
            assert target.is_file(), f"{script.name} imports missing {relative}"


def test_dynamic_text_is_escaped_in_templates():
    """Titles come from an external API; HTML templates must not insert them unescaped.

    Lines without HTML markup (plain strings for toast() or openModal(), which escape
    their input themselves) are not templates and are skipped.
    """
    raw_title = re.compile(r"\$\{(?:game|deal|item|event)\.title\}")
    for script in STATIC_DIR.rglob("*.js"):
        for number, line in enumerate(script.read_text(encoding="utf-8").splitlines(), 1):
            if "<" in line:
                assert not raw_title.search(line), f"{script.name}:{number} inserts a raw title"


def test_javascript_is_served_with_javascript_mime_type(tmp_path):
    from fastapi.testclient import TestClient

    from game_tracker.config import Settings
    from game_tracker.service import TrackerService
    from game_tracker.web.app import create_app
    from tests.test_web_api import FakeSource

    settings = Settings("x", tmp_path / "db.sqlite", tmp_path, 1, 6, "WARNING")
    client = TestClient(create_app(TrackerService(FakeSource(), settings)))
    response = client.get("/js/main.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert Path(STATIC_DIR / "js" / "main.js").is_file()
