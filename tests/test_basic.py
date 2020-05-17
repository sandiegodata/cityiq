"""

"""

import logging

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config
from cityiq.scrape import logger as scrape_logger
from cityiq.token import logger as token_logger

from .support import CityIQTest
import csv
import pathlib
from datetime import datetime

# config_file = '/Users/eric/proj/virt-proj/data-project/sdrdl-data-projects/sandiego.gov/predix.io/prod-credentials
# .yaml'


import logging
logging.basicConfig(level=logging.DEBUG)

config = Config(cache_objects='/tmp/object/', cache_error='/tmp/error', cache_meta='/tmp/meta')

class TestBasic(CityIQTest):

    def test_get_token(self):
        c = CityIq(config)

        self.assertTrue(len(c.token) > 100)

    def test_time(self):

        c = CityIq(config)

        dt = c.tz.localize(datetime(2020, 1, 1, 0, 0, 0))

        for t in ('2020-01-01', 1577865600, datetime(2020, 1, 1, 0, 0, 0)):
            self.assertEquals(dt, c.convert_time(t))

        now = c.tz.localize(datetime.now())

        for t in ('now', None):
            self.assertEquals(int(now.timestamp()), int(c.convert_time(t).timestamp()))

    def test_cache_assets_locations(self):
        from time import time

        c = CityIq(config)

        c.clear_meta_cache()

        #
        # These should take gonger because
        # they are making the full request
        t = time()
        o = c.get_locations()
        self.assertGreater(time() - t, 1)
        self.assertGreater(len(o), 500)

        t = time()
        c.get_assets()
        self.assertGreater(time() - t, 4)
        o = self.assertGreater(len(o), 500)

        # These should be fast, because they are cached.
        t = time()
        o=c.get_locations()
        self.assertLess(time() - t, 1)
        self.assertGreater(len(o), 500)

        t = time()
        o=c.get_assets()
        self.assertLess(time() - t, 1)
        self.assertGreater(len(o), 500)


    def test_total_bbox(self):

        c = CityIq(config)

        print(c.total_bounds)


    def test_location_events(self):
        from datetime import datetime

        c = CityIq(config)

        locations = list(c.locations)

        start = c.tz.localize(datetime(2020, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2020, 2, 1, 0, 0, 0))

        for l in locations:
            print(l.uid, len(l.get_events('PKIN', start, end)))


    def test_location_events_2(self):

        from datetime import datetime

        c = CityIq(config)

        locations = list(c.locations)

        start = c.tz.localize(datetime(2020, 1, 1, 0, 0, 0))
        end = None # c.tz.localize(datetime(2019, 2, 1, 14, 0, 0))

        print(locations[300].events('PKIN', start, end))

    def test_nodes(self):

        c = CityIq(config)

        for n in c.nodes:
            print(n)
            for c in n.children:
                print('  ', c)

    def test_walkways(self):

        c = CityIq(Config(cache_dir='/tmp'))

        for n in c.parking_zones:
            print(n)
            for c in n.assets:
                print('  ', c)

    def test_pkin_events(self):

        c = CityIq(Config(cache_dir='/tmp'))

        from datetime import datetime
        import pytz

        pacific = pytz.timezone('US/Pacific')

        ts = pacific.localize(datetime(2019, 2, 4, 17, 30, 0)).timestamp()

        events = list(c.events(start_time=ts, span=15 * 60, event_type='PKIN'))

        min_ts = 2 ** 64
        max_ts = 0

        for i, e in enumerate(events):
            min_ts = min(min_ts, int(e['timestamp']))
            max_ts = max(max_ts, int(e['timestamp']))

        self.assertEquals(388, len(events))
        self.assertEquals(1549330381284, min_ts)
        self.assertEquals(1549331098206, max_ts)

    def test_pdevt_events(self):

        c = CityIq(Config(cache_dir='/tmp'))

        from datetime import datetime
        import pytz

        pacific = pytz.timezone('US/Pacific')

        ts = pacific.localize(datetime(2019, 2, 4, 17, 30, 0)).timestamp()

        events = list(c.events(start_time=ts, span=15 * 60, event_type='PEDEVT'))

        min_ts = 2 ** 64
        max_ts = 0

        for i, e in enumerate(events):
            min_ts = min(min_ts, int(e['timestamp']))
            max_ts = max(max_ts, int(e['timestamp']))

        print(min_ts, max_ts)

        self.assertEquals(280, len(events))
        self.assertEquals(1549330201799, min_ts)
        self.assertEquals(1549331099575, max_ts)

    def test_async_events(self):

        c = CityIq(Config(cache_dir='/tmp'))

        for e in c.events_async():
            print(e)

    def test_scrape_events_1(self):
        from datetime import datetime
        from cityiq.scrape import get_events
        import json

        logging.basicConfig(level=logging.INFO)
        token_logger.setLevel(logging.DEBUG)
        scrape_logger.setLevel(logging.DEBUG)

        config = Config()

        r = get_events(config, datetime(2019, 2, 5, 12, 0, 0), 1 * 60 * 60, ['PKIN', 'PKOUT'])

        with open('/tmp/results.json', 'w') as f:
            json.dump(r, f)



    def test_bicycle_events(self):

        c = CityIq(config)

        for a in c.get_assets():
            if a.eventTypes and 'BICYCLE' in a.eventTypes:
                print(a.uid, len(a.get_events('BICYCLE', '2020-4-1', '2020-4-2')))


    def test_bicycle_event(self):

        c = CityIq(config)

        start = c.tz.localize(datetime(2020, 4, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2020, 4, 3, 0, 0, 0))

        a = c.get_asset('99b3cf15-cf73-459e-8811-904224c3dfd5')

        print(a.uid, len(a.get_events('BICYCLE', '2020-4-1', '2020-4-2')))


    def test_locations_at_asset(self):

        import csv
        import pathlib

        c = CityIq(config)

        for a in c.assets:
            for l in a.locations:
                print(a.assetUid, a.parentAssetUid, a.assetType,  l.locationUid, l.parentLocationUid, l.locationType)


    def test_load_locations(self):

        c = CityIq(config)

        for l in c.load_locations('/tmp/locations.csv'):
            print(l)

