"""Cloudflare Python Worker: read-only, notify-only crypto quote check.

Fires on a Cloudflare cron trigger. Pulls a live BTC/USD quote directly from
Alpaca's public market-data REST API, checks it against a spread threshold,
and POSTs a summary to a webhook if it looks interesting. It never places an
order and never touches Robinhood or this repo's local capital_engine gate
(those only exist on the operator's machine, not reachable from Cloudflare).

Required secrets (set via `wrangler secret put <NAME>`):
  ALPACA_API_KEY_ID
  ALPACA_API_SECRET_KEY
  NOTIFY_WEBHOOK_URL   -- any endpoint that accepts a JSON POST (e.g. a
                          Slack incoming webhook, ntfy.sh topic URL, etc.)

Optional config (via wrangler.toml [vars]):
  SPREAD_BPS_THRESHOLD -- max allowed (ask-bid)/mid in basis points before
                          this is considered "worth a look" (default 50)
"""
from workers import WorkerEntrypoint, fetch

SYMBOL = "BTC/USD"
QUOTE_URL = f"https://data.alpaca.markets/v1beta3/crypto/us/latest/quotes?symbols={SYMBOL}"


class Default(WorkerEntrypoint):
    async def scheduled(self, controller, env, ctx):
        api_key = getattr(env, "ALPACA_API_KEY_ID", None)
        api_secret = getattr(env, "ALPACA_API_SECRET_KEY", None)
        webhook_url = getattr(env, "NOTIFY_WEBHOOK_URL", None)
        threshold_bps = float(getattr(env, "SPREAD_BPS_THRESHOLD", "50"))

        if not api_key or not api_secret:
            print("SKIPPED: missing ALPACA_API_KEY_ID/ALPACA_API_SECRET_KEY secret")
            return

        response = await fetch(
            QUOTE_URL,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            },
        )
        if response.status != 200:
            print(f"ALPACA_QUOTE_ERROR: status={response.status}")
            return

        payload = await response.json()
        quote = (payload.get("quotes") or {}).get(SYMBOL)
        if not quote:
            print("NO_QUOTE_RETURNED")
            return

        bid = quote.get("bp")
        ask = quote.get("ap")
        if not bid or not ask or bid <= 0 or ask <= 0:
            print("MISSING_BID_ASK")
            return

        mid = (bid + ask) / 2
        spread_bps = (ask - bid) / mid * 10000

        print(f"QUOTE_CHECK symbol={SYMBOL} bid={bid} ask={ask} spread_bps={spread_bps:.2f}")

        if spread_bps > threshold_bps:
            print("SPREAD_TOO_WIDE_NO_NOTIFY")
            return

        if not webhook_url:
            print("VIABLE_BUT_NO_WEBHOOK_CONFIGURED")
            return

        message = (
            f"[Alpaca cron check] {SYMBOL} bid={bid} ask={ask} "
            f"spread_bps={spread_bps:.1f} -- this is a data signal only, "
            "not a trade. Review manually before any action."
        )
        await fetch(
            webhook_url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"text": message},
        )
        print("NOTIFIED")
