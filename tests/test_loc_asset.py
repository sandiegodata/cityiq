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

config = Config(cache_objects='/tmp', cache_errors='/tmp/errors')

class TestLocAsset(CityIQTest):

    def test_location_events(self):
        from datetime import datetime

        c = CityIq(Config(cache_dir='/tmp', cache_errors='/tmp/errors'))

        locations = list(c.walkways)

        start = c.tz.localize(datetime(2019, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 1, 31, 0, 0, 0))


        ft = FetchTask(locations[100], overwrite=True)

        events1 = ft.events('PEDEVT', start, end)

        print(len(events1))

        events2 = locations[100].events('PEDEVT', start, end)

        print(len(events2))


    def test_asset_events(self):

        c = CityIq(Config(cache_objects='/tmp'))

        start = c.tz.localize(datetime(2019, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 1, 31, 0, 0, 0))

        a = c.get_asset('ff0cfb97-d1d5-463a-b36f-2626421b5e8d')

        ft = FetchTask(0, a, 'PKIN', start, end, overwrite=True)

        events1 = ft.run()

        print(len(events1))

    def test_async_runner_locations(self):

        c = CityIq(config)

        start = c.tz.localize(datetime(2020, 5, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2020, 5, 5, 0, 0, 0))

        assets = [ e for e in c.get_assets() if e.eventTypes and 'BICYCLE' in e.eventTypes ]

        afr = AsyncFetchRunner(c.config, assets[0:10], 'BICYCLE', start, end)

        for e in afr.get_events():
            print(e)