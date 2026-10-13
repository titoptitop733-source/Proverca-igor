# DROPZONE - Game Price Tracker

Track prices of PC games across digital stores (Steam, GOG, Humble, Epic, ...), keep a
wishlist with target prices and get an explained **"buy now or wait"** recommendation
based on the recorded price history.

**Author:** _Your Name_ · Technical University of Košice, FEI · Programovanie v Pythone

## Problem being solved

Game prices change often and differ between stores. Checking a wishlist manually in
several stores is slow and it is easy to miss a sale - or to buy just before a bigger one.
DROPZONE records prices of tracked games from all stores into a local database, shows the
price history, compares stores and tells the user whether the current price is a good
deal compared to the game's history.

## Features

- search any PC game and add it to the wishlist (live data from the CheapShark API)
- price snapshots from all stores stored in SQLite, with a minimal interval between checks
- statistics with pandas: all-time low, average, highest price, discount frequency
- **buy / good deal / wait recommendation** with human-readable reasons
- target prices with alerts (target reached, almost there, waiting for a drop)
- dashboard: potential savings, price drops, historical lows, activity feed
- **Discover** page with live discounts, store / price / discount filters and sorting
- prices shown in USD, EUR or GBP (ECB exchange rates from the Frankfurter API)
- dark and light theme (or follow the system setting), remembered in the browser
- three user interfaces sharing one application core:
  - **web app** (FastAPI REST API + single-page frontend) - main interface
  - desktop app (Tkinter + embedded matplotlib chart)
  - command line (argparse)

## Technology areas

| Area | Where it is used |
|------|------------------|
| HTTP and external APIs | `httpx` clients for CheapShark (prices, deals, stores) and Frankfurter (exchange rates); timeouts, error mapping, response validation, caching |
| Databases | SQLite schema (games, stores, price history), parameterized queries, window functions, automatic migrations |
| Data Science | pandas statistics and recommendation heuristic, matplotlib charts (PNG + Tkinter) |
| Web backend | FastAPI REST API, Pydantic request/response models, OpenAPI docs at `/docs` |
| User interface | web frontend (HTML/CSS/JavaScript, no build step), Tkinter desktop GUI |
| Scripting / CLI | `argparse` CLI, configuration via `.env`, `pathlib` |

## Requirements

- Python 3.10 or newer
- internet connection for live prices (no API keys are needed)
- a web browser for the web interface

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # optional - the defaults work out of the box
```

The database `data/game_tracker.db` is created automatically on first start.

## Configuration

All settings live in `.env` (see `.env.example`). Nothing is hard-coded in the source.

| Variable | Default | Meaning |
|----------|---------|---------|
| `GT_API_BASE_URL` | `https://www.cheapshark.com/api/1.0` | price API |
| `GT_FX_API_URL` | `https://api.frankfurter.dev/v1` | exchange-rate API |
| `GT_DB_PATH` | `data/game_tracker.db` | SQLite database file |
| `GT_HTTP_TIMEOUT` | `10` | HTTP timeout in seconds |
| `GT_MIN_SNAPSHOT_INTERVAL_HOURS` | `6` | minimal hours between two price checks of a game |
| `GT_WEB_HOST` | `127.0.0.1` | web server address (local computer only) |
| `GT_WEB_PORT` | `8000` | web server port |
| `GT_CHARTS_DIR` | `data/charts` | where CLI charts are saved |
| `GT_LOG_LEVEL` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Running

Run all commands from the project root with the virtual environment activated.

### Web application (recommended)

```bash
game-tracker web                 # opens http://127.0.0.1:8000 in the browser
game-tracker web --port 8080     # another port
game-tracker web --no-browser
```

Stop the server with `Ctrl+C`. The interactive API documentation is at
`http://127.0.0.1:8000/docs`.

### Desktop application

```bash
game-tracker gui
```

### Command line

```bash
game-tracker search "hollow knight"        # find a game and its ID
game-tracker add 165363 --target 7.50      # track a game with a target price (USD)
game-tracker list                          # wishlist with prices and advice
game-tracker update                        # check prices (--force ignores the interval)
game-tracker history 165363                # best price per check (--all for every store)
game-tracker stats 165363                  # statistics and recommendation
game-tracker chart 165363 --open           # save a PNG chart and open it
game-tracker target 165363 5
game-tracker remove 165363
```

## Basic usage (web)

1. Click **Track a game**, search a title and click **Track**.
2. The dashboard shows tracked games, potential savings and the biggest discount.
3. Open a game to see its price chart (1M - ALL), the store comparison and the
   **Buy or wait?** verdict, and set a target price.
4. **Discover** lists current deals; track any of them with one click.
5. Prices are checked automatically when the app starts (respecting the interval);
   the refresh button checks all games immediately.

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | totals, featured deal, activity feed |
| GET | `/api/wishlist` | tracked games with prices, status and advice |
| POST | `/api/wishlist` | track a game `{game_id, target_price?}` (201, 409 duplicate) |
| DELETE | `/api/wishlist/{id}` | stop tracking (204, 404) |
| PUT | `/api/wishlist/{id}/target` | set or clear the target price |
| GET | `/api/games/{id}` | detail: statistics, history, store offers |
| POST | `/api/update` | check prices `{force}` |
| GET | `/api/search?q=` | search games |
| GET | `/api/deals` | current deals (`sort`, `store`, `max_price`, `title`, `page`) |
| GET | `/api/stores`, `/api/meta` | store list; version, exchange rates, sources |

All prices in the API are in USD; the frontend converts them for display.

## Tests

```bash
pytest
```

The tests never use the network: external APIs are replaced by `httpx.MockTransport`
or fake data sources, the database is created in a temporary directory and the REST
API is tested with FastAPI's `TestClient`.

## Documentation

The technical documentation is in `docs/documentation.pdf` (Slovak). It is generated by
`docs/build_documentation.py`; to rebuild it after changing the text or the screenshots
in `docs/img/`:

```bash
pip install -e ".[docs]"
python docs/build_documentation.py
```

## Project structure

```
src/game_tracker/
├── api_client.py    # CheapShark HTTP client -> domain models
├── currency.py      # Frankfurter exchange rates with caching and fallback
├── models.py        # dataclasses (Game, Deal, PricePoint, ...)
├── storage.py       # SQLite repository and migrations
├── collector.py     # adding games, price updates, alerts
├── analysis.py      # pandas statistics and buy/wait recommendation
├── insights.py      # target status, activity feed, dashboard totals
├── overview.py      # stored data + analysis, shared by all interfaces
├── service.py       # thread-safe facade for the GUI and the web API
├── charts.py        # matplotlib charts
├── config.py        # settings from environment / .env
├── cli.py           # command-line interface
├── ui/              # Tkinter desktop GUI
└── web/
    ├── app.py           # FastAPI application and routes
    ├── schemas.py       # Pydantic request/response models
    ├── serializers.py   # domain objects -> API responses
    ├── server.py        # uvicorn start-up
    └── static/          # frontend: index.html, css/, js/ (ES modules)
tests/               # pytest tests
docs/                # documentation (PDF)
```

## How the recommendation works

The advice uses the best price of every check plus the all-time low reported by
CheapShark (which also covers the time before tracking started):

1. **BUY NOW** - the price reached your target, or is within 10 % of the all-time low
2. **GOOD DEAL** - at least 50 % off, or 15 % below the average recorded price
3. **WAIT** - the game has already been at least 30 % cheaper, or there is no discount

With fewer than 3 checks the advice is marked as low-confidence. The rules explain
past prices; they do not predict future sales. Thresholds are constants at the top of
`analysis.py`.

## Security notes

- the web server listens on `127.0.0.1` only, so it is not reachable from the network
- all SQL queries are parameterized; request bodies and query parameters are validated
  by Pydantic (types, ranges, lengths)
- text from external APIs is HTML-escaped in the frontend; only `https://` image URLs
  are accepted from the API
- no secrets are needed; configuration is read from `.env`, which is git-ignored

## Data sources

Prices: [CheapShark API](https://apidocs.cheapshark.com/) (USD). Exchange rates:
[Frankfurter](https://frankfurter.dev) - European Central Bank reference rates. Game
artwork: Steam store CDN. Icons: [Lucide](https://lucide.dev) (ISC licence).
