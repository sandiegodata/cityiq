import unittest
from pathlib import Path

from cityiq.config import Config


class CityIQTest(unittest.TestCase):
    """Test Metapack AppUrls and Row Generators"""

    def get_test_data(self, *paths):
        from os.path import dirname, join, abspath

        return join(dirname(abspath(__file__)), 'test_data', *paths)

    def setUp(self):
        import warnings

        self.config = Config(Path(__file__).parent.joinpath())
        warnings.simplefilter('ignore')
