#!/usr/bin/env python3
import argparse
import asyncio
import gzip
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    load_dotenv = None

try:
    import certifi
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    certifi = None

try:
    from alpaca.data.enums import DataFeed
    from alpaca.data.live.crypto import CryptoDataStream
    from alpaca.data.live.stock import StockDataStream
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    DataFeed = None
    CryptoDataStream = None
    StockDataStream = None

from project_root import ROOT

WATCHLIST_PATH = ROOT / "data" / "blue_chip_watchlist.txt"


def load_blue_chip_watchlist():
    if not WATCHLIST_PATH.exists():
        return ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]
    symbols = []
    for raw in WATCHLIST_PATH.read_text(encoding="utf-8").splitlines():
        symbol = raw.strip().upper()
        if symbol and not symbol.startswith("#"):
            symbols.append(symbol)
    return symbols or ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]


BLUE_CHIPS = load_blue_chip_watchlist()
CRYPTO_PAIRS = ["BTC/USD", "ETH/USD"]
STREAM_DIR = ROOT / "data" / "alpaca_stream"
STATUS = STREAM_DIR / "status.json"
LATEST_CRYPTO_QUOTE = ROOT / "data" / "alpaca_crypto_quote_snapshot.json"
EVENT_LOG = ROOT / "logs" / "alpaca_market_stream.jsonl"
LOG_ARCHIVE_DIR = ROOT / "logs" / "archive"
MAX_JSONL_LOG_BYTES = 50 * 1024 * 1024  # append-only stream log; grew to 3GB+ unbounded before this


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def rotate_jsonl_if_oversized(path):
    """Archive (gzip) and reset an append-only JSONL log once it crosses
    MAX_JSONL_LOG_BYTES, instead of letting it grow forever. Preserves the
    old content (compressed, moved aside) rather than deleting it, since
    these are audit-relevant stream logs. Rotation failures never block the
    actual stream write.
    """
    try:
        if not path.exists() or path.stat().st_size < MAX_JSONL_LOG_BYTES:
            return
        LOG_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_path = LOG_ARCHIVE_DIR / f"{path.stem}.{stamp}{path.suffix}.gz"
        with path.open("rb") as source, gzip.open(archive_path, "wb") as dest:
            shutil.copyfileobj(source, dest)
        path.unlink()
    except OSError:
        pass


def append_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    rotate_jsonl_if_oversized(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")


def public_attrs(data):
    if hasattr(data, "model_dump"):
        dumped = data.model_dump(mode="json")
        return json.loads(json.dumps(dumped, default=str))
    out = {}
    for name in dir(data):
        if name.startswith("_"):
            continue
        value = getattr(data, name)
        if callable(value):
            continue
        try:
            value = json.loads(json.dumps(value, default=str))
        except TypeError:
            value = str(value)
        out[name] = value
    return out


def value(data, *names):
    for name in names:
        found = getattr(data, name, None)
        if found is not None:
            return found
    return None


def number(raw):
    if isinstance(raw, bool):
        return None
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def event_timestamp(data):
    timestamp = value(data, "timestamp", "time", "t")
    if isinstance(timestamp, datetime):
        return timestamp.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return str(timestamp) if timestamp else iso_now()


def normalize_symbol(raw):
    return str(raw or "").strip().upper().replace("-", "/")


def crypto_base(raw):
    symbol = normalize_symbol(raw)
    if "/" in symbol:
        return symbol.split("/", 1)[0]
    if symbol.endswith("USD"):
        return symbol[:-3]
    return symbol


def env_credential(primary, *aliases):
    for name in (primary, *aliases):
        value = os.getenv(name)
        if value:
            return value
    return None


class AlpacaMarketStream:
    def __init__(self, api_key, secret_key, stock_feed, blue_chips, crypto_pairs):
        self.api_key = api_key
        self.secret_key = secret_key
        self.stock_feed = stock_feed
        self.blue_chips = blue_chips
        self.crypto_pairs = crypto_pairs
        self.latest_stock_trades = {}
        self.latest_stock_quotes = {}
        self.latest_crypto_trades = {}
        self.latest_crypto_quotes = {}

    def write_status(self, state):
        write_json(STATUS, {
            "timestamp_utc": iso_now(),
            "runtime": "ALPACA_MARKET_DATA_STREAM",
            "state": state,
            "blue_chips": self.blue_chips,
            "crypto_pairs": self.crypto_pairs,
            "stock_feed": self.stock_feed,
            "stock_trade_symbols": sorted(self.latest_stock_trades),
            "stock_quote_symbols": sorted(self.latest_stock_quotes),
            "crypto_trade_symbols": sorted(self.latest_crypto_trades),
            "crypto_quote_symbols": sorted(self.latest_crypto_quotes),
            "execution_authority": False,
            "trade_execution_allowed": False,
            "feed_mode": "websocket_event_driven",
            "rest_snapshot_polling": False,
        })

    def record_event(self, kind, symbol, market_timestamp, payload):
        record = {
            "timestamp_utc": iso_now(),
            "market_timestamp": market_timestamp,
            "kind": kind,
            "symbol": symbol,
            "source": "AlpacaDataStream",
            "payload": payload,
            "execution_authority": False,
        }
        append_jsonl(EVENT_LOG, record)
        write_json(STREAM_DIR / f"latest_{kind}_{symbol.replace('/', '_')}.json", record)
        return record

    def write_crypto_market_input_if_ready(self, symbol):
        quote = self.latest_crypto_quotes.get(symbol)
        trade = self.latest_crypto_trades.get(symbol)
        if not quote:
            return
        bid = number(quote["payload"].get("bid"))
        ask = number(quote["payload"].get("ask"))
        trade_last = number((trade or {}).get("payload", {}).get("price"))
        midpoint_last = (bid + ask) / 2 if bid is not None and ask is not None else None
        last = trade_last or midpoint_last
        if bid is None or ask is None or last is None:
            return
        base = crypto_base(symbol)
        timestamp = max(quote["market_timestamp"], (trade or {}).get("market_timestamp", quote["market_timestamp"]))
        write_json(LATEST_CRYPTO_QUOTE, {
            "symbol": base,
            "asset_class": "CRYPTO",
            "session": "CRYPTO_24_7",
            "venue": "Alpaca Crypto",
            "broker_name": "Alpaca",
            "timestamp": timestamp,
            "quote_timestamp": timestamp,
            "bid": bid,
            "ask": ask,
            "last": last,
            "liquidity_usd": None,
            "data_status": "fresh",
            "risk_status": "fail",
            "source_count": 1,
            "source_conflict": False,
            "buying_power_usd": None,
            "crypto_buying_power_usd": None,
            "requested_notional_usd": None,
            "crypto_account_confirmed": False,
            "maintenance_active": None,
            "account_restricted": None,
            "margin_requested": False,
            "margin_approved": False,
            "account_net_worth_usd": None,
            "explicit_execution_authorization": False,
            "source": "AlpacaDataStream.crypto_trades_and_quotes",
            "feed_mode": "websocket_event_driven",
            "rest_snapshot_polling": False,
            "freshness_driver": "latest Alpaca websocket quote/trade event timestamp",
            "last_source": "trade" if trade_last is not None else "quote_midpoint",
            "raw_symbol": symbol,
        })

    async def stock_trade_handler(self, data):
        symbol = normalize_symbol(value(data, "symbol", "S"))
        payload = {
            "price": number(value(data, "price", "p")),
            "size": number(value(data, "size", "s")),
            "raw": public_attrs(data),
        }
        record = self.record_event("stock_trade", symbol, event_timestamp(data), payload)
        self.latest_stock_trades[symbol] = record

    async def stock_quote_handler(self, data):
        symbol = normalize_symbol(value(data, "symbol", "S"))
        payload = {
            "bid": number(value(data, "bid_price", "bid", "bp")),
            "ask": number(value(data, "ask_price", "ask", "ap")),
            "bid_size": number(value(data, "bid_size", "bs")),
            "ask_size": number(value(data, "ask_size", "as")),
            "raw": public_attrs(data),
        }
        record = self.record_event("stock_quote", symbol, event_timestamp(data), payload)
        self.latest_stock_quotes[symbol] = record

    async def crypto_trade_handler(self, data):
        symbol = normalize_symbol(value(data, "symbol", "S"))
        payload = {
            "price": number(value(data, "price", "p")),
            "size": number(value(data, "size", "s")),
            "raw": public_attrs(data),
        }
        record = self.record_event("crypto_trade", symbol, event_timestamp(data), payload)
        self.latest_crypto_trades[symbol] = record
        self.write_crypto_market_input_if_ready(symbol)

    async def crypto_quote_handler(self, data):
        symbol = normalize_symbol(value(data, "symbol", "S"))
        payload = {
            "bid": number(value(data, "bid_price", "bid", "bp")),
            "ask": number(value(data, "ask_price", "ask", "ap")),
            "bid_size": number(value(data, "bid_size", "bs")),
            "ask_size": number(value(data, "ask_size", "as")),
            "raw": public_attrs(data),
        }
        record = self.record_event("crypto_quote", symbol, event_timestamp(data), payload)
        self.latest_crypto_quotes[symbol] = record
        self.write_crypto_market_input_if_ready(symbol)

    async def run(self):
        if DataFeed is None or StockDataStream is None or CryptoDataStream is None:
            raise SystemExit("BLOCKED: alpaca-py is not installed.")
        if not self.api_key or not self.secret_key:
            raise SystemExit("BLOCKED: ALPACA_API_KEY_ID/APCA_API_KEY_ID and ALPACA_API_SECRET_KEY/APCA_API_SECRET_KEY are required.")

        self.write_status("starting")
        feed = DataFeed.SIP if self.stock_feed == "sip" else DataFeed.IEX
        stock_stream = StockDataStream(self.api_key, self.secret_key, feed=feed)
        crypto_stream = CryptoDataStream(self.api_key, self.secret_key)

        stock_stream.subscribe_trades(self.stock_trade_handler, *self.blue_chips)
        stock_stream.subscribe_quotes(self.stock_quote_handler, *self.blue_chips)
        crypto_stream.subscribe_trades(self.crypto_trade_handler, *self.crypto_pairs)
        crypto_stream.subscribe_quotes(self.crypto_quote_handler, *self.crypto_pairs)
        self.write_status("streaming")

        await asyncio.gather(stock_stream._run_forever(), crypto_stream._run_forever())


def parse_symbols(raw, defaults):
    if not raw:
        return defaults
    parsed = [item.strip().upper() for item in raw.split(",") if item.strip()]
    return parsed or defaults


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    parser = argparse.ArgumentParser(description="Stream Alpaca stock and crypto market data into local non-executing artifacts.")
    parser.add_argument("--stock-feed", default=os.getenv("ALPACA_STOCK_FEED", "iex"), choices=["iex", "sip"])
    parser.add_argument("--blue-chips", default=os.getenv("ALPACA_BLUE_CHIPS", ",".join(BLUE_CHIPS)))
    parser.add_argument("--crypto-pairs", default=os.getenv("ALPACA_CRYPTO_PAIRS", ",".join(CRYPTO_PAIRS)))
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    if certifi is not None:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

    stream = AlpacaMarketStream(
        env_credential("ALPACA_API_KEY_ID", "APCA_API_KEY_ID", "ALPACA_API_KEY"),
        env_credential("ALPACA_API_SECRET_KEY", "APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY"),
        args.stock_feed,
        parse_symbols(args.blue_chips, BLUE_CHIPS),
        parse_symbols(args.crypto_pairs, CRYPTO_PAIRS),
    )
    try:
        asyncio.run(stream.run())
    except KeyboardInterrupt:
        stream.write_status("stopped")
        time.sleep(0.1)


if __name__ == "__main__":
    main()
