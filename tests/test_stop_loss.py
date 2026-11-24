import unittest
from decimal import Decimal

from regenerate_server import (
    _parse_investment_amount,
    estimate_daily_buy_point,
    estimate_daily_swing_low,
    estimate_daily_stop_loss,
    estimate_stop_loss,
)


class EstimateStopLossTests(unittest.TestCase):
    def test_uses_latest_swing_high_after_latest_swing_low_and_atr_at_that_high(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[20] = {"date": "2026-06-01", "high": 100, "low": 90, "close": 95}
        candles[25] = {"date": "2026-07-06", "high": 120, "low": 100, "close": 110}

        estimate = estimate_stop_loss(candles)

        self.assertEqual(estimate["swing_high_date"], "2026-07-06")
        self.assertEqual(estimate["atr_window"], 15)
        self.assertEqual(estimate["atr"], 60 / 15)
        estimates = estimate["estimates"]
        self.assertEqual([item["multiplier"] for item in estimates], [1.5, 2.5, 3.5])
        self.assertEqual([item["stop_loss"] for item in estimates], [114, 110, 106])
        self.assertEqual([item["atr_distance"] for item in estimates], [6, 10, 14])

    def test_requires_a_swing_high_after_the_latest_swing_low(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[20] = {"date": "2026-06-01", "high": 100, "low": 90, "close": 95}
        candles[25] = {"date": "2026-07-06", "high": 120, "low": 100, "close": 110}
        candles[27] = {"date": "2026-07-20", "high": 100, "low": 80, "close": 90}

        with self.assertRaisesRegex(ValueError, "after the latest swing low"):
            estimate_stop_loss(candles)

    def test_daily_stop_is_one_percent_below_the_latest_confirmed_swing_low(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[12] = {"date": "2026-01-13", "high": 100, "low": 90, "close": 95}
        candles[22] = {"date": "2026-01-23", "high": 95, "low": 80, "close": 85}

        estimate = estimate_daily_stop_loss(candles)

        self.assertEqual(estimate["swing_low_date"], "2026-01-23")
        self.assertEqual(estimate["swing_low"], 80)
        self.assertEqual(estimate["stop_distance"], 0.8)
        self.assertEqual(estimate["stop_loss"], 79.2)

    def test_daily_swing_low_returns_latest_confirmed_swing_low(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[12] = {"date": "2026-01-13", "high": 100, "low": 99, "close": 100}
        candles[22] = {"date": "2026-01-23", "high": 110, "low": 80, "close": 105}

        estimate = estimate_daily_swing_low(candles)

        self.assertEqual(estimate["swing_low_date"], "2026-01-23")
        self.assertEqual(estimate["swing_low"], 80)
        self.assertEqual(estimate["pivot_window"], 2)
        self.assertEqual(estimate["latest_close"], 100)
        self.assertEqual(estimate["latest_date"], "2026-01-30")

    def test_daily_swing_low_requires_confirmed_swing_low(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        # All lows are equal — no pivot low confirmed

        with self.assertRaisesRegex(ValueError, "No confirmed daily swing low"):
            estimate_daily_swing_low(candles)

    def test_daily_buy_point_is_latest_confirmed_swing_high(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[12] = {"date": "2026-01-13", "high": 110, "low": 99, "close": 105}
        candles[22] = {"date": "2026-01-23", "high": 115, "low": 105, "close": 110}

        estimate = estimate_daily_buy_point(candles)

        self.assertEqual(estimate["swing_high_date"], "2026-01-23")
        self.assertEqual(estimate["swing_high"], 115)
        self.assertEqual(estimate["pivot_window"], 2)
        self.assertEqual(estimate["latest_close"], 100)
        self.assertEqual(estimate["latest_date"], "2026-01-30")
        self.assertNotIn("whole_shares", estimate)

    def test_daily_buy_point_calculates_only_whole_shares(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        candles[22] = {"date": "2026-01-23", "high": 115, "low": 105, "close": 110}

        estimate = estimate_daily_buy_point(
            candles, investment_amount=Decimal("459.99")
        )

        self.assertEqual(estimate["swing_high"], 115)
        self.assertEqual(estimate["whole_shares"], 3)

    def test_investment_amount_is_optional_and_must_be_positive(self):
        self.assertIsNone(_parse_investment_amount({}))
        self.assertEqual(
            _parse_investment_amount({"amount": ["125.50"]}),
            Decimal("125.50"),
        )
        for value in ("", "0", "-1", "NaN", "Infinity", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "positive number"):
                    _parse_investment_amount({"amount": [value]})
        with self.assertRaisesRegex(ValueError, "single investment amount"):
            _parse_investment_amount({"amount": ["100", "200"]})

    def test_daily_buy_point_requires_confirmed_swing_high(self):
        candles = [
            {"date": f"2026-01-{index + 1:02d}", "high": 101, "low": 99, "close": 100}
            for index in range(30)
        ]
        # No pivot high present - all highs are same

        with self.assertRaisesRegex(ValueError, "No confirmed daily swing high"):
            estimate_daily_buy_point(candles)


if __name__ == "__main__":
    unittest.main()
