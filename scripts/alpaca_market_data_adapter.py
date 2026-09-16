#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

try:
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
    from alpaca.data.live.crypto import CryptoDataStream
    from alpaca.data.live.stock import StockDataStream
    from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest
    from alpaca.trading.client import TradingClient
except ImportError:  # pragma: no cover
    DataFeed = None
    CryptoDataStream = None
    StockDataStream = None
    CryptoHistoricalDataClient = None
    StockHistoricalDataClient = None
    CryptoLatestQuoteRequest = None
    StockLatestQuoteRequest = None
    TradingClient = None

from project_root import ROOT

PROVIDER = "Alpaca"
BLUE_CHIP_WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"
CRYPTO_WATCHLIST = ROOT / "data" / "volatile_crypto_candidates.json"
EXPANSION_WATCHLIST = ROOT / "data" / "apex_expansion_watchlist.txt"
STATE_PATH = ROOT / "data" / "alpaca_adapter_state.json"
QUOTE_SNAPSHOT_PATH = ROOT / "data" / "alpaca_normalized_quotes.json"
CAPITAL_STATUS_PATH = ROOT / "data" / "alpaca_capital_status.json"
LOG_PATH = ROOT / "logs" / "alpaca_market_data_adapter.jsonl"
DEFAULT_QUOTE_MAX_AGE_SECONDS = 15
DEFAULT_SCAN_INTERVAL_SECONDS = 7.0
MIN_REST_SCAN_INTERVAL_SECONDS = 60
MIN_LOOP_INTERVAL_SECONDS = 0.0007
MAX_LOOP_INTERVAL_SECONDS = 7.0


@dataclass
class NormalizedQuote:
    provider: str
    symbol: str
    asset_class: str
    bid: float | None
    ask: float | None
    last: float | None
    timestamp: str | None


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_age_seconds(value, now=None):
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - parsed).total_seconds()


def number(raw):
    if isinstance(raw, bool):
        return None
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def append_jsonl(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def load_credentials(env=os.environ):
    key_id = env.get("ALPACA_API_KEY_ID") or env.get("APCA_API_KEY_ID") or env.get("ALPACA_API_KEY")
    secret = env.get("ALPACA_API_SECRET_KEY") or env.get("APCA_API_SECRET_KEY") or env.get("ALPACA_SECRET_KEY")
    missing = []
    if not key_id:
        missing.append("ALPACA_API_KEY_ID")
    if not secret:
        missing.append("ALPACA_API_SECRET_KEY")
    return {"api_key_id": key_id, "api_secret_key": secret, "missing": missing, "ok": not missing}


def config_from_env(env=os.environ):
    def positive_float(name, default):
        try:
            value = float(env.get(name, default))
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def positive_int(name, default):
        return int(positive_float(name, default))

    def bounded_interval(name, default):
        value = positive_float(name, default)
        return max(MIN_LOOP_INTERVAL_SECONDS, min(MAX_LOOP_INTERVAL_SECONDS, value))

    return {
        "quote_max_age_seconds": positive_int("QUOTE_MAX_AGE_SECONDS", DEFAULT_QUOTE_MAX_AGE_SECONDS),
        "scan_interval_seconds": bounded_interval("SCAN_INTERVAL_SECONDS", DEFAULT_SCAN_INTERVAL_SECONDS),
        "min_rest_scan_interval_seconds": positive_int("MIN_REST_SCAN_INTERVAL_SECONDS", MIN_REST_SCAN_INTERVAL_SECONDS),
        "stock_feed": env.get("ALPACA_STOCK_FEED", "iex").lower(),
    }


def read_line_symbols(path: Path):
    if not path.exists():
        return []
    symbols = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        symbol = raw.strip().upper()
        if symbol and not symbol.startswith("#"):
            symbols.append(symbol)
    return symbols


def normalize_crypto_pair(symbol):
    symbol = str(symbol or "").strip().upper().replace("-", "/")
    if "/" in symbol:
        base, quote = symbol.split("/", 1)
        return f"{base}/{quote or 'USD'}"
    if symbol.endswith("USD"):
        return f"{symbol[:-3]}/USD"
    return f"{symbol}/USD"


def read_crypto_symbols(path: Path):
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    symbols = []
    for key in ("active_symbol", "fallback_symbol"):
        symbol = payload.get(key)
        if symbol:
            pair = normalize_crypto_pair(symbol)
            if pair not in symbols:
                symbols.append(pair)
    return symbols


def read_symbol_routes():
    equities = read_line_symbols(BLUE_CHIP_WATCHLIST)
    expansion = read_line_symbols(EXPANSION_WATCHLIST)
    for symbol in expansion:
        if symbol not in equities:
            equities.append(symbol)
    crypto = read_crypto_symbols(CRYPTO_WATCHLIST)
    return {"equities": equities, "crypto": crypto}


def get_field(obj, *names):
    if isinstance(obj, dict):
        for name in names:
            if name in obj and obj[name] is not None:
                return obj[name]
        return None
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def model_to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    return {}


def normalize_quote(raw, symbol, asset_class, trade=None):
    payload = model_to_dict(raw)
    trade_payload = model_to_dict(trade) if trade is not None else {}
    bid = number(get_field(payload, "bid_price", "bp", "bid"))
    ask = number(get_field(payload, "ask_price", "ap", "ask"))
    trade_last = number(get_field(trade_payload, "price", "p", "last"))
    midpoint_last = (bid + ask) / 2 if bid is not None and ask is not None else None
    timestamp = get_field(payload, "timestamp", "t") or get_field(trade_payload, "timestamp", "t")
    if isinstance(timestamp, datetime):
        timestamp = timestamp.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return NormalizedQuote(
        provider=PROVIDER,
        symbol=str(symbol).upper(),
        asset_class=asset_class,
        bid=bid,
        ask=ask,
        last=trade_last or midpoint_last,
        timestamp=str(timestamp) if timestamp else None,
    )


def quote_status(quote: NormalizedQuote, max_age_seconds, now=None):
    missing = []
    for field in ("bid", "ask", "last", "timestamp"):
        if getattr(quote, field) in (None, ""):
            missing.append(field)
    age = timestamp_age_seconds(quote.timestamp, now=now) if quote.timestamp else None
    stale = age is None or age < 0 or age > max_age_seconds
    ok = not missing and not stale
    return {
        "ok": ok,
        "missing": missing,
        "age_seconds": age,
        "stale": stale,
        "max_age_seconds": max_age_seconds,
    }


def capital_status_from_account(account):
    raw = model_to_dict(account)
    buying_power = number(get_field(raw, "buying_power"))
    crypto_buying_power = number(get_field(raw, "crypto_buying_power", "crypto_buying_power_usd"))
    status = str(get_field(raw, "status") or "UNKNOWN")
    blocked = bool(get_field(raw, "trading_blocked") or get_field(raw, "account_blocked"))
    missing = []
    if buying_power is None:
        missing.append("buying_power_usd")
    if crypto_buying_power is None:
        missing.append("crypto_buying_power_usd")
    return {
        "label": "capital",
        "status": "OK" if not missing and not blocked else "NO ACTION",
        "account_status": status,
        "buying_power_usd": buying_power,
        "crypto_buying_power_usd": crypto_buying_power,
        "missing": missing,
        "blocked": blocked,
        "source": "Alpaca TradingClient.get_account",
        "timestamp": iso_now(),
    }


def health_payload(state):
    quotes = state.get("quotes", {})
    stale_count = sum(1 for item in quotes.values() if not item.get("status", {}).get("ok"))
    symbols_ok = sorted(symbol for symbol, item in quotes.items() if item.get("status", {}).get("ok"))
    return {
        "last_event_at": state.get("last_event_at"),
        "symbols_ok": symbols_ok,
        "stale_count": stale_count,
        "scanner_viable": bool(state.get("scanner_viable")) and stale_count == 0,
        "execution_allowed": False,
        "capital_status": state.get("capital_status", {"status": "NO ACTION", "missing": ["capital"]}),
    }


class AlpacaReadOnlyAdapter:
    def __init__(self, credentials, config=None):
        self.credentials = credentials
        self.config = config or config_from_env()
        self.routes = read_symbol_routes()
        self.quotes = {}
        self.capital_status = {"status": "NO ACTION", "missing": ["capital"]}
        self.last_event_at = None

    def require_dependencies(self):
        if any(item is None for item in (DataFeed, StockDataStream, CryptoDataStream, StockHistoricalDataClient, CryptoHistoricalDataClient, TradingClient)):
            raise SystemExit("BLOCKED: alpaca-py is not installed.")
        if not self.credentials.get("ok"):
            raise SystemExit("BLOCKED: missing " + ", ".join(self.credentials.get("missing", [])))

    def state(self):
        return {
            "last_event_at": self.last_event_at,
            "symbols_ok": sorted(symbol for symbol, item in self.quotes.items() if item["status"]["ok"]),
            "stale_count": sum(1 for item in self.quotes.values() if not item["status"]["ok"]),
            "scanner_viable": False,
            "execution_allowed": False,
            "capital_status": self.capital_status,
            "quotes": self.quotes,
            "freshness_driver": "websocket quote events; REST is preflight/fallback only",
            "rest_snapshot_polling": False,
        }

    def record_quote(self, quote: NormalizedQuote):
        status = quote_status(quote, self.config["quote_max_age_seconds"])
        record = {"quote": asdict(quote), "status": status}
        self.quotes[quote.symbol] = record
        self.last_event_at = iso_now()
        write_json(QUOTE_SNAPSHOT_PATH, self.quotes)
        write_json(STATE_PATH, self.state())
        append_jsonl(LOG_PATH, {"event": "quote", "timestamp_utc": self.last_event_at, **record})
        return record

    async def stock_quote_handler(self, data):
        quote = normalize_quote(data, get_field(data, "symbol", "S"), "US_EQUITY")
        self.record_quote(quote)

    async def crypto_quote_handler(self, data):
        quote = normalize_quote(data, normalize_crypto_pair(get_field(data, "symbol", "S")), "CRYPTO")
        self.record_quote(quote)

    def reconcile_rest_once(self):
        self.require_dependencies()
        if certifi is not None:
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        api_key = self.credentials["api_key_id"]
        secret = self.credentials["api_secret_key"]
        feed = DataFeed.SIP if self.config["stock_feed"] == "sip" else DataFeed.IEX
        stock_client = StockHistoricalDataClient(api_key, secret)
        crypto_client = CryptoHistoricalDataClient(api_key, secret)
        trading_client = TradingClient(api_key, secret, paper=True)

        account = trading_client.get_account()
        self.capital_status = capital_status_from_account(account)
        write_json(CAPITAL_STATUS_PATH, self.capital_status)

        if self.routes["equities"]:
            response = stock_client.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=self.routes["equities"], feed=feed)
            )
            for symbol, quote in dict(response).items():
                self.record_quote(normalize_quote(quote, symbol, "US_EQUITY"))
        if self.routes["crypto"]:
            response = crypto_client.get_crypto_latest_quote(
                CryptoLatestQuoteRequest(symbol_or_symbols=self.routes["crypto"])
            )
            for symbol, quote in dict(response).items():
                self.record_quote(normalize_quote(quote, symbol, "CRYPTO"))
        write_json(STATE_PATH, self.state())
        return self.state()

    def reconcile_rest_loop_blocked(self):
        interval = self.config["scan_interval_seconds"]
        if interval < self.config["min_rest_scan_interval_seconds"]:
            raise SystemExit(
                "BLOCKED: REST latest-quote snapshots cannot be polled faster than "
                f"{self.config['min_rest_scan_interval_seconds']} seconds. "
                "Use --stream for fresh websocket-driven market data."
            )
        return self.reconcile_rest_once()

    async def run_streams(self):
        self.require_dependencies()
        if certifi is not None:
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        feed = DataFeed.SIP if self.config["stock_feed"] == "sip" else DataFeed.IEX
        stock_stream = StockDataStream(self.credentials["api_key_id"], self.credentials["api_secret_key"], feed=feed)
        crypto_stream = CryptoDataStream(self.credentials["api_key_id"], self.credentials["api_secret_key"])
        if self.routes["equities"]:
            stock_stream.subscribe_quotes(self.stock_quote_handler, *self.routes["equities"])
        if self.routes["crypto"]:
            crypto_stream.subscribe_quotes(self.crypto_quote_handler, *self.routes["crypto"])
        await asyncio.gather(stock_stream._run_forever(), crypto_stream._run_forever())


def load_state():
    if not STATE_PATH.exists():
        return {
            "last_event_at": None,
            "quotes": {},
            "scanner_viable": False,
            "execution_allowed": False,
            "capital_status": {"status": "NO ACTION", "missing": ["capital"]},
        }
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"last_event_at": None, "quotes": {}, "scanner_viable": False, "execution_allowed": False}


def auth_ok(headers, env=os.environ):
    token = env.get("CLOUDFLARE_SCAN_TOKEN") or env.get("SCAN_INTERFACE_TOKEN")
    if not token:
        return False
    auth = headers.get("Authorization") or ""
    bearer = auth.removeprefix("Bearer ").strip()
    return bearer == token or headers.get("X-Scan-Token") == token


class ScanHandler(BaseHTTPRequestHandler):
    def send_json(self, code, payload):
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if not auth_ok(self.headers):
            self.send_json(401, {"error": "unauthorized"})
            return
        parsed = urlparse(self.path)
        state = load_state()
        if parsed.path == "/health":
            self.send_json(200, health_payload(state))
            return
        if parsed.path == "/scan":
            mode = parse_qs(parsed.query).get("mode", [""])[0]
            if mode != "medium":
                self.send_json(400, {"error": "unsupported mode", "required": "medium"})
                return
            self.send_json(200, health_payload(state))
            return
        self.send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):  # pragma: no cover
        append_jsonl(LOG_PATH, {"event": "http", "timestamp_utc": iso_now(), "message": fmt % args})


def serve_cloudflare_interface(host, port):
    ThreadingHTTPServer((host, port), ScanHandler).serve_forever()


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    parser = argparse.ArgumentParser(description="Read-only Alpaca market-data adapter.")
    parser.add_argument("--rest-once", action="store_true")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default=os.getenv("SCAN_INTERFACE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SCAN_INTERFACE_PORT", "8787")))
    args = parser.parse_args()

    adapter = AlpacaReadOnlyAdapter(load_credentials(), config_from_env())
    if args.rest_once:
        print(json.dumps(adapter.reconcile_rest_once(), indent=2, sort_keys=True))
        return
    if args.stream:
        asyncio.run(adapter.run_streams())
        return
    if args.serve:
        serve_cloudflare_interface(args.host, args.port)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
