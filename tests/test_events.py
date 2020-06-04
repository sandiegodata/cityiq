"""

"""

import logging
from pathlib import Path

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config

from .support import CityIQTest

import logging
logging.basicConfig()

class TestEvents(CityIQTest):

    def setUp(self):
        self.config = Config(Path(__file__).parent.joinpath())

    def test_bicycle_events(self):
        import pandas as pd

        api_logger.setLevel(logging.DEBUG)

        c = CityIq(self.config)

        a = c.get_asset('0e5d0a42-8c9e-49fd-9bd7-6ccdf69f840e')

        # Clean everything

        c._clean_cache(a, 'BICYCLE', '2020-01-01', '2020-02-01')

        e = c.get_cached_events(a, 'BICYCLE', '2020-01-10', '2020-01-15')

        self.assertEqual(0, len(e))

        # Cache events in ranges.

        c.cache_events(a, 'BICYCLE', '2020-01-01', '2020-01-05')

        e = c.get_cached_events(a, 'BICYCLE', '2020-01-01', '2020-02-01')
        self.assertEqual(22942, len(e))
        self.assertEqual('2020-01-01', str(e.timestamp.min().date()))
        self.assertEqual('2020-01-04', str(e.timestamp.max().date()))

        c.cache_events(a, 'BICYCLE', '2020-01-10', '2020-01-15')
        c.cache_events(a, 'BICYCLE', '2020-01-20', '2020-01-25')

        e = c.get_cached_events(a, 'BICYCLE', '2020-01-01', '2020-02-01')
        self.assertEqual(80212, len(e))
        self.assertEqual('2020-01-01', str(e.timestamp.min().date()))
        self.assertEqual('2020-01-24', str(e.timestamp.max().date()))

        c.cache_events(a, 'BICYCLE', '2020-01-04', '2020-01-11')
        c.cache_events(a, 'BICYCLE', '2020-01-01', '2020-02-01')

        e = c.get_cached_events(a, 'BICYCLE', '2020-01-01', '2020-02-01')
        self.assertEqual(177568, len(e))
        self.assertEqual('2020-01-01', str(e.timestamp.min().date()))
        self.assertEqual('2020-01-31', str(e.timestamp.max().date()))

        # Check a subrange.
        e = c.get_cached_events(a, 'BICYCLE', '2020-01-10', '2020-01-15')

        self.assertEqual(28670, len(e))
        self.assertEqual('2020-01-10', str(e.timestamp.min().date()))
        self.assertEqual('2020-01-14', str(e.timestamp.max().date()))

        c._clean_cache(a, 'BICYCLE', '2020-01-01', '2020-02-01')
        self.assertEqual(0, len(e))

    def test_make_events(self):
        c = CityIq(self.config)

        a = c.get_asset('0e5d0a42-8c9e-49fd-9bd7-6ccdf69f840e')

        tasks = c.make_tasks([a], ['PKIN', 'PKOUT'], '2020-01-01', '2020-03-01')

        self.assertEqual(12, len(tasks))

        dates = [t.start_date.isoformat() for t in tasks]


        self.assertEquals(['2020-01-01T00:00:00-08:00', '2020-01-11T00:00:00-08:00',
                           '2020-01-21T00:00:00-08:00', '2020-01-31T00:00:00-08:00',
                           '2020-02-10T00:00:00-08:00', '2020-02-20T00:00:00-08:00',
                           '2020-01-01T00:00:00-08:00', '2020-01-11T00:00:00-08:00',
                           '2020-01-21T00:00:00-08:00', '2020-01-31T00:00:00-08:00',
                           '2020-02-10T00:00:00-08:00', '2020-02-20T00:00:00-08:00'],
                          dates)


    def test_async_events(self):
        api_logger.setLevel(logging.DEBUG)

        c = CityIq(self.config)

        assets = list(c.assets_by_event(['PKIN','PKOUT']))

        self.assertEqual(2590, len(assets))

        assets = assets[100:110]

        tasks = c.make_tasks(assets,['PKIN','PKOUT'], '2020-01-01', '2020-02-01' )

        self.assertEqual(20, len(tasks))  # one per asset/event type

        list(c.run_async(tasks))

        df = c.get_cached_events(assets,['PKIN','PKOUT'], '2020-01-01', '2020-02-01' )

        print(len(df))
        print(df.head())

