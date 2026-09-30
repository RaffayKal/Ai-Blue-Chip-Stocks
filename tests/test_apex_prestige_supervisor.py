#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apex_prestige_supervisor as supervisor


class ApexPrestigeSupervisorTests(unittest.TestCase):
    def test_successful_scan_checks_packet_handoff_each_cycle(self):
        calls = []
        statuses = []

        def run(command):
            calls.append(command)
            if len(calls) == 1:
                return 0, "SYSTEM_STATE: ACTIVE\n"
            if len(calls) == 2:
                return 0, "SCANNER: updated\n"
            return 0, "APEX_PACKET_MONITOR: viable_false\n"

        with patch.object(supervisor, "run_command", side_effect=run), patch.object(
            supervisor, "write_json", side_effect=lambda _path, data: statuses.append(data)
        ), patch.object(supervisor, "log"), patch.object(supervisor, "load_interval", return_value=4):
            supervisor.supervisor_once(Path("rules/apex_packet_monitor.template.json"))

        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][calls[1].index("--lane") + 1], "supervisor_health")
        self.assertEqual(calls[2][1:], ["algorithms/apex_packet_monitor.py", "--config", "rules/apex_packet_monitor.template.json", "--once"])
        self.assertTrue(statuses[0]["packet_monitor_checked"])
        self.assertEqual(statuses[0]["last_monitor_exit"], 0)

    def test_failed_scan_does_not_emit_from_old_envelope(self):
        calls = []
        statuses = []

        def run(command):
            calls.append(command)
            return (0, "SYSTEM_STATE: ACTIVE\n") if len(calls) == 1 else (1, "SCANNER: failed\n")

        with patch.object(supervisor, "run_command", side_effect=run), patch.object(
            supervisor, "write_json", side_effect=lambda _path, data: statuses.append(data)
        ), patch.object(supervisor, "log"), patch.object(supervisor, "load_interval", return_value=4):
            supervisor.supervisor_once(Path("rules/apex_packet_monitor.template.json"))

        self.assertEqual(len(calls), 2)
        self.assertFalse(statuses[0]["packet_monitor_checked"])
        self.assertIsNone(statuses[0]["last_monitor_exit"])

    def test_frozen_health_scan_cannot_overwrite_primary_envelope(self):
        calls = []

        def run(command):
            calls.append(command)
            return (0, "SYSTEM_STATE: FROZEN\n") if len(calls) == 1 else (0, "SCANNER: updated\n")

        with patch.object(supervisor, "run_command", side_effect=run), patch.object(
            supervisor, "write_json"
        ), patch.object(supervisor, "log"):
            supervisor.supervisor_once(Path("rules/apex_packet_monitor.template.json"))

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][calls[1].index("--lane") + 1], "supervisor_health")
        self.assertEqual(calls[1][calls[1].index("--codex-heavy-state") + 1], "FROZEN")


if __name__ == "__main__":
    unittest.main()
