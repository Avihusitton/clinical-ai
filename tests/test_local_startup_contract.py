# -*- coding: utf-8 -*-
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LocalStartupContractTests(unittest.TestCase):
    def test_launcher_starts_only_local_qa_and_local_neo4j(self):
        launcher = (ROOT / "start_local_system.ps1").read_text(encoding="utf-8")

        self.assertIn("local_qa_app.py", launcher)
        self.assertIn("'console'", launcher)
        self.assertIn("CreateNoWindow = $true", launcher)
        self.assertNotIn("Start-Process", launcher)
        self.assertIn("UseShellExecute = $true", launcher)
        self.assertNotIn("EnvironmentVariables", launcher)
        self.assertIn("127.0.0.1", launcher)
        self.assertIn("NEO4J_PASSWORD", launcher)
        self.assertNotIn("OPENROUTER", launcher.upper())

    def test_launcher_persists_exact_process_ids_and_runtime_status(self):
        launcher = (ROOT / "start_local_system.ps1").read_text(encoding="utf-8")

        self.assertIn("neo4j-relate.pid", launcher)
        self.assertIn("local_qa.pid", launcher)
        self.assertIn("runtime_status.json", launcher)


if __name__ == "__main__":
    unittest.main()
