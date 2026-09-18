"""Fixed-point APEX micro-spot ledger and fail-closed sizing helpers."""
from decimal import Decimal, ROUND_DOWN

ATOMIC_UNIT = 0.00000007
Q = Decimal("0.00000007")


def _d(value):
    return Decimal(str(value))


def ledger_units(amount):
    return int((_d(amount) / Q).to_integral_value(rounding=ROUND_DOWN))


def deployable_aum(settled_cash, realized_pnl, fees_and_slippage, tax_reserve, protected_reserve):
    retained = max(_d(realized_pnl) - _d(fees_and_slippage), Decimal("0"))
    return float(max(_d(settled_cash) + retained - _d(tax_reserve) - _d(protected_reserve), Decimal("0")))


def is_executable(apex_viable, risk_gates_passed, source_freshness, deployable, broker_minimum):
    return bool(apex_viable and risk_gates_passed and source_freshness and _d(deployable) >= _d(broker_minimum))


def size_order(current_aum, risk_fraction, stop_distance_pct, deployable, position_cap,
               broker_minimum, expected_edge, expected_cost, projected_drawdown,
               drawdown_limit):
    stop = _d(stop_distance_pct)
    if stop <= 0:
        return None, "stop_distance_pct must be positive"
    if _d(expected_edge) <= _d(expected_cost):
        return None, "expected_edge does not exceed expected_cost"
    if _d(projected_drawdown) > _d(drawdown_limit):
        return None, "drawdown exceeds drawdown_limit"
    risk_cash = _d(current_aum) * _d(risk_fraction)
    notional = min(risk_cash / stop, _d(deployable), _d(position_cap))
    if notional < _d(broker_minimum):
        return None, "broker_minimum not met"
    return float(notional), None


def next_floor_above(current_aum):
    value = _d(current_aum)
    for floor in (Q, _d("0.07"), _d("0.70"), _d("7.00"), _d("25.00")):
        if value < floor:
            return float(floor)
    return float(value * 10)


def should_harvest(current_aum, unrealized_gain_pct, held_seconds, min_hold_seconds,
                   stop_loss_triggered, invalidation_triggered):
    if stop_loss_triggered or invalidation_triggered:
        return True, "stop_loss_or_invalidation_overrides_patience"
    if _d(held_seconds) < _d(min_hold_seconds):
        return False, "min_hold_seconds_not_met"
    target = (_d(next_floor_above(current_aum)) / _d(current_aum)) - 1 if _d(current_aum) else Decimal("Infinity")
    if _d(unrealized_gain_pct) < target:
        return False, "next-floor_gain_requirement_not_met"
    return True, "hold_time_and_grow_target_met"


def apply_closed_trade(current_aum, sale_proceeds, cost_basis, fees, slippage,
                       tax_allocation, protected_floor, reserve_fraction):
    net = _d(sale_proceeds) - _d(cost_basis) - _d(fees) - _d(slippage) - _d(tax_allocation)
    new_aum = _d(current_aum) + net
    floor = _d(protected_floor)
    candidate = _d(next_floor_above(current_aum))
    locked = Decimal("0")
    if net > 0 and new_aum >= candidate:
        floor = candidate
        locked = net * _d(reserve_fraction)
    return float(new_aum), float(floor), float(locked)


def evaluate(payload):
    required = ("current_aum", "settled_cash", "realized_pnl", "fees_and_slippage",
                "tax_reserve", "protected_reserve", "broker_minimum", "stop_distance_pct",
                "apex_viable", "source_freshness", "risk_gates_passed", "risk_fraction",
                "position_cap", "expected_edge", "expected_cost", "projected_drawdown",
                "drawdown_limit")
    failed = [key for key in required if key not in payload or payload.get(key) is None]
    if failed:
        return {"RESULT": "NO ACTION", "FAILED_CHECKS": failed}
    deployable = deployable_aum(payload["settled_cash"], payload["realized_pnl"], payload["fees_and_slippage"], payload["tax_reserve"], payload["protected_reserve"])
    notional, rejection = size_order(payload["current_aum"], payload["risk_fraction"], payload["stop_distance_pct"], deployable, payload["position_cap"], payload["broker_minimum"], payload["expected_edge"], payload["expected_cost"], payload["projected_drawdown"], payload["drawdown_limit"])
    if rejection or not is_executable(payload["apex_viable"], payload["risk_gates_passed"], payload["source_freshness"], deployable, payload["broker_minimum"]):
        checks = [rejection] if rejection else ["APEX viability or freshness/risk gate failed"]
        return {"RESULT": "NO ACTION", "FAILED_CHECKS": checks, "DEPLOYABLE_AUM": deployable}
    return {"RESULT": "SIZED CANDIDATE", "ORDER_NOTIONAL": notional, "DEPLOYABLE_AUM": deployable, "FAILED_CHECKS": []}
