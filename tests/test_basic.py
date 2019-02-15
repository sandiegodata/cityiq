"""

"""

import logging

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config
from cityiq.scrape import logger as scrape_logger
from cityiq.token import logger as token_logger

from .support import CityIQTest

config_file = '/Users/eric/proj/virt-proj/data-project/sdrdl-data-projects/sandiego.gov/predix.io/prod-credentials.yaml'


class TestBasic(CityIQTest):

    def test_get_token(self):
        config = Config(config_file, cache_dir='/tmp')

        c = CityIq(config)

        self.assertTrue(len(c.token) > 100)

    def test_get_assets(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        assets = list(c.get_assets())

        self.assertTrue(len(assets) > 4000)

        return

        for a in assets[:5]:
            print(a.assetType, a.assetUid)
            # print(a.data)
            # print(l.detail)
            for l in a.locations:
                print('  ', l)

            for c in a.children:
                print('  ', c)

    def test_total_bbox(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        print(c.total_bounds)

        print(len(list(c.get_assets())))

    def test_dump_assets(self):
        import csv

        c = CityIq(Config(config_file, cache_dir='/tmp'))
        with open('/tmp/assets.csv', 'w') as f:
            w = csv.writer(f)
            w.writerow('id type lat lon'.split())

            for a in c.get_assets():
                w.writerow([a.assetUid, a.assetType, a.lat, a.lon])

    def test_get_locations(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        locations = list(c.get_locations())

        self.assertTrue(len(locations) > 900)

        for l in locations[:5]:
            print('----')
            print(l.locationType, l.locationUid)
            # print(l.data)
            # print(l.detail)
            for a in l.assets:
                print('   ', a)

    def test_location_events(self):
        from datetime import datetime

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        locations = list(c.locations)

        start = c.tz.localize(datetime(2019, 2, 1, 11, 0, 0))
        end = c.tz.localize(datetime(2019, 2, 1, 14, 0, 0))

        print(locations[100].events('PKIN', start, end))

    def test_nodes(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        for n in c.nodes:
            print(n)
            for c in n.children:
                print('  ', c)

    def test_walkways(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        for n in c.parking_zones:
            print(n)
            for c in n.assets:
                print('  ', c)

    def test_pkin_events(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

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

        c = CityIq(Config(config_file, cache_dir='/tmp'))

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

        self.assertEquals(2061, len(events))
        self.assertEquals(1549330201799, min_ts)
        self.assertEquals(1549331099575, max_ts)

    def test_async_events(self):

        c = CityIq(Config(config_file, cache_dir='/tmp'))

        for e in c.events_async():
            print(e)

    def test_scrape_events_1(self):
        from datetime import datetime
        from cityiq.scrape import get_events
        import json

        logging.basicConfig(level=logging.INFO)
        token_logger.setLevel(logging.DEBUG)
        scrape_logger.setLevel(logging.DEBUG)

        config = Config(config_file, cache_dir='/tmp')

        r = get_events(config, datetime(2019, 2, 5, 12, 0, 0), 1 * 60 * 60, ['PKIN', 'PKOUT'])

        with open('/tmp/results.json', 'w') as f:
            json.dump(r, f)

    def test_scrape_events(self):
        import pytz
        from datetime import datetime
        from cityiq.scrape import scrape_events

        logging.basicConfig(level=logging.INFO)
        token_logger.setLevel(logging.DEBUG)
        scrape_logger.setLevel(logging.DEBUG)
        api_logger.setLevel(logging.DEBUG)

        start_time = pytz.timezone('US/Pacific').localize(datetime(2019, 1, 1, 0, 0))

        config = Config(config_file)

        scrape_events(config, start_time, ['PKIN', 'PKOUT'])
