import unittest

from experiments.product_lifecycle.native_sender_rebuild_parity_benchmark import (
    DEFAULT_REBUILD_MANIFEST,
    _protocol_signature,
    load_verified_source,
)


class NativeSenderRebuildParityBenchmarkTests(unittest.TestCase):
    def test_manifest_resolves_to_verified_git_source_and_workflow(self):
        manifest, source, workflow, identity = load_verified_source(
            DEFAULT_REBUILD_MANIFEST
        )

        self.assertTrue(identity["passed"])
        self.assertEqual(identity["tag_commit"], manifest["commit"])
        self.assertIn(b"static int write_all", source)
        self.assertIn(b"Build universal sender", workflow)

    def test_protocol_signature_excludes_diagnostic_fields(self):
        result = {
            "repetitions": 2,
            "exact_deliveries": 2,
            "silent_successes": 2,
            "missing_socket_exit": 1,
            "missing_socket_silent": True,
            "invalid_arguments_exit": 2,
            "invalid_arguments_silent": True,
            "passed": True,
            "diagnostic_only": "ignored",
        }
        signature = _protocol_signature(result)

        self.assertNotIn("diagnostic_only", signature)
        self.assertEqual(signature["missing_socket_exit"], 1)
        self.assertEqual(signature["invalid_arguments_exit"], 2)


if __name__ == "__main__":
    unittest.main()
