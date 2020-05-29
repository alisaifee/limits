import pytest

from limits import limits


def test_seconds_value():
    assert limits.RateLimitItemPerSecond(1).get_expiry() == 1
    assert limits.RateLimitItemPerMinute(1).get_expiry() == 60
    assert limits.RateLimitItemPerHour(1).get_expiry() == 60 * 60
    assert limits.RateLimitItemPerDay(1).get_expiry() == 60 * 60 * 24
    assert limits.RateLimitItemPerMonth(1).get_expiry() == 60 * 60 * 24 * 30
    assert (
        limits.RateLimitItemPerYear(1).get_expiry() == 60 * 60 * 24 * 30 * 12
    )


@pytest.mark.parametrize(
    'string_representation, limit_instance',
    [
        ("1 per 1 second", limits.RateLimitItemPerSecond(1)),
        ("1 per 1 minute", limits.RateLimitItemPerMinute(1)),
        ("1 per 1 hour", limits.RateLimitItemPerHour(1)),
        ("1 per 1 day", limits.RateLimitItemPerDay(1)),
        ("1 per 1 month", limits.RateLimitItemPerMonth(1)),
        ("1 per 1 year", limits.RateLimitItemPerYear(1)),
    ]
)
def test_representation(string_representation, limit_instance):
    assert string_representation in str(limit_instance)


def test_comparison():
    assert limits.RateLimitItemPerSecond(1) < limits.RateLimitItemPerMinute(1)
    assert limits.RateLimitItemPerMinute(1) < limits.RateLimitItemPerHour(1)
    assert limits.RateLimitItemPerHour(1) < limits.RateLimitItemPerDay(1)
    assert limits.RateLimitItemPerDay(1) < limits.RateLimitItemPerMonth(1)
    assert limits.RateLimitItemPerMonth(1) < limits.RateLimitItemPerYear(1)
