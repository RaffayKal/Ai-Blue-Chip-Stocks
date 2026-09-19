#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "algorithms"))

import apex_micro_crypto_ledger as ledger


class LedgerUnitsTests(unittest.TestCase):
    def test_atomic_unit_matches_denomination_table(self):
        self.assertEqual(ledger.ATOMIC_UNIT, 0.00000007)

    def test_ledger_units_floors_and_matches_table_rows(self):
        self.assertEqual(ledger.ledger_units(0.00000007), 1)
        self.assertEqual(ledger.ledger_units(0.00000070), 10)
        self.assertEqual(ledger.ledger_units(7.00000000), 100_000_000)

    def test_ledger_units_never_rounds_up(self):
        # Just under one grain must not be credited as a full grain.
        self.assertEqual(ledger.ledger_units(0.00000069), 9)

    def test_aum_row_matches_table_within_rounding(self):
        units = ledger.ledger_units(25.00000000)
        self.assertEqual(units, 357142857)


class DeployableAumTests(unittest.TestCase):
    def test_deployable_aum_excludes_negative_realized_pnl(self):
        result = ledger.deployable_aum(
            settled_cash=10.0, realized_pnl=-5.0, fees_and_slippage=0.0,
            tax_reserve=0.0, protected_reserve=0.0,
        )
        # A realized loss must not reduce settled_cash below itself here --
        # max(net_realized, 0) means losses don't get deployed as "gains".
        self.assertEqual(result, 10.0)

    def test_deployable_aum_subtracts_reserves(self):
        result = ledger.deployable_aum(
            settled_cash=10.0, realized_pnl=5.0, fees_and_slippage=1.0,
            tax_reserve=1.0, protected_reserve=2.0,
        )
        self.assertAlmostEqual(result, 10.0 + 4.0 - 1.0 - 2.0)


class ExecutableGateTests(unittest.TestCase):
    def test_all_true_and_sufficient_deployable_is_executable(self):
        self.assertTrue(ledger.is_executable(True, True, True, deployable=5.0, broker_minimum=1.0))

    def test_any_false_flag_blocks(self):
        self.assertFalse(ledger.is_executable(False, True, True, deployable=5.0, broker_minimum=1.0))
        self.assertFalse(ledger.is_executable(True, False, True, deployable=5.0, broker_minimum=1.0))
        self.assertFalse(ledger.is_executable(True, True, False, deployable=5.0, broker_minimum=1.0))

    def test_deployable_below_broker_minimum_blocks(self):
        self.assertFalse(ledger.is_executable(True, True, True, deployable=0.5, broker_minimum=1.0))


class SizeOrderTests(unittest.TestCase):
    def test_caps_at_deployable_and_position_cap(self):
        notional, rejection = ledger.size_order(
            current_aum=100.0, risk_fraction=0.5, stop_distance_pct=0.01,
            deployable=10.0, position_cap=1000.0, broker_minimum=1.0,
            expected_edge=1.0, expected_cost=0.1,
            projected_drawdown=0.05, drawdown_limit=0.5,
        )
        # candidate_notional = 50/0.01 = 5000, capped to deployable=10
        self.assertIsNone(rejection)
        self.assertEqual(notional, 10.0)

    def test_rejects_below_broker_minimum(self):
        notional, rejection = ledger.size_order(
            current_aum=1.0, risk_fraction=0.1, stop_distance_pct=1.0,
            deployable=10.0, position_cap=1000.0, broker_minimum=5.0,
            expected_edge=1.0, expected_cost=0.1,
            projected_drawdown=0.05, drawdown_limit=0.5,
        )
        self.assertIsNone(notional)
        self.assertIn("broker_minimum", rejection)

    def test_rejects_when_edge_does_not_exceed_cost(self):
        notional, rejection = ledger.size_order(
            current_aum=100.0, risk_fraction=0.5, stop_distance_pct=0.01,
            deployable=10.0, position_cap=1000.0, broker_minimum=1.0,
            expected_edge=0.05, expected_cost=0.1,
            projected_drawdown=0.05, drawdown_limit=0.5,
        )
        self.assertIsNone(notional)
        self.assertIn("expected_edge", rejection)

    def test_rejects_when_drawdown_exceeds_limit(self):
        notional, rejection = ledger.size_order(
            current_aum=100.0, risk_fraction=0.5, stop_distance_pct=0.01,
            deployable=10.0, position_cap=1000.0, broker_minimum=1.0,
            expected_edge=1.0, expected_cost=0.1,
            projected_drawdown=0.9, drawdown_limit=0.5,
        )
        self.assertIsNone(notional)
        self.assertIn("drawdown", rejection)

    def test_rejects_invalid_stop_distance(self):
        notional, rejection = ledger.size_order(
            current_aum=100.0, risk_fraction=0.5, stop_distance_pct=0.0,
            deployable=10.0, position_cap=1000.0, broker_minimum=1.0,
            expected_edge=1.0, expected_cost=0.1,
            projected_drawdown=0.05, drawdown_limit=0.5,
        )
        self.assertIsNone(notional)
        self.assertIn("stop_distance_pct", rejection)


class FloorLadderTests(unittest.TestCase):
    def test_next_floor_above_named_tiers(self):
        self.assertAlmostEqual(ledger.next_floor_above(0.0), ledger.ATOMIC_UNIT)
        self.assertAlmostEqual(ledger.next_floor_above(7.0), 25.0)

    def test_next_floor_above_extends_past_named_ladder(self):
        # Past $25 (AUM), the ladder keeps multiplying by 10 indefinitely.
        self.assertAlmostEqual(ledger.next_floor_above(25.0), 250.0)
        self.assertAlmostEqual(ledger.next_floor_above(250.0), 2500.0)


class ShouldHarvestTests(unittest.TestCase):
    def test_stop_loss_overrides_patience(self):
        harvest, reason = ledger.should_harvest(
            current_aum=1.0, unrealized_gain_pct=0.0, held_seconds=0.0,
            min_hold_seconds=3600.0, stop_loss_triggered=True,
            invalidation_triggered=False,
        )
        self.assertTrue(harvest)
        self.assertEqual(reason, "stop_loss_or_invalidation_overrides_patience")

    def test_invalidation_overrides_patience(self):
        harvest, reason = ledger.should_harvest(
            current_aum=1.0, unrealized_gain_pct=0.0, held_seconds=0.0,
            min_hold_seconds=3600.0, stop_loss_triggered=False,
            invalidation_triggered=True,
        )
        self.assertTrue(harvest)

    def test_blocks_before_min_hold_seconds(self):
        harvest, reason = ledger.should_harvest(
            current_aum=1.0, unrealized_gain_pct=1.0, held_seconds=10.0,
            min_hold_seconds=3600.0, stop_loss_triggered=False,
            invalidation_triggered=False,
        )
        self.assertFalse(harvest)
        self.assertIn("min_hold_seconds", reason)

    def test_blocks_when_gain_below_next_floor_requirement(self):
        # current_aum=0.05 -> next floor is 0.07, requiring +40% gain.
        harvest, reason = ledger.should_harvest(
            current_aum=0.05, unrealized_gain_pct=0.10, held_seconds=99999.0,
            min_hold_seconds=3600.0, stop_loss_triggered=False,
            invalidation_triggered=False,
        )
        self.assertFalse(harvest)
        self.assertIn("next-floor", reason)

    def test_harvests_once_hold_time_and_floor_target_are_met(self):
        harvest, reason = ledger.should_harvest(
            current_aum=0.05, unrealized_gain_pct=0.5, held_seconds=99999.0,
            min_hold_seconds=3600.0, stop_loss_triggered=False,
            invalidation_triggered=False,
        )
        self.assertTrue(harvest)
        self.assertEqual(reason, "hold_time_and_grow_target_met")


class ClosedTradeTests(unittest.TestCase):
    def test_aum_updates_by_net_trade_pnl(self):
        new_aum, new_floor, locked = ledger.apply_closed_trade(
            current_aum=5.0, sale_proceeds=6.0, cost_basis=5.0,
            fees=0.1, slippage=0.05, tax_allocation=0.05,
            protected_floor=0.0, reserve_fraction=0.5,
        )
        self.assertAlmostEqual(new_aum, 5.0 + (6.0 - 5.0 - 0.1 - 0.05 - 0.05))

    def test_crossing_a_floor_locks_reserve_and_raises_floor(self):
        # current_aum=0.05 is below the $0.07 Floor tier; a big trade pushes
        # new_current_aum past it, which must lock reserve and raise the floor.
        new_aum, new_floor, locked = ledger.apply_closed_trade(
            current_aum=0.05, sale_proceeds=1.0, cost_basis=0.0,
            fees=0.0, slippage=0.0, tax_allocation=0.0,
            protected_floor=0.0, reserve_fraction=0.5,
        )
        self.assertGreaterEqual(new_aum, 0.07)
        self.assertAlmostEqual(new_floor, 0.07)
        self.assertGreater(locked, 0.0)

    def test_not_crossing_a_floor_locks_nothing(self):
        new_aum, new_floor, locked = ledger.apply_closed_trade(
            current_aum=0.01, sale_proceeds=0.02, cost_basis=0.01,
            fees=0.0, slippage=0.0, tax_allocation=0.0,
            protected_floor=0.0, reserve_fraction=0.5,
        )
        self.assertEqual(locked, 0.0)
        self.assertEqual(new_floor, 0.0)


class EvaluateIntegrationTests(unittest.TestCase):
    def base_payload(self):
        return {
            "current_aum": 25.0,
            "settled_cash": 20.0,
            "realized_pnl": 5.0,
            "unrealized_pnl": 0.0,
            "fees_and_slippage": 0.1,
            "tax_reserve": 1.0,
            "protected_reserve": 0.0,
            "broker_minimum": 1.0,
            "stop_distance_pct": 0.02,
            "apex_viable": True,
            "source_freshness": True,
            "risk_gates_passed": True,
            "risk_fraction": 0.1,
            "position_cap": 10.0,
            "expected_edge": 1.0,
            "expected_cost": 0.1,
            "projected_drawdown": 0.05,
            "drawdown_limit": 0.5,
        }

    def test_missing_field_returns_no_action(self):
        payload = self.base_payload()
        del payload["current_aum"]
        result = ledger.evaluate(payload)
        self.assertEqual(result["RESULT"], "NO ACTION")
        self.assertIn("current_aum", result["FAILED_CHECKS"])

    def test_gate_failure_returns_no_action(self):
        payload = self.base_payload()
        payload["apex_viable"] = False
        result = ledger.evaluate(payload)
        self.assertEqual(result["RESULT"], "NO ACTION")

    def test_valid_payload_sizes_a_candidate(self):
        result = ledger.evaluate(self.base_payload())
        self.assertEqual(result["RESULT"], "SIZED CANDIDATE")
        self.assertIsInstance(result["ORDER_NOTIONAL"], float)
        self.assertGreater(result["ORDER_NOTIONAL"], 0)


if __name__ == "__main__":
    unittest.main()
