from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from utils.game_analytics.get_pay_splits import return_all_filepaths
from utils.game_analytics.get_symbol_hits import HitRateCalculations


class IsolatedAnalyticsPathTests(unittest.TestCase):
    def test_split_paths_use_the_explicit_generation_root(self) -> None:
        lut_path, split_path = return_all_filepaths(
            "brain_frenzy",
            "base",
            publish_path="isolated/publish_files",
            lookup_path="isolated/lookup_tables",
        )
        self.assertEqual(
            Path(lut_path),
            Path("isolated/publish_files/lookUpTable_base_0.csv"),
        )
        self.assertEqual(
            Path(split_path),
            Path("isolated/lookup_tables/lookUpTableSegmented_base.csv"),
        )

    def test_symbol_analysis_reads_the_explicit_generation_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            library = Path(temp_dir)
            (library / "forces").mkdir()
            (library / "publish_files").mkdir()
            (library / "forces" / "force_record_base.json").write_text(
                json.dumps(
                    [
                        {
                            "search": [{"name": "symbol", "value": "L1"}],
                            "timesTriggered": 1,
                            "bookIds": [1],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (library / "publish_files" / "lookUpTable_base_0.csv").write_text(
                "1,10,100\n",
                encoding="utf-8",
            )

            result = HitRateCalculations(
                "brain_frenzy",
                "base",
                mode_cost=1,
                library_path=str(library),
            )

            self.assertEqual(result.weights, [10])
            self.assertEqual(result.payouts, [100.0])


if __name__ == "__main__":
    unittest.main()
