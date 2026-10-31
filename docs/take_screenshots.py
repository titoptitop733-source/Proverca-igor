"""Take the web screenshots used in docs/documentation.pdf from the running application.

Usage (two terminals, virtual environment activated in both):

    pip install -e ".[shots]"
    playwright install chromium          # one-time download of a browser (~150 MB)

    game-tracker web --no-browser        # terminal 1: leave it running
    python docs/take_screenshots.py      # terminal 2

The images are saved to docs/img/ and picked up by docs/build_documentation.py.
Use your real data (10+ tracked games with some price history) for the best result.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

IMG = Path(__file__).resolve().parent / "img"
VIEWPORT = {"width": 1440, "height": 900}
PREFS_KEY = "dropzone.prefs.v1"


def pick_game(base_url: str) -> int:
    """The tracked game with the longest price history looks best on the detail page."""
    games = httpx.get(f"{base_url}/api/wishlist", timeout=15).json()
    if not games:
        sys.exit("The wishlist is empty - track some games first (see README).")
    return max(games, key=lambda game: len(game["sparkline"]))["game_id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="address of the running app")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    try:
        httpx.get(f"{base_url}/api/meta", timeout=5).raise_for_status()
    except httpx.HTTPError:
        sys.exit(f"The application is not running at {base_url}. Start: game-tracker web --no-browser")
    game_id = pick_game(base_url)

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('Playwright is missing. Run: pip install -e ".[shots]" and playwright install chromium')

    IMG.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError:
            sys.exit("Browser is missing. Run: playwright install chromium")
        page = browser.new_page(viewport=VIEWPORT)

        def theme(name: str) -> None:
            page.goto(base_url + "/")
            page.evaluate(
                "([key, theme]) => localStorage.setItem(key, JSON.stringify({theme, currency: 'EUR'}))",
                [PREFS_KEY, name],
            )

        def shoot(route: str, filename: str) -> None:
            page.goto(f"{base_url}/#/{route}")
            page.reload()                       # apply the saved theme before taking the picture
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1800)         # charts and artwork finish loading
            page.mouse.move(2, 2)               # no hover effects in the picture
            page.screenshot(path=str(IMG / filename))
            print("saved", IMG / filename)

        theme("dark")
        shoot("overview", "web_overview.png")
        shoot(f"game/{game_id}", "web_game.png")
        shoot("wishlist", "web_wishlist.png")
        shoot("discover", "web_discover.png")
        theme("light")
        shoot(f"game/{game_id}", "web_game_light.png")
        theme("dark")
        browser.close()

    print("Done. Replace docs/img/desktop_gui.png with your own screenshot of: game-tracker gui")


if __name__ == "__main__":
    main()
