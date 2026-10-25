import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda_pipeline import (
    Paths,
    _schedule_features_for_group,
    add_metadata_features,
    build_forecast_frame,
    load_raw,
)


ROOT = Path(__file__).resolve().parents[1]


class ScheduleFeatureTests(unittest.TestCase):
    def test_visible_boundary_is_right_censored(self):
        frame = pd.DataFrame(
            {
                "HubID": [1] * 5,
                "Date": pd.date_range("2015-01-01", periods=5),
                "PromoActive": [0, 1, 1, 1, 1],
            }
        )
        features = _schedule_features_for_group(frame, "PromoActive", "Promo")
        self.assertEqual(features.loc[1, "Promo_StreakDay"], 1)
        self.assertEqual(features.loc[4, "Promo_RightCensored"], 1)
        self.assertTrue(pd.isna(features.loc[4, "Promo_Tomorrow"]))

    def test_calendar_gap_breaks_streak(self):
        frame = pd.DataFrame(
            {
                "HubID": [1, 1, 1],
                "Date": pd.to_datetime(["2015-01-01", "2015-01-02", "2015-01-05"]),
                "IsOpen": [1, 1, 1],
            }
        )
        features = _schedule_features_for_group(frame, "IsOpen", "Open")
        self.assertEqual(features.loc[2, "Open_StreakDay"], 1)


class RealDataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = Paths(ROOT)
        cls.frames = load_raw(cls.paths)

    def test_raw_contract(self):
        train, test, metadata = self.frames["train"], self.frames["test"], self.frames["metadata"]
        self.assertEqual(train.shape, (970_379, 9))
        self.assertEqual(test.shape, (46_830, 8))
        self.assertEqual(metadata["HubID"].nunique(), 1_115)
        self.assertEqual(train.duplicated(["HubID", "Date"]).sum(), 0)
        self.assertEqual(test.duplicated(["HubID", "Date"]).sum(), 0)

    def test_closed_rows_are_zero(self):
        closed = self.frames["train"].query("IsOpen == 0")
        self.assertTrue(closed["OrderVolume"].eq(0).all())
        self.assertTrue(closed["AppSessions"].eq(0).all())

    def test_metadata_features_preserve_rows_and_handle_missing(self):
        sample = self.frames["train"].head(2_000)
        enriched = add_metadata_features(sample, self.frames["metadata"])
        self.assertEqual(len(sample), len(enriched))
        self.assertFalse(np.isinf(enriched.select_dtypes(include=[np.number])).any().any())

    def test_fold_features_ignore_future_targets_and_sessions(self):
        origin = pd.Timestamp("2015-05-08")
        future = self.frames["train"].copy()
        original = build_forecast_frame(self.frames["train"], future, self.frames["metadata"], origin)
        mask = future["Date"].between(origin + pd.Timedelta(days=1), origin + pd.Timedelta(days=42))
        future.loc[mask, "OrderVolume"] += 999_999
        future.loc[mask, "AppSessions"] += 99_999
        mutated = build_forecast_frame(self.frames["train"], future, self.frames["metadata"], origin)
        feature_columns = [c for c in original if not c.startswith("Actual")]
        pd.testing.assert_frame_equal(original[feature_columns], mutated[feature_columns], check_dtype=True)


if __name__ == "__main__":
    unittest.main()
