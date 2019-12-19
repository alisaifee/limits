import os
import unittest
from nose.plugins.skip import SkipTest

class IntegrationTest(unittest.TestCase):
    def setUp(self):
        if not os.environ.get('INTEGRATION_TESTS'):
            raise SkipTest
