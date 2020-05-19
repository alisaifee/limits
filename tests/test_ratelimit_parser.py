import unittest

import pytest

from limits.util import parse, parse_many, granularity_from_string
from limits import limits


@pytest.mark.unit
class RatelimitParserTests(unittest.TestCase):
    def test_singles(self):
        for rl_string in ["1 per second", "1/SECOND", "1 / Second"]:
            self.assertEqual(
                parse(rl_string), limits.RateLimitItemPerSecond(1)
            )
        for rl_string in ["1 per minute", "1/MINUTE", "1/Minute"]:
            self.assertEqual(
                parse(rl_string), limits.RateLimitItemPerMinute(1)
            )
        for rl_string in ["1 per hour", "1/HOUR", "1/Hour"]:
            self.assertEqual(parse(rl_string), limits.RateLimitItemPerHour(1))
        for rl_string in ["1 per day", "1/DAY", "1 / Day"]:
            self.assertEqual(parse(rl_string), limits.RateLimitItemPerDay(1))
        for rl_string in ["1 per month", "1/MONTH", "1 / Month"]:
            self.assertEqual(parse(rl_string), limits.RateLimitItemPerMonth(1))
        for rl_string in ["1 per year", "1/Year", "1 / year"]:
            self.assertEqual(parse(rl_string), limits.RateLimitItemPerYear(1))

    def test_multiples(self):
        self.assertEqual(parse("1 per 3 hour").get_expiry(), 3 * 60 * 60)
        self.assertEqual(parse("1 per 2 hours").get_expiry(), 2 * 60 * 60)
        self.assertEqual(parse("1/2 day").get_expiry(), 2 * 24 * 60 * 60)

    def test_parse_many(self):
        parsed = parse_many("1 per 3 hour; 1 per second")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].get_expiry(), 3 * 60 * 60)
        self.assertEqual(parsed[1].get_expiry(), 1)

    def test_parse_many_csv(self):
        parsed = parse_many("1 per 3 hour, 1 per second")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].get_expiry(), 3 * 60 * 60)
        self.assertEqual(parsed[1].get_expiry(), 1)

    def test_invalid_string(self):
        self.assertRaises(ValueError, parse, None)
        self.assertRaises(ValueError, parse, "1 per millienium")
        self.assertRaises(ValueError, granularity_from_string, "millenium")
        self.assertRaises(ValueError, parse_many, "1 per year; 2 per decade")
