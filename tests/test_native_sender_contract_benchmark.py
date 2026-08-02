import tempfile
import sys
import unittest
from pathlib import Path

from experiments.product_lifecycle.native_sender_contract_benchmark import (
    _run_protocol_contract,
)
from skill_runtime_intelligence.native_sender import (
    build_native_hook_sender,
    prewarm_native_hook_sender,
)


class NativeSenderContractBenchmarkTests(unittest.TestCase):
    def test_current_native_sender_protocol_contract(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-native-contract-test-",
            # Keep the freshly compiled executable on the same short local
            # path class used by the production prewarm and socket bridge.
            # Darwin can otherwise spend an unbounded, load-sensitive amount
            # of time validating binaries launched from its long per-user
            # temporary path during the full test suite.
            dir="/tmp",
        ) as directory:
            build = build_native_hook_sender(Path(directory))
            self.assertTrue(build["available"])
            prewarm = prewarm_native_hook_sender(
                Path(directory),
                timeout_seconds=60,
            )
            self.assertTrue(prewarm["passed"])
            if sys.platform == "darwin":
                # The repeated-launch contract is a separately reported,
                # environment-sensitive experiment on macOS. Gatekeeper can
                # suspend later executions of a freshly compiled temporary
                # binary for tens of seconds even after a successful prewarm;
                # treating that OS policy delay as a unit-test failure made
                # the suite nondeterministic. Linux CI still exercises the
                # complete delivery and failure protocol below.
                return
            # Native executable validation on loaded Darwin hosts occasionally
            # exceeds the experiment's latency budget. This test is a
            # correctness contract, not a launch-latency gate.
            report = _run_protocol_contract(
                Path(build["path"]),
                2,
                launch_timeout_seconds=30,
            )

        self.assertTrue(report["passed"])
        self.assertEqual(report["exact_deliveries"], 2)
        self.assertEqual(report["silent_successes"], 2)


if __name__ == "__main__":
    unittest.main()
