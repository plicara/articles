"""Boundary tests for the published comparison and episode accounting."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import replay

class ReplayTests(unittest.TestCase):
    def test_common_population_thresholds_and_episode_resets(self):
        base = dict(label_v1="WRONG", label_v2="WRONG", boolean=.5,
                    peers=2, peer_disagree=1, exact=None, crossref=None,
                    focused=None, enriched=None)
        rows = [dict(base, task_id="tie"),
                dict(base, task_id="no-peer", peers=0, peer_disagree=0, boolean=.01),
                dict(base, task_id="ambiguous", label_v2="AMBIGUOUS", boolean=.01),
                dict(base, task_id="ok", label_v1="OK", label_v2="OK", boolean=.01)]
        tics = [dict(episode=1, kills=1, health=20, finished=False),
                dict(episode=1, kills=2, health=0, finished=True),
                dict(episode=2, kills=1, health=0, finished=False)]
        runs = [dict(run=arm, arm=arm, seed=1, tics=tics, tics_per_second=35)
                for arm in ("prose_v5", "grid_v3_control")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in (("extraction", rows), ("doom", runs)):
                (root / (name + ".jsonl")).write_text("".join(json.dumps(r)+"\n" for r in data))
            with patch.object(replay, "HERE", root):
                result = replay.compute()
        v2 = result["extraction"]["labels"]["label_v2"]
        self.assertEqual(v2["comparison"]["jev_boolean"]["WRONG"],
                         dict(flagged=0, total=1, rate=0))
        self.assertEqual(v2["comparison"]["peer_majority"]["WRONG"]["rate"], 1)
        self.assertEqual(v2["comparison"]["uniform_peer"]["WRONG"]["rate"], .5)
        self.assertEqual(v2["all_boolean"]["WRONG"]["total"], 2)
        self.assertEqual(v2["below_005"], dict(correct=1, total=2))
        self.assertIsNone(v2["e4_fused"]["WRONG"]["rate"])
        self.assertEqual(result["doom"]["totals"]["prose_v5"],
                         dict(kills=3, deaths=1, seconds=3/35))

if __name__ == "__main__":
    unittest.main()
