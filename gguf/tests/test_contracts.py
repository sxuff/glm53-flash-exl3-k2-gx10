from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads((ROOT / "results" / "summary.json").read_text())
        cls.target = json.loads((ROOT / "manifests" / "target.json").read_text())
        cls.runtime = json.loads((ROOT / "manifests" / "runtime.json").read_text())

    def test_pinned_lineage(self) -> None:
        self.assertEqual(self.target["revision"], "2975ab414d30340466d8c51533c6e91f0cca64c1")
        self.assertEqual(self.runtime["commit"], "629b50552801912b3e2078f9799e4d77213197d7")
        patch = ROOT / self.runtime["patch"]
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), self.runtime["patch_sha256"])

    def test_artifact_manifest(self) -> None:
        self.assertEqual(len(self.target["files"]), 5)
        self.assertEqual(sum(row["bytes"] for row in self.target["files"]), 103008962080)
        self.assertEqual(len({row["final_name"] for row in self.target["files"]}), 5)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in self.target["files"]))

    def test_speed_values(self) -> None:
        a = self.summary["arms"]["no-mtp"]
        b = self.summary["arms"]["mtp-n2"]
        self.assertAlmostEqual(a["mean_server_decode_tokens_per_second"], 18.40163204148179, places=12)
        self.assertAlmostEqual(b["mean_server_decode_tokens_per_second"], 27.66900143012806, places=12)
        self.assertAlmostEqual(
            b["mean_server_decode_tokens_per_second"] / a["mean_server_decode_tokens_per_second"],
            self.summary["comparison"]["mean_server_decode_ratio"],
            places=12,
        )
        self.assertAlmostEqual(self.summary["comparison"]["mean_server_decode_increase_percent"], 50.361671006981055, places=12)

    def test_whole_request_values(self) -> None:
        a = self.summary["arms"]["no-mtp"]
        b = self.summary["arms"]["mtp-n2"]
        self.assertAlmostEqual(a["measured_completion_tokens"] / a["summed_wall_seconds"], a["aggregate_whole_request_tokens_per_second"], places=12)
        self.assertAlmostEqual(b["measured_completion_tokens"] / b["summed_wall_seconds"], b["aggregate_whole_request_tokens_per_second"], places=12)

    def test_acceptance(self) -> None:
        acceptance = self.summary["arms"]["mtp-n2"]["acceptance"]
        self.assertEqual(acceptance["proposed_draft_tokens"], 2650)
        self.assertEqual(acceptance["accepted_draft_tokens"], 1865)
        self.assertAlmostEqual(1865 / 2650, acceptance["rate"], places=12)

    def test_safety(self) -> None:
        for arm in self.summary["arms"].values():
            self.assertGreater(arm["minimum_mem_available_bytes"], 6 * 1024**3)
            self.assertEqual(arm["maximum_host_swap_growth_bytes"], 0)
            self.assertEqual(arm["maximum_service_swap_bytes"], 0)

    def test_default_mode(self) -> None:
        serve = (ROOT / "scripts" / "serve.sh").read_text()
        self.assertIn('MODE="${MODE:-mtp}"', serve)
        self.assertIn("--spec-type draft-mtp", serve)
        self.assertIn("--spec-draft-n-max 2", serve)
        self.assertIn("--spec-draft-n-min 0", serve)


if __name__ == "__main__":
    unittest.main()
