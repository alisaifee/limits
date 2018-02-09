import unittest
from limits import limits
import six


class LimitsTests(unittest.TestCase):
    class FakeLimit(limits.RateLimitItem):
        granularity = (1, "fake")

    class GreaterFakeLimit(limits.RateLimitItem):
        granularity = (2, "fake")

    def test_key_all_strings_default_namespace(self):
        item = self.FakeLimit(1, 1)
        self.assertEqual(item.key_for("a", "b", "c"), "LIMITER/a/b/c/1/1/fake")

    def test_key_with_none_default_namespace(self):
        item = self.FakeLimit(1, 1)
        self.assertEqual(
            item.key_for("a", None, None), "LIMITER/a/None/None/1/1/fake"
        )

    def test_key_with_int_default_namespace(self):
        item = self.FakeLimit(1, 1)
        self.assertEqual(item.key_for("a", 1), "LIMITER/a/1/1/1/fake")

    def test_key_with_mixed_string_types_default_namespace(self):
        item = self.FakeLimit(1, 1)
        self.assertEqual(item.key_for(b"a", "b"), "LIMITER/a/b/1/1/fake")

    def test_eq(self):
        item1 = self.FakeLimit(1, 1)
        item2 = self.FakeLimit(1, 1)
        item3 = self.FakeLimit(2, 1)
        self.assertEqual(item1, item2)
        self.assertNotEqual(item1, item3)
        self.assertNotEqual(item1, None)

    def test_lt(self):
        item1 = self.FakeLimit(1, 1)
        item2 = self.FakeLimit(1, 1)
        item3 = self.GreaterFakeLimit(1, 1)
        self.assertFalse(item1 < item2)
        self.assertFalse(item1 > item2)
        self.assertLess(item1, item3)
        self.assertGreater(item3, item1)
        self.assertGreater(item1, None)
