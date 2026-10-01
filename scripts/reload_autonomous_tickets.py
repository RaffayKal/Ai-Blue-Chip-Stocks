#!/usr/bin/env python3
import json
import re
from pathlib import Path

from project_root import ROOT
DATA = ROOT / 'data'
LOG = DATA / 'autonomous_execution_log.json'
ALGORITHM_ID = 'APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING'
BUY_ACTIVE = DATA / 'autonomous_crypto_market_buy_auto_max_active.json'
SELL_ACTIVE = DATA / 'autonomous_crypto_market_sell_position_auto_active.json'
CANDIDATES = DATA / 'volatile_crypto_candidates.json'


def load_json(path):
    with path.open() as f:
        return json.load(f)


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2) + '\n')


def execution_counts():
    payload = load_json(LOG)
    executions = payload.get('executions', [])
    if not isinstance(executions, list):
        raise SystemExit('BLOCKED: execution log must contain executions list')
    counts = {}
    for item in executions:
        if not isinstance(item, dict):
            continue
        ticket_id = item.get('ticket_id')
        if isinstance(ticket_id, str) and ticket_id:
            counts[ticket_id] = counts.get(ticket_id, 0) + 1
    return counts


def active_crypto_symbol():
    payload = load_json(CANDIDATES)
    symbol = str(payload.get('active_symbol') or '').strip().upper()
    if not symbol:
        symbol = str(payload.get('fallback_symbol') or '').strip().upper()
    if not symbol:
        raise SystemExit('BLOCKED: no active crypto symbol selected')
    return symbol


def next_sequence(prefix, used_ids):
    highest = 0
    pattern = re.compile(rf'^{re.escape(prefix)}_(\d+)$')
    for ticket_id in used_ids:
        if not isinstance(ticket_id, str):
            continue
        match = pattern.match(ticket_id)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def ticket_exhausted(path, counts):
    if not path.exists():
        return True
    ticket = load_json(path)
    ticket_id = ticket.get('ticket_id')
    max_executions = ticket.get('max_executions')
    if ticket.get('user_algorithm_id') != ALGORITHM_ID:
        return True
    if max_executions != 7:
        return True
    if not isinstance(ticket_id, str) or not ticket_id:
        return True
    return counts.get(ticket_id, 0) >= max_executions


def refresh_active_symbol(path, counts):
    """Keep the reusable active ticket bound to the scanner's current symbol.

    The active symbol rotates continuously.  Leaving a prior symbol in the
    ticket creates a deterministic handoff mismatch even when the fresh
    envelope is otherwise executable.  Preserve the ticket id and its
    idempotency history; only refresh the symbol when the current ticket is
    still within its existing execution limit.
    """
    if not path.exists():
        return False
    ticket = load_json(path)
    ticket_id = ticket.get('ticket_id')
    if not isinstance(ticket_id, str) or counts.get(ticket_id, 0) >= int(ticket.get('max_executions', 0) or 0):
        return False
    symbol = active_crypto_symbol()
    if ticket.get('symbol') == symbol:
        return False
    ticket['symbol'] = symbol
    write_json(path, ticket)
    return True


def buy_ticket(seq):
    return {
        'autonomous_execution': True,
        'user_algorithm_id': ALGORITHM_ID,
        'symbol': active_crypto_symbol(),
        'asset_class': 'CRYPTO',
        'venue': 'Robinhood Crypto',
        'side': 'buy',
        'type': 'market',
        'dollar_amount_mode': 'AUTO_MAX_ALLOWED',
        'min_dollar_amount': '1.00',
        'max_dollar_amount': '1000000000.00',
        'requires_preview': True,
        'requires_algorithm_result': 'VALIDATED SETUP',
        'ticket_id': f'crypto_market_buy_auto_max_{seq:06d}',
        'max_executions': 7,
        'reload_mode': 'UNLIMITED_7_SHOT_RELOAD'
    }


def sell_ticket(seq):
    return {
        'autonomous_execution': True,
        'user_algorithm_id': ALGORITHM_ID,
        'symbol': active_crypto_symbol(),
        'asset_class': 'CRYPTO',
        'venue': 'Robinhood Crypto',
        'side': 'sell',
        'type': 'market',
        'quantity_mode': 'AUTO_SELLABLE_POSITION',
        'min_quantity': '0.00000001',
        'requires_preview': True,
        'requires_algorithm_result': 'VALIDATED SETUP',
        'ticket_id': f'crypto_market_sell_position_auto_{seq:06d}',
        'max_executions': 7,
        'reload_mode': 'UNLIMITED_7_SHOT_RELOAD'
    }


def main():
    if Path.cwd() != ROOT:
        raise SystemExit('BLOCKED: command is not running inside AI BLUE CHIP STOCKS')
    counts = execution_counts()
    used = set(counts)
    changed = []
    if ticket_exhausted(BUY_ACTIVE, counts):
        seq = next_sequence('crypto_market_buy_auto_max', used)
        while f'crypto_market_buy_auto_max_{seq:06d}' in used:
            seq += 1
        write_json(BUY_ACTIVE, buy_ticket(seq))
        changed.append(f'BUY={BUY_ACTIVE.name}:crypto_market_buy_auto_max_{seq:06d}')
    elif refresh_active_symbol(BUY_ACTIVE, counts):
        changed.append(f'BUY={BUY_ACTIVE.name}:symbol_refreshed')
    if ticket_exhausted(SELL_ACTIVE, counts):
        seq = next_sequence('crypto_market_sell_position_auto', used)
        while f'crypto_market_sell_position_auto_{seq:06d}' in used:
            seq += 1
        write_json(SELL_ACTIVE, sell_ticket(seq))
        changed.append(f'SELL={SELL_ACTIVE.name}:crypto_market_sell_position_auto_{seq:06d}')
    elif refresh_active_symbol(SELL_ACTIVE, counts):
        changed.append(f'SELL={SELL_ACTIVE.name}:symbol_refreshed')
    if changed:
        print('AUTONOMOUS_TICKET_RELOAD: UPDATED')
        for item in changed:
            print(item)
    else:
        print('AUTONOMOUS_TICKET_RELOAD: CURRENT')


if __name__ == '__main__':
    main()
