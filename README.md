# Game Price Tracker

Track prices of PC games across many digital stores (Steam, GOG, Humble, ...) and find
out when it is a good time to buy.

**Author:** _Your Name_ · Technical University of Košice, FEI · Programovanie v Pythone

## Problem being solved

Game prices change frequently and differ between stores. Checking a wishlist manually in
several stores is slow and it is easy to miss a sale. This application keeps a wishlist,
regularly records prices from all stores into a local database and notifies the user when
a game drops below a chosen target price.

## Current functionality (MVP)

- search games by title via the public [CheapShark API](https://apidocs.cheapshark.com/)
- wishlist with optional target price per game
- download current deals from all stores and store snapshots in SQLite
- price history per game, latest best price and store
- price alerts when the best price is at or below the target
- error handling for network problems, timeouts, rate limits and invalid input

## Planned functionality

- Tkinter GUI (search, wishlist, price chart, alerts)
- analysis with pandas: historical minimum, average discount, discount frequency
- "buy now or wait" recommendation based on collected price history
- price charts with matplotlib
- conversion of prices to EUR using an exchange-rate API
- scheduled automatic updates

## Technology areas

| Area | Usage |
|------|-------|
| HTTP and external API | `httpx` client for CheapShark, JSON parsing, timeouts, error handling |
| Databases | SQLite schema with wishlist, stores and price history, parameterized queries |
| Scripting / CLI | `argparse` CLI, configuration via `.env`, `pathlib` |
| Data Science *(planned)* | pandas + matplotlib for price statistics and charts |
| User interface *(planned)* | Tkinter / ttk desktop GUI |

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

## Running the MVP

Run commands from the project root:

```bash
game-tracker search "hollow knight"        # find a game and its ID
game-tracker add 12345 --target 7.50       # add to wishlist with target price
game-tracker list                          # wishlist with current best prices
game-tracker update                        # refresh prices of all games
game-tracker history 12345                 # recorded price history
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
├── collector.py    # business logic: updating prices, alerts
├── config.py       # settings from environment / .env
└── cli.py          # command-line interface
tests/              # pytest tests
docs/               # documentation (PDF)
```

## Data source

Prices are provided by [CheapShark](https://www.cheapshark.com/). All prices are in USD.
