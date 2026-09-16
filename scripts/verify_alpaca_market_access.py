#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

from alpaca.data.enums import DataFeed
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest
from alpaca.trading.client import TradingClient

from project_root import ROOT

STATUS = ROOT / "data" / "alpaca_market_access_status.json"
BLUE_CHIP_WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"
EXPANSION_WATCHLIST = ROOT / "data" / "apex_expansion_watchlist.txt"


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def read_symbols(path, limit):
    symbols = []
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            symbol = raw.strip().upper()
            if symbol and not symbol.startswith("#"):
                symbols.append(symbol)
    return symbols[:limit]


def quote_payload(quote):
    raw = quote.model_dump(mode="json") if hasattr(quote, "model_dump") else {}
    bid = raw.get("bid_price") or raw.get("bp")
    ask = raw.get("ask_price") or raw.get("ap")
    bid_size = raw.get("bid_size") or raw.get("bs")
    ask_size = raw.get("ask_size") or raw.get("as")
    timestamp = raw.get("timestamp") or raw.get("t")
    return {
        "bid": bid,
        "ask": ask,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "timestamp": timestamp,
        "has_bid_ask": bid is not None and ask is not None,
        "raw": raw,
    }


def collect_quotes(client, request, label):
    try:
        response = client.get_stock_latest_quote(request) if label != "crypto" else client.get_crypto_latest_quote(request)
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc), "quotes": {}}
    quotes = {}
    for symbol, quote in dict(response).items():
        quotes[symbol] = quote_payload(quote)
    return {
        "status": "OK",
        "quote_count": len(quotes),
        "fresh_bid_ask_count": sum(1 for item in quotes.values() if item["has_bid_ask"]),
        "quotes": quotes,
    }


def env_credential(primary, *aliases):
    for name in (primary, *aliases):
        value = os.getenv(name)
        if value:
            return value
    return None


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    parser = argparse.ArgumentParser(description="Verify Alpaca account and market-data access without order mutation.")
    parser.add_argument("--stock-feed", default=os.getenv("ALPACA_STOCK_FEED", "iex"), choices=["iex", "sip"])
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    if certifi is not None:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    api_key = env_credential("ALPACA_API_KEY_ID", "APCA_API_KEY_ID", "ALPACA_API_KEY")
    secret_key = env_credential("ALPACA_API_SECRET_KEY", "APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise SystemExit("BLOCKED: ALPACA_API_KEY_ID/APCA_API_KEY_ID and ALPACA_API_SECRET_KEY/APCA_API_SECRET_KEY are required.")

    feed = DataFeed.SIP if args.stock_feed == "sip" else DataFeed.IEX
    blue_chips = read_symbols(BLUE_CHIP_WATCHLIST, args.limit)
    expansion = read_symbols(EXPANSION_WATCHLIST, args.limit)
    crypto = ["BTC/USD", "ETH/USD"]

    stock_client = StockHistoricalDataClient(api_key, secret_key)
    crypto_client = CryptoHistoricalDataClient(api_key, secret_key)
    trading_client = TradingClient(api_key, secret_key, paper=True)

    try:
        account = trading_client.get_account()
        account_raw = account.model_dump(mode="json") if hasattr(account, "model_dump") else {}
        account_status = {
            "status": account_raw.get("status"),
            "crypto_status": account_raw.get("crypto_status"),
            "trading_blocked": account_raw.get("trading_blocked"),
            "account_blocked": account_raw.get("account_blocked"),
            "pattern_day_trader": account_raw.get("pattern_day_trader"),
            "buying_power": account_raw.get("buying_power"),
            "cash": account_raw.get("cash"),
        }
    except Exception as exc:
        account_status = {"status": "ERROR", "error": str(exc)}

    result = {
        "timestamp_utc": iso_now(),
        "alpaca_paper_trading_client_checked": True,
        "order_preview_called": False,
        "order_placement_called": False,
        "trade_execution_allowed": False,
        "stock_feed": args.stock_feed,
        "account": account_status,
        "blue_chip_quotes": collect_quotes(
            stock_client,
            StockLatestQuoteRequest(symbol_or_symbols=blue_chips, feed=feed),
            "stock",
        ) if blue_chips else {"status": "NO_SYMBOLS", "quotes": {}},
        "apex_expansion_quotes": collect_quotes(
            stock_client,
            StockLatestQuoteRequest(symbol_or_symbols=expansion, feed=feed),
            "stock",
        ) if expansion else {"status": "NO_SYMBOLS", "quotes": {}},
        "crypto_quotes": collect_quotes(
            crypto_client,
            CryptoLatestQuoteRequest(symbol_or_symbols=crypto),
            "crypto",
        ),
    }
    write_json(STATUS, result)

    print(f"ALPACA_MARKET_ACCESS_STATUS: {STATUS}")
    print(f"ACCOUNT_STATUS: {account_status.get('status')}")
    print(f"BLUE_CHIP_QUOTES: {result['blue_chip_quotes'].get('status')} {result['blue_chip_quotes'].get('fresh_bid_ask_count')}")
    print(f"APEX_EXPANSION_QUOTES: {result['apex_expansion_quotes'].get('status')} {result['apex_expansion_quotes'].get('fresh_bid_ask_count')}")
    print(f"CRYPTO_QUOTES: {result['crypto_quotes'].get('status')} {result['crypto_quotes'].get('fresh_bid_ask_count')}")
    print("ORDER_PREVIEW_CALLED: false")
    print("ORDER_PLACEMENT_CALLED: false")


if __name__ == "__main__":
    main()
