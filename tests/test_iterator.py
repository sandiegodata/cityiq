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

class TestIterator(CityIQTest):

    def test_basic(self):
        from datetime import datetime
        from cityiq.iterate import EventIterator

        c = CityIq(Config())

        l =  c.load_locations('/tmp/locations.csv')

        start = c.tz.localize(datetime(2019, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 3, 25, 0, 0, 0))

        ei = EventIterator(c.config, 'PKIN', objects=l[:2], start_time='2020-05-10', end_time='2020-05-20')

        #for e in list(l)[:5]:
        #    print(e)

        for e in ei.generate_file_names():
            print(e)

        #for e in ei.request_months():
        #    print(e)

        #for e in ei.generate_file_names():
        #    print(e)
