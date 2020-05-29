import unittest

from limits import limits


class GranularityTests(unittest.TestCase):
    def test_seconds_value(self):
        self.assertEqual(
            limits.RateLimitItemPerSecond(1).get_expiry(), 1
        )
        self.assertEqual(
            limits.RateLimitItemPerMinute(1).get_expiry(), 60
        )
        self.assertEqual(
            limits.RateLimitItemPerHour(1).get_expiry(), 60 * 60
        )
        self.assertEqual(
            limits.RateLimitItemPerDay(1).get_expiry(), 60 * 60 * 24
        )
        self.assertEqual(
            limits.RateLimitItemPerMonth(1).get_expiry(), 60 * 60 * 24 * 30
        )
        self.assertEqual(
            limits.RateLimitItemPerYear(1).get_expiry(), 60 * 60 * 24 * 30 * 12
        )

    def test_representation(self):
        self.assertTrue(
            "1 per 1 second" in str(limits.RateLimitItemPerSecond(1))
        )
        self.assertTrue(
            "1 per 1 minute" in str(limits.RateLimitItemPerMinute(1))
        )
        self.assertTrue(
            "1 per 1 hour" in str(limits.RateLimitItemPerHour(1))
        )
        self.assertTrue(
            "1 per 1 day" in str(limits.RateLimitItemPerDay(1))
        )
        self.assertTrue(
            "1 per 1 month" in str(limits.RateLimitItemPerMonth(1))
        )
        self.assertTrue(
            "1 per 1 year" in str(limits.RateLimitItemPerYear(1))
        )

    def test_comparison(self):
        self.assertTrue(
            limits.RateLimitItemPerSecond(1) < limits.RateLimitItemPerMinute(1)
        )
        self.assertTrue(
            limits.RateLimitItemPerMinute(1) < limits.RateLimitItemPerHour(1)
        )
        self.assertTrue(
            limits.RateLimitItemPerHour(1) < limits.RateLimitItemPerDay(1)
        )
        self.assertTrue(
            limits.RateLimitItemPerDay(1) < limits.RateLimitItemPerMonth(1)
        )
        self.assertTrue(
            limits.RateLimitItemPerMonth(1) < limits.RateLimitItemPerYear(1)
        )
