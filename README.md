# Game Price Tracker

Track prices of PC games across many digital stores (Steam, GOG, Humble, ...) and find
out when it is a good time to buy.

**Author:** _Your Name_ · Technical University of Košice, FEI · Programovanie v Pythone

## Problem being solved

Game prices change frequently and differ between stores. Checking a wishlist manually in
several stores is slow and it is easy to miss a sale. This application keeps a wishlist,
regularly records prices from all stores into a local database and notifies the user when
a game drops below a chosen target price.

## Current functionality

- search games by title via the public [CheapShark API](https://apidocs.cheapshark.com/)
- wishlist with optional target price per game
- download current deals from all stores and store snapshots in SQLite
- minimal interval between snapshots (no duplicate data when updating often)
- price history per game (best price per snapshot or all stores)
- price statistics with pandas: all-time low, average, discount frequency, biggest discount
- **"buy now / good deal / wait" recommendation** with explained reasons
- price history charts (matplotlib, PNG)
- price alerts when the best price is at or below the target
- **desktop GUI (Tkinter)**: search & add games, wishlist coloured by advice, statistics,
  embedded interactive chart, price alert pop-ups, prices refreshed in a background thread
- automatic database migration from older versions
- error handling for network problems, timeouts, rate limits and invalid input

## Planned functionality

- conversion of prices to EUR using an exchange-rate API
- scheduled automatic updates

## Technology areas

| Area | Usage |
|------|-------|
| HTTP and external API | `httpx` client for CheapShark, JSON parsing, timeouts, error handling |
| Databases | SQLite schema with wishlist, stores and price history, parameterized queries |
| Scripting / CLI | `argparse` CLI, configuration via `.env`, `pathlib` |
| Data Science | pandas statistics, recommendation heuristic, matplotlib charts |
| User interface | Tkinter / ttk desktop GUI with embedded matplotlib chart |

## Requirements

- Python 3.10+
- internet connection (no API key needed)

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # optional, defaults work out of the box
```

## Configuration

All settings are in `.env` (see `.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `GT_API_BASE_URL` | `https://www.cheapshark.com/api/1.0` | API base URL |
| `GT_DB_PATH` | `data/game_tracker.db` | SQLite database file (created automatically) |
| `GT_HTTP_TIMEOUT` | `10` | HTTP timeout in seconds |
| `GT_LOG_LEVEL` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `GT_MIN_SNAPSHOT_INTERVAL_HOURS` | `6` | minimal hours between two snapshots of a game |
| `GT_CHARTS_DIR` | `data/charts` | where charts are saved |

## Running

Run commands from the project root.

### Desktop application

```bash
game-tracker gui          # or: game-tracker-gui
```

On start the application refreshes prices in the background (games updated in the last
`GT_MIN_SNAPSHOT_INTERVAL_HOURS` are skipped) and shows a pop-up when a price reaches
your target.

### Command line

```bash
game-tracker search "hollow knight"        # find a game and its ID
game-tracker add 12345 --target 7.50       # add to wishlist with target price
game-tracker list                          # wishlist with prices and buy/wait advice
game-tracker update                        # refresh prices (add --force to ignore interval)
game-tracker history 12345                 # best price per snapshot (--all for every store)
game-tracker stats 12345                   # statistics and recommendation
game-tracker chart 12345 --open            # save price chart as PNG and open it
game-tracker target 12345 5                # change target price
game-tracker remove 12345
```

Alternatively: `python -m game_tracker <command>`.

## Tests

```bash
pytest
```

Tests do not use the network: API responses are mocked with `httpx.MockTransport`
and the database is created in a temporary directory.

## Project structure

```
src/game_tracker/
├── api_client.py   # CheapShark HTTP client -> domain models
├── models.py       # dataclasses (Game, Deal, PricePoint, ...)
├── storage.py      # SQLite repository
├── collector.py    # business logic: adding games, updating prices, alerts
├── analysis.py     # pandas statistics and buy/wait recommendation
├── overview.py     # combines stored data + analysis (shared by CLI and GUI)
├── service.py      # thread-safe facade used by the GUI
├── charts.py       # matplotlib price charts (PNG and embedded)
├── config.py       # settings from environment / .env
├── cli.py          # command-line interface
└── ui/             # Tkinter GUI
    ├── app.py           # main window
    ├── search_dialog.py # search & add dialog
    ├── chart_panel.py   # matplotlib chart inside Tkinter
    ├── background.py    # runs HTTP requests outside the UI thread
    ├── formatting.py    # pure formatting helpers (unit tested)
    └── errors.py        # user-friendly error dialogs
tests/              # pytest tests
docs/               # documentation (PDF)
```

## Data source

Prices are provided by [CheapShark](https://www.cheapshark.com/). All prices are in USD.

## How the recommendation works

The advice is computed from the best price of every snapshot plus the all-time low
reported by CheapShark (which covers the period before tracking started):

1. **BUY NOW** - price reached your target, or is within 10 % of the all-time low
2. **GOOD DEAL** - at least 50 % off, or 15 % below the average observed price
3. **WAIT** - the game has already been at least 30 % cheaper, or there is no discount

With fewer than 3 snapshots the advice is marked as low-confidence. Thresholds are
constants at the top of `analysis.py`.
