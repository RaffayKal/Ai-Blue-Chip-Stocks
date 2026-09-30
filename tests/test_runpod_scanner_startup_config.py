#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")


class RunpodScannerStartupConfigTests(unittest.TestCase):
    def test_runtime_connection_targets_current_pod_and_accepted_bridge_key(self):
        config = (ROOT / "runpod_vllm_cpu_006.json").read_text(encoding="utf-8")
        self.assertIn('"t3yz4nrfl1utcr-644117fc@ssh.runpod.io"', config)
        self.assertIn('"/Users/raffaykal/runpod_codex_bridge"', config)
        self.assertIn('"--max-num-seqs", "7"', config)
        report = (ROOT / "scripts" / "report_runpod_runtime.sh").read_text(encoding="utf-8")
        self.assertIn('t3yz4nrfl1utcr-644117fc@ssh.runpod.io', report)
        self.assertNotIn('e7iwfvficlyk6w-644117fc@ssh.runpod.io', report)

    def test_runtime_report_reads_the_deployed_workspace(self):
        report = (ROOT / "scripts" / "report_runpod_runtime.sh").read_text(encoding="utf-8")
        self.assertIn('ROOT=/workspace/apex', report)

    def test_vllm_secret_source_is_keychain_not_project_env(self):
        config = (ROOT / "runpod_vllm_cpu_006.json").read_text(encoding="utf-8")
        self.assertIn("macOS Keychain service AI BLUE CHIP STOCKS RunPod VLLM API Key", config)
        self.assertNotIn('"VLLM_API_KEY": "read from ignored .env.local"', config)
        checker = (ROOT / "scripts" / "check_vllm_service.py").read_text(encoding="utf-8")
        self.assertIn('KEYCHAIN_SERVICE = "AI BLUE CHIP STOCKS RunPod VLLM API Key"', checker)

    def test_runpod_defaults_to_high_cpu_utilization_fanout(self):
        startup = (ROOT / "scripts" / "start_runpod_scanner_24_7.sh").read_text(encoding="utf-8")
        self.assertIn('export RUNPOD_SCANNER_LANES="${RUNPOD_SCANNER_LANES:-auto}"', startup)
        self.assertIn('RUNPOD_SAFE_MEDIUM_WEIGHT_LANES:-70', startup)
        self.assertIn('RUNPOD_MAX_MEDIUM_WEIGHT_LANES:-70', startup)

        fleet = (ROOT / "scripts" / "start_lightweight_scanner_fleet.sh").read_text(encoding="utf-8")
        self.assertIn('RUNPOD_MIN_LIGHTWEIGHT_LANES:-70', fleet)
        self.assertIn('RUNPOD_MAX_LIGHTWEIGHT_LANES:-70', fleet)
        self.assertIn('RESOURCE_CPU_TARGET_PERCENT: 97-100', fleet)
        plist = (ROOT / "com.raffaykal.apex-prestige-runpod-scanner.plist").read_text(encoding="utf-8")
        self.assertIn('<key>RUNPOD_MAX_MEDIUM_WEIGHT_LANES</key>\n    <string>70</string>', plist)

    def test_fleet_startup_surfaces_a_visible_scanning_proof_heartbeat(self):
        # The pool's own per-lane output is redirected to a log file so 700
        # lanes don't flood the container log; without a separate visible
        # heartbeat there is nothing in the container log proving the
        # scanner is actively deciding anything, only infra-level price
        # ticks that look identical whether or not scanning is happening.
        fleet = (ROOT / "scripts" / "start_lightweight_scanner_fleet.sh").read_text(encoding="utf-8")
        self.assertIn("SCANNING_PROOF:", fleet)
        self.assertIn("candidate_decision=", fleet)
        self.assertIn("scanner_viable=", fleet)
        self.assertIn("fleet_consensus=", fleet)


if __name__ == "__main__":
    unittest.main()
