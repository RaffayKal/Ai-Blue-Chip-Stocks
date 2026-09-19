#!/usr/bin/env python3
"""Read-only medium-cadence stock/crypto scanner for RunPod or a local host.

Robinhood is the frontline broker/data authority. Alpaca is corroboration only.
ChatGPT MCP/plugin observations may be supplied as
timestamped JSON via PLUGIN_INPUT_FILE; MCP tools are not directly callable from
an external Python process.
"""

from __future__ import annotations

import json
import os
import ssl
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

from project_root import ROOT

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass
if certifi is not None:
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


STOCK_URL = "https://data.alpaca.markets/v2/stocks/quotes/latest"
STOCK_TRADE_URL = "https://data.alpaca.markets/v2/stocks/trades/latest"
CRYPTO_URL = "https://data.alpaca.markets/v1beta3/crypto/us/latest/quotes"
CRYPTO_TRADE_URL = "https://data.alpaca.markets/v1beta3/crypto/us/latest/trades"
ALPACA_ACCOUNT_URL = os.getenv("ALPACA_ACCOUNT_URL", "https://paper-api.alpaca.markets/v2/account")
ALPACA_CLOCK_URL = os.getenv("ALPACA_CLOCK_URL", "https://paper-api.alpaca.markets/v2/clock")
ROBINHOOD_EQUITY_CAPITAL = ROOT / "data" / "robinhood_equity_capital_snapshot.json"
ROBINHOOD_EQUITY_QUOTE_DIR = ROOT / "data"
WATCHLIST = Path(os.getenv("WATCHLIST_FILE", "data/blue_chip_watchlist.txt"))
CRYPTO_WATCHLIST = Path(os.getenv("CRYPTO_WATCHLIST_FILE", "data/crypto_watchlist.txt"))
MAX_AGE = float(os.getenv("QUOTE_MAX_AGE_SECONDS", "120"))
MIN_LOOP_INTERVAL_SECONDS = 4.0
MAX_LOOP_INTERVAL_SECONDS = 420.0


def bounded_loop_interval(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = MAX_LOOP_INTERVAL_SECONDS
    if parsed <= 0:
        parsed = MAX_LOOP_INTERVAL_SECONDS
    return max(MIN_LOOP_INTERVAL_SECONDS, min(MAX_LOOP_INTERVAL_SECONDS, parsed))


INTERVAL = bounded_loop_interval(os.getenv("SCAN_INTERVAL_SECONDS", "7"))
PORT = int(os.getenv("PORT", "8080"))
AUTH_TOKEN = os.getenv("CRON_AUTH_TOKEN", "")
PLUGIN_INPUT_FILE = os.getenv("PLUGIN_INPUT_FILE", "")
PLUGIN_REGISTRY = [
    "superpowers", "alpaca", "blue_chip_stocks", "finances", "nvidia",
    "openai_developers", "runpod", "tradingcursor", "stocktwits",
    "longbridge", "calculator", "productivity", "cowork_plugin_management",
    "airtable", "figma", "amplitude", "github", "ace_knowledge_graph",
]

state = {
    "status": "starting",
    "last_scan_at": None,
    "quotes": [],
    "plugin_observations": [],
    "errors": [],
    "market_session": "UNKNOWN",
    "market_session_source": "alpaca_clock",
    "equity_data_status": {"status": "UNKNOWN"},
    "crypto_data_status": {"status": "UNKNOWN"},
    "data_viable": False,
    "scanner_viable": False,
    "execution_allowed": False,
    "capital_status": {"status": "NO ACTION", "reason": "dynamic broker lookup required"},
}
lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def number(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_ts(value):
    if not value or not isinstance(value, str):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def quote_age_seconds(timestamp):
    parsed = parse_ts(timestamp)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()


def normalize_quote(symbol: str, asset_class: str, raw: dict, trade: dict | None = None, provider: str = "alpaca") -> dict:
    bid = number(raw.get("bp"))
    ask = number(raw.get("ap"))
    trade = trade or {}
    last = number(raw.get("p"))
    last_source = "quote"
    if last is None:
        last = number(trade.get("p"))
        last_source = "latest_trade" if last is not None else None
    timestamp = raw.get("t")
    parsed_timestamp = parse_ts(timestamp)
    age = quote_age_seconds(timestamp)
    trade_timestamp = trade.get("t")
    trade_age = quote_age_seconds(trade_timestamp)
    missing = [
        name for name, value in (("bid", bid), ("ask", ask), ("last", last), ("timestamp", timestamp))
        if value in (None, "")
    ]
    stale = age is None or age < 0 or age > MAX_AGE
    ok = not missing and not stale
    return {
        "provider": provider,
        "symbol": symbol,
        "asset_class": asset_class,
        "bid": bid,
        "ask": ask,
        "last": last,
        "last_source": last_source,
        "timestamp": timestamp,
        "parsed_utc_timestamp": parsed_timestamp.isoformat() if parsed_timestamp else None,
        "age_seconds": age,
        "latest_trade_timestamp": trade_timestamp,
        "latest_trade_age_seconds": trade_age,
        "ok": ok,
        "missing": missing,
        "stale": stale,
    }


def symbols() -> tuple[list[str], list[str]]:
    stocks, crypto = [], []
    if not WATCHLIST.exists():
        return stocks, read_crypto_symbols()
    for raw in WATCHLIST.read_text().splitlines():
        s = raw.strip().upper()
        if not s or s.startswith("#"):
            continue
        if s in {"BTC/USD", "ETH/USD", "SOL/USD", "BTCUSD", "ETHUSD", "SOLUSD"} or "/" in s:
            crypto.append(s.replace("USD", "/USD") if "/" not in s else s)
        else:
            stocks.append(s)
    crypto.extend(read_crypto_symbols())
    return stocks, crypto


def read_crypto_symbols() -> list[str]:
    if not CRYPTO_WATCHLIST.exists():
        return []
    crypto = []
    for raw in CRYPTO_WATCHLIST.read_text().splitlines():
        symbol = raw.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        crypto.append(symbol.replace("USD", "/USD") if "/" not in symbol else symbol)
    return crypto


def alpaca_request(url: str) -> dict:
    key, secret = os.getenv("ALPACA_API_KEY_ID"), os.getenv("ALPACA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError("missing ALPACA_API_KEY_ID or ALPACA_API_SECRET_KEY")
    req = Request(url, headers={
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    })
    context = ssl.create_default_context(cafile=certifi.where()) if certifi is not None else None
    with urlopen(req, timeout=20, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def alpaca_get(url: str, symbols_: list[str], feed: str | None = None) -> dict:
    sep = "&" if "?" in url else "?"
    query = "symbols=" + ",".join(symbols_)
    if feed:
        query += "&feed=" + feed
    return alpaca_request(url + sep + query)


def latest_trades(url: str, symbols_: list[str], feed: str | None = None) -> dict:
    if not symbols_:
        return {}
    payload = alpaca_get(url, symbols_, feed)
    return payload.get("trades", {})


def alpaca_capital_status() -> dict:
    account = alpaca_request(ALPACA_ACCOUNT_URL)
    buying_power = number(account.get("buying_power"))
    crypto_buying_power = number(account.get("crypto_buying_power"))
    missing = []
    if buying_power is None:
        missing.append("buying_power_usd")
    if crypto_buying_power is None:
        missing.append("crypto_buying_power_usd")
    status = "NO ACTION" if missing else "OK"
    return {
        "label": "capital",
        "account_type": "paper" if "paper-api.alpaca.markets" in ALPACA_ACCOUNT_URL else "live_or_custom",
        "status": status,
        "source": ALPACA_ACCOUNT_URL,
        "buying_power_usd": buying_power,
        "crypto_buying_power_usd": crypto_buying_power,
        "missing": missing,
    }


def robinhood_equity_capital_status() -> dict:
    """Load the fresh Robinhood account artifact; never substitute Alpaca."""
    try:
        payload = json.loads(ROBINHOOD_EQUITY_CAPITAL.read_text())
    except (OSError, json.JSONDecodeError):
        payload = {}
    buying_power = number(payload.get("buying_power_usd"))
    retrieved_at = payload.get("capital_retrieved_at") or payload.get("timestamp")
    parsed = parse_ts(retrieved_at)
    age = (datetime.now(timezone.utc) - parsed).total_seconds() if parsed else None
    valid = (
        buying_power is not None
        and payload.get("capital_source") == "robinhood.get_account.buying_power"
        and age is not None
        and 0 <= age <= MAX_AGE
    )
    return {
        "label": "capital",
        "account_type": "robinhood",
        "status": "OK" if valid else "NO ACTION",
        "source": "Robinhood",
        "buying_power_usd": buying_power if valid else None,
        "missing": [] if valid else ["fresh Robinhood buying_power_usd"],
        "age_seconds": age,
    }


def robinhood_equity_quotes(symbols_: list[str]) -> dict:
    """Return only fresh per-symbol Robinhood quote artifacts."""
    result = {}
    for symbol in symbols_:
        path = ROBINHOOD_EQUITY_QUOTE_DIR / f"robinhood_equity_quote_snapshot_{symbol}.json"
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        timestamp = payload.get("quote_timestamp") or payload.get("timestamp")
        parsed = parse_ts(timestamp)
        age = (datetime.now(timezone.utc) - parsed).total_seconds() if parsed else None
        if payload.get("provider") != "Robinhood" or parsed is None or not (0 <= age <= MAX_AGE):
            continue
        result[symbol] = payload
    return result


def alpaca_market_session() -> dict:
    clock = alpaca_request(ALPACA_CLOCK_URL)
    is_open = clock.get("is_open")
    session = "OPEN" if is_open is True else "CLOSED" if is_open is False else "UNKNOWN"
    return {
        "market_session": session,
        "market_session_source": "alpaca_clock",
        "raw": {
            "timestamp": clock.get("timestamp"),
            "next_open": clock.get("next_open"),
            "next_close": clock.get("next_close"),
        },
    }


def lane_data_status(quotes: list[dict], asset_class: str, market_session: str | None = None) -> dict:
    lane_quotes = [quote for quote in quotes if quote.get("asset_class") == asset_class]
    stale = [quote for quote in lane_quotes if quote.get("stale")]
    missing = [quote for quote in lane_quotes if quote.get("missing")]
    ok = [quote for quote in lane_quotes if quote.get("ok")]
    status = "OK" if lane_quotes and len(ok) == len(lane_quotes) else "NO ACTION"
    reason = None
    if not lane_quotes:
        reason = "no symbols configured"
    elif asset_class == "stock" and market_session == "CLOSED" and stale:
        reason = "stale equity quotes are expected outside market hours"
    elif stale:
        reason = "stale quotes"
    elif missing:
        reason = "missing quote fields"
    return {
        "status": status,
        "symbols_total": len(lane_quotes),
        "symbols_ok": [quote["symbol"] for quote in ok],
        "stale_count": len(stale),
        "missing_count": len(missing),
        "reason": reason,
    }


def stale_quote_diagnostics(quotes: list[dict]) -> list[dict]:
    rows = []
    for quote in quotes:
        if quote.get("ok"):
            continue
        rows.append({
            "symbol": quote.get("symbol"),
            "provider": quote.get("provider"),
            "quote_timestamp": quote.get("timestamp"),
            "parsed_utc_timestamp": quote.get("parsed_utc_timestamp"),
            "age_seconds": quote.get("age_seconds"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "last": quote.get("last"),
        })
    return rows


def print_stale_quote_diagnostics(rows: list[dict]) -> None:
    for row in rows:
        print(
            "STALE_QUOTE "
            f"symbol={row['symbol']} "
            f"provider={row['provider']} "
            f"quote_timestamp={row['quote_timestamp']} "
            f"parsed_utc_timestamp={row['parsed_utc_timestamp']} "
            f"age_seconds={row['age_seconds']} "
            f"bid={row['bid']} "
            f"ask={row['ask']} "
            f"last={row['last']}",
            flush=True,
        )


def load_plugin_observations() -> list[dict]:
    if not PLUGIN_INPUT_FILE:
        return []
    path = Path(PLUGIN_INPUT_FILE)
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, list) else [value]
    except Exception as exc:
        state["errors"].append(f"plugin input: {exc}")
        return []


def scan() -> dict:
    stocks, crypto = symbols()
    quotes = []
    errors = []
    session_info = {
        "market_session": "UNKNOWN",
        "market_session_source": "alpaca_clock",
        "raw": {},
    }
    try:
        session_info = alpaca_market_session()
    except Exception as exc:
        errors.append(f"clock: {exc}")
    capital_status = {"status": "NO ACTION", "reason": "fresh Robinhood broker artifact required"}
    try:
        # Robinhood is frontline for equities. Crypto remains handled by the
        # dedicated Robinhood crypto-capital artifact in the APEX scanner;
        # this legacy medium orchestrator must not promote Alpaca to stock
        # authority.
        capital_status = robinhood_equity_capital_status() if stocks else alpaca_capital_status()
    except Exception as exc:
        errors.append(f"capital: {exc}")
    try:
        if stocks:
            robinhood_quotes = robinhood_equity_quotes(stocks)
            for symbol, q in robinhood_quotes.items():
                quotes.append(normalize_quote(symbol, "stock", q, q, provider="robinhood"))
        if crypto:
            crypto_trades = latest_trades(CRYPTO_TRADE_URL, crypto)
            payload = alpaca_get(CRYPTO_URL, crypto)
            for symbol, q in payload.get("quotes", {}).items():
                quotes.append(normalize_quote(symbol, "crypto", q, crypto_trades.get(symbol)))
    except Exception as exc:
        errors.append(str(exc))
    plugin_obs = load_plugin_observations()
    stale_count = sum(1 for q in quotes if not q.get("ok"))
    symbols_ok = [q["symbol"] for q in quotes if q.get("ok")]
    stale_diagnostics = stale_quote_diagnostics(quotes)
    print_stale_quote_diagnostics(stale_diagnostics)
    market_session = session_info["market_session"]
    equity_data_status = lane_data_status(quotes, "stock", market_session)
    crypto_data_status = lane_data_status(quotes, "crypto", market_session)
    data_viable = (
        not errors
        and (
            equity_data_status["status"] == "OK"
            or crypto_data_status["status"] == "OK"
        )
    )
    scanner_viable = data_viable and capital_status["status"] == "OK"
    result = {"status": "ok" if scanner_viable else "no_action", "last_scan_at": now(),
              "quotes": quotes, "plugin_observations": plugin_obs, "errors": errors,
              "symbols_ok": symbols_ok, "stale_count": stale_count,
              "stale_quote_diagnostics": stale_diagnostics,
              "market_session": market_session,
              "market_session_source": session_info["market_session_source"],
              "market_clock": session_info["raw"],
              "equity_data_status": equity_data_status,
              "crypto_data_status": crypto_data_status,
              "data_viable": data_viable, "scanner_viable": scanner_viable,
              "execution_allowed": False, "capital_status": capital_status,
              "plugin_registry": PLUGIN_REGISTRY}
    with lock:
        state.update(result)
    return result


class Handler(BaseHTTPRequestHandler):
    def _authorized(self) -> bool:
        return not AUTH_TOKEN or self.headers.get("Authorization") == f"Bearer {AUTH_TOKEN}"

    def _send(self, body: dict, code: int = 200) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send({"error": "unauthorized"}, 401)
            return
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            with lock:
                self._send({
                    "last_event_at": state["last_scan_at"],
                    "symbols_ok": state.get("symbols_ok", []),
                    "stale_count": state.get("stale_count", 0),
                    "market_session": state.get("market_session", "UNKNOWN"),
                    "market_session_source": state.get("market_session_source", "alpaca_clock"),
                    "equity_data_status": state.get("equity_data_status"),
                    "crypto_data_status": state.get("crypto_data_status"),
                    "data_viable": state.get("data_viable", False),
                    "scanner_viable": state["scanner_viable"],
                    "execution_allowed": state["execution_allowed"],
                    "capital_status": state.get("capital_status"),
                    "errors": state["errors"],
                    "status": state["status"],
                })
        elif parsed.path == "/scan":
            mode = parse_qs(parsed.query).get("mode", [""])[0]
            if mode and mode != "medium":
                self._send({"error": "unsupported mode", "required": "medium"}, 400)
            else:
                self._send(scan())
        else:
            self._send({"error": "not found"}, 404)

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    scan()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    while True:
        time.sleep(INTERVAL)
        scan()


if __name__ == "__main__":
    main()
