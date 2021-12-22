from limits import limits


class TestGranularity:
    def test_seconds_value(self):
        assert limits.RateLimitItemPerSecond(1).get_expiry() == 1
        assert limits.RateLimitItemPerMinute(1).get_expiry() == 60
        assert limits.RateLimitItemPerHour(1).get_expiry() == 60 * 60
        assert limits.RateLimitItemPerDay(1).get_expiry() == 60 * 60 * 24
        assert limits.RateLimitItemPerMonth(1).get_expiry() == 60 * 60 * 24 * 30
        assert limits.RateLimitItemPerYear(1).get_expiry() == 60 * 60 * 24 * 30 * 12

    def test_representation(self):
        assert "1 per 1 second" in str(limits.RateLimitItemPerSecond(1))
        assert "1 per 1 minute" in str(limits.RateLimitItemPerMinute(1))
        assert "1 per 1 hour" in str(limits.RateLimitItemPerHour(1))
        assert "1 per 1 day" in str(limits.RateLimitItemPerDay(1))
        assert "1 per 1 month" in str(limits.RateLimitItemPerMonth(1))
        assert "1 per 1 year" in str(limits.RateLimitItemPerYear(1))

    def test_comparison(self):
        assert limits.RateLimitItemPerSecond(1) < limits.RateLimitItemPerMinute(1)
        assert limits.RateLimitItemPerMinute(1) < limits.RateLimitItemPerHour(1)
        assert limits.RateLimitItemPerHour(1) < limits.RateLimitItemPerDay(1)
        assert limits.RateLimitItemPerDay(1) < limits.RateLimitItemPerMonth(1)
        assert limits.RateLimitItemPerMonth(1) < limits.RateLimitItemPerYear(1)
