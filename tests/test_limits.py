import pytest

from limits import limits


class FakeLimit(limits.RateLimitItem):
    granularity = (1, "fake")


def test_key_all_strings_default_namespace():
    item = FakeLimit(1, 1)
    assert item.key_for("a", "b", "c") == "LIMITER/a/b/c/1/1/fake"


def test_key_with_none_default_namespace():
    item = FakeLimit(1, 1)
    assert item.key_for("a", None, None) == "LIMITER/a/None/None/1/1/fake"


def test_key_with_int_default_namespace():
    item = FakeLimit(1, 1)
    assert item.key_for("a", 1) == "LIMITER/a/1/1/1/fake"


def test_key_with_mixed_string_types_default_namespace():
    item = FakeLimit(1, 1)
    assert item.key_for(b"a", "b") == "LIMITER/a/b/1/1/fake"


@pytest.mark.parametrize(
    "expiry_seconds, limit",
    [
        (1, limits.RateLimitItemPerSecond(1)),
        (1 * 60, limits.RateLimitItemPerMinute(1)),
        (2 * 60, limits.RateLimitItemPerMinute(1, 2)),
        (1 * 60 * 60, limits.RateLimitItemPerHour(1, 1)),
        (2 * 60 * 60, limits.RateLimitItemPerHour(1, 2)),
        (1 * 60 * 60 * 24, limits.RateLimitItemPerDay(1, 1)),
        (2 * 60 * 60 * 24, limits.RateLimitItemPerDay(1, 2)),
        (1 * 60 * 60 * 24 * 30, limits.RateLimitItemPerMonth(1)),
        (1 * 60 * 60 * 24 * 30 * 12, limits.RateLimitItemPerYear(1)),
    ]
)
def test_expiry(expiry_seconds, limit):
    assert limit.get_expiry() == expiry_seconds
