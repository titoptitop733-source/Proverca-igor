"""Start the local web server (uvicorn) with real dependencies."""

from __future__ import annotations

import logging
import threading
import webbrowser

import uvicorn

from game_tracker.api_client import CheapSharkClient
from game_tracker.config import Settings
from game_tracker.currency import ExchangeRateProvider
from game_tracker.service import TrackerService
from game_tracker.web.app import create_app

logger = logging.getLogger(__name__)


def run_server(settings: Settings, open_browser: bool = True) -> None:
    url = f"http://{settings.web_host}:{settings.web_port}/"
    with CheapSharkClient(settings.api_base_url, settings.http_timeout) as client:
        rates = ExchangeRateProvider(settings.fx_api_url, settings.http_timeout)
        try:
            app = create_app(
                TrackerService(client, settings), rates, settings.min_snapshot_interval_hours
            )
            print(f"DROPZONE is running at {url}  (press Ctrl+C to stop)")
            if open_browser:
                threading.Timer(1.0, webbrowser.open, args=(url,)).start()
            uvicorn.run(
                app, host=settings.web_host, port=settings.web_port,
                log_level=settings.log_level.lower(),
            )
        finally:
            rates.close()
