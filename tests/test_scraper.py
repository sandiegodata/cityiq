"""

"""
import logging

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config
from cityiq.scrape import logger as scrape_logger
from cityiq.token import logger as token_logger
from datetime import datetime
from .support import CityIQTest
from  cityiq.task import FetchTask
from cityiq.scrape import AsyncFetchRunner
import logging


logging.basicConfig(level=logging.DEBUG)
from cityiq.scrape import AsyncFetchRunner

class TestScraper(CityIQTest):

    def test_basic(self):
        from datetime import datetime
        from cityiq.iterate import EventIterator

        c = CityIq(Config())

        l = c.get_locations()

