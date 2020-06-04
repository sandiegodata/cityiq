"""

"""

import logging
from pathlib import Path

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config

from .support import CityIQTest

logging.basicConfig()


class TestEvents(CityIQTest):

    def setUp(self):
        self.config = Config(Path(__file__).parent.joinpath())

    def test_bicycle_events(self):
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
        e = c.get_cached_events(a, 'BICYCLE', '2020-01-10', '2020-01-15')
        self.assertEqual(0, len(e))

    def test_make_events(self):
        c = CityIq(self.config)

        a = c.get_asset('0e5d0a42-8c9e-49fd-9bd7-6ccdf69f840e')

        tasks = c.make_tasks([a], ['PKIN', 'PKOUT'], '2020-01-01', '2020-03-01')

        self.assertEqual(24, len(tasks))

        dates = list(sorted([t.start_date.isoformat() for t in tasks]))

        self.assertEqual(['2020-01-01T00:00:00-08:00',
                           '2020-01-01T00:00:00-08:00',
                           '2020-01-06T00:00:00-08:00',
                           '2020-01-06T00:00:00-08:00',
                           '2020-01-11T00:00:00-08:00',
                           '2020-01-11T00:00:00-08:00',
                           '2020-01-16T00:00:00-08:00',
                           '2020-01-16T00:00:00-08:00'], dates[:8] )


    def test_async_events(self):
        api_logger.setLevel(logging.DEBUG)

        c = CityIq(self.config)

        assets = list(c.assets_by_event(['PKIN', 'PKOUT']))

        self.assertEqual(2590, len(assets))

        assets = [c.get_asset(u) for u in ['094c05dc-6378-476b-817d-21ba3b99f8ab',
                                           '09741091-c77e-4d61-9a14-d489bd061975',
                                           '09aa6fad-0ae3-4256-906b-8e82c82eeacb',
                                           '09b58810-dd7b-40f2-b183-aef265db4681',
                                           '09f05731-a47e-41e6-970b-9fae943bfd3f',
                                           '09fdcb8e-9498-4c9e-8612-afdfd0487f64',
                                           '0a2f68d2-b283-4835-a775-a209645cebb2',
                                           '0a2ff822-6ba2-4f11-a6a0-b7f080b7ad08',
                                           '0a31fd96-f288-411c-8e50-f07b0b532462',
                                           '0a3e5df5-0738-4f3f-9ab8-1498adfde99c']]

        tasks = c.make_tasks(assets, ['PKIN', 'PKOUT'], '2020-01-01', '2020-02-01')

        self.assertEqual(140, len(tasks))  # one per asset/event type

        list(c.run_async(tasks))

        df = c.get_cached_events(assets, ['PKIN', 'PKOUT'], '2020-01-01', '2020-02-01')

        print(len(df))
        print(df.head())
