from collections import defaultdict

from limits import limits


class TestLimits:
    class FakeLimit(limits.RateLimitItem):
        GRANULARITY = limits.Granularity(1, "fake")

    class OtherFakeLimit(limits.RateLimitItem):
        GRANULARITY = limits.Granularity(1, "otherfake")

    def test_key_all_strings_default_namespace(self):
        item = self.FakeLimit(1, 1)
        assert item.key_for("a", "b", "c") == "LIMITER/a/b/c/1/1/fake"

    def test_key_with_none_default_namespace(self):
        item = self.FakeLimit(1, 1)
        assert item.key_for("a", None, None) == "LIMITER/a/None/None/1/1/fake"

    def test_key_with_int_default_namespace(self):
        item = self.FakeLimit(1, 1)
        assert item.key_for("a", 1) == "LIMITER/a/1/1/1/fake"

    def test_key_with_mixed_string_types_default_namespace(self):
        item = self.FakeLimit(1, 1)
        assert item.key_for(b"a", "b") == "LIMITER/a/b/1/1/fake"

    def test_equality(self):
        item = self.FakeLimit(1, 1)
        assert item == self.FakeLimit(1, 1)
        assert item != self.FakeLimit(1, 2)
        assert item != self.FakeLimit(2, 1)
        assert item != "someething else"

    def test_hashabilty(self):
        mapping = defaultdict(lambda: 1)
        mapping[self.FakeLimit(1, 1)] += 1
        mapping[self.FakeLimit(1, 1)] += 1
        mapping[self.FakeLimit(1, 2)] += 1
        mapping[self.FakeLimit(1, 2)] += 1
        mapping[self.OtherFakeLimit(1, 2)] += 1

        assert len(mapping) == 3
