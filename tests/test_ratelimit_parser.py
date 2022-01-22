import pytest

from limits import limits
from limits.util import granularity_from_string, parse, parse_many


class TestRatelimitParser:
    def test_singles(self):
        for rl_string in ["1 per second", "1/SECOND", "1 / Second"]:
            assert parse(rl_string) == limits.RateLimitItemPerSecond(1)

        for rl_string in ["1 per minute", "1/MINUTE", "1/Minute"]:
            assert parse(rl_string) == limits.RateLimitItemPerMinute(1)

        for rl_string in ["1 per hour", "1/HOUR", "1/Hour"]:
            assert parse(rl_string) == limits.RateLimitItemPerHour(1)

        for rl_string in ["1 per day", "1/DAY", "1 / Day"]:
            assert parse(rl_string) == limits.RateLimitItemPerDay(1)

        for rl_string in ["1 per month", "1/MONTH", "1 / Month"]:
            assert parse(rl_string) == limits.RateLimitItemPerMonth(1)

        for rl_string in ["1 per year", "1/Year", "1 / year"]:
            assert parse(rl_string) == limits.RateLimitItemPerYear(1)

    def test_multiples(self):
        assert parse("1 per 3 hour").get_expiry() == 3 * 60 * 60
        assert parse("1 per 2 hours").get_expiry() == 2 * 60 * 60
        assert parse("1/2 day").get_expiry() == 2 * 24 * 60 * 60

    def test_parse_many(self):
        parsed = parse_many("1 per 3 hour; 1 per second")
        assert len(parsed) == 2
        assert parsed[0].get_expiry() == 3 * 60 * 60
        assert parsed[1].get_expiry() == 1

    def test_parse_many_csv(self):
        parsed = parse_many("1 per 3 hour, 1 per second")
        assert len(parsed) == 2
        assert parsed[0].get_expiry() == 3 * 60 * 60
        assert parsed[1].get_expiry() == 1

    @pytest.mark.parametrize("value", [None, "1 per millenium", "meow"])
    def test_invalid_string_parse(self, value):
        with pytest.raises(ValueError):
            parse(value)

    @pytest.mark.parametrize("value", ["millenium", "meow"])
    def test_invalid_string_granularity(self, value):
        with pytest.raises(ValueError):
            granularity_from_string(value)

    @pytest.mark.parametrize(
        "value",
        ["1 per yearl; 2 per decade"],
    )
    def test_invalid_string_parse_many(self, value):
        with pytest.raises(ValueError):
            parse_many(value)
