from limits import limits
from limits.util import parse, parse_many, granularity_from_string
import pytest


@pytest.mark.parametrize(
    'rate_limit_string, limit_instance',
    [
        ("1 per second", limits.RateLimitItemPerSecond(1)),
        ("1/SECOND", limits.RateLimitItemPerSecond(1)),
        ("1 / Second", limits.RateLimitItemPerSecond(1)),
        ("1 per minute", limits.RateLimitItemPerMinute(1)),
        ("1/MINUTE", limits.RateLimitItemPerMinute(1)),
        ("1/Minute", limits.RateLimitItemPerMinute(1)),
        ("1 per hour", limits.RateLimitItemPerHour(1)),
        ("1/HOUR", limits.RateLimitItemPerHour(1)),
        ("1/Hour", limits.RateLimitItemPerHour(1)),
        ("1 per day", limits.RateLimitItemPerDay(1)),
        ("1/DAY", limits.RateLimitItemPerDay(1)),
        ("1/Day", limits.RateLimitItemPerDay(1)),
        ("1 per month", limits.RateLimitItemPerMonth(1)),
        ("1/MONTH", limits.RateLimitItemPerMonth(1)),
        ("1/Month", limits.RateLimitItemPerMonth(1)),
        ("1 per year", limits.RateLimitItemPerYear(1)),
        ("1/YEAR", limits.RateLimitItemPerYear(1)),
        ("1/Year", limits.RateLimitItemPerYear(1)),
    ]
)
def test_singles(rate_limit_string, limit_instance):
    assert parse(rate_limit_string) == limit_instance


@pytest.mark.parametrize(
    'multiples_string, limit_instance',
    [
        ("1 per 3 hour", limits.RateLimitItemPerHour(1, 3)),
        ("1 per 2 hours", limits.RateLimitItemPerHour(1, 2)),
        ("1/2day", limits.RateLimitItemPerDay(1, 2)),
    ]
)
def test_multiples(multiples_string, limit_instance):
    assert parse(multiples_string) == limit_instance


@pytest.mark.parametrize(
    'multi_string, count, limit_instances',
    [
        (
            "1 per 3 hour, 1 per second", 2,
            [
                limits.RateLimitItemPerHour(1, 3),
                limits.RateLimitItemPerSecond(1)
            ]
        ),
        (
            "1/hour; 2/second, 10 per 2 days", 3,
            [
                limits.RateLimitItemPerHour(1),
                limits.RateLimitItemPerSecond(2),
                limits.RateLimitItemPerDay(10, 2),
            ]
        ),
    ]
)
def test_parse_many(multi_string, count, limit_instances):
    parsed = parse_many(multi_string)
    assert len(parsed) == count
    assert limit_instances == parsed


@pytest.mark.parametrize(
    'invalid_string',
    [None, "1 per millennium", "one per second"]
)
def test_parse_invalid_string(invalid_string):
    with pytest.raises(ValueError):
        parse(invalid_string)


@pytest.mark.parametrize('invalid_string', ['millennium', ''])
def test_granularity_from_string_invalid(invalid_string):
    with pytest.raises(ValueError):
        granularity_from_string(invalid_string)


@pytest.mark.parametrize('invalid_string', ["1 per year; 2 per decade", ])
def test_parse_many_invalid_string(invalid_string):
    with pytest.raises(ValueError):
        parse_many(invalid_string)
