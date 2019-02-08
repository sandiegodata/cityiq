import unittest


class CityIQTest(unittest.TestCase):
    """Test Metapack AppUrls and Row Generators"""

    def test_data(self, *paths):
        from os.path import dirname, join, abspath

        return join(dirname(abspath(__file__)), 'test_data', *paths)

    def get_config(self):

        pass

    def setUp(self):
        import warnings
        warnings.simplefilter('ignore')
