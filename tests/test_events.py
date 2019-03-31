"""

"""

import logging

from cityiq.api import CityIq
from cityiq.api import logger as api_logger
from cityiq.config import Config
from cityiq.scrape import logger as scrape_logger
from cityiq.token import logger as token_logger

from .support import CityIQTest


class TestBasic(CityIQTest):

    def test_location_events(self):
        from datetime import datetime

        c = CityIq(Config(cache_dir='/tmp'))

        locations = list(c.parking_zones)

        start = c.tz.localize(datetime(2019, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 1, 31, 0, 0, 0))

        events = locations[100].events('PKIN', start, end)

        self.assertEqual(3537, len(events))

    def test_walkway_events(self):
        from datetime import datetime

        c = CityIq(Config(cache_dir='/tmp'))

        locations = list(c.walkways)

        start = c.tz.localize(datetime(2019, 1, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 1, 31, 0, 0, 0))

        events = locations[100].events('PEDEVT', start, end)

        self.assertEqual(15581, len(events))

        # Longer

        start = c.tz.localize(datetime(2018, 8, 1, 0, 0, 0))
        end = c.tz.localize(datetime(2019, 1, 31, 0, 0, 0))

        events = locations[50].events('PEDEVT', start, end)

        self.assertEqual(53676, len(events))

    def test_pkin_events(self):

        c = CityIq(Config(cache_dir='/tmp'))

        from datetime import datetime
        import pytz

        pacific = pytz.timezone('US/Pacific')

        ts = pacific.localize(datetime(2019, 2, 4, 17, 30, 0)).timestamp()

        events = c.events(start_time=ts, span=15 * 60, event_type='PKIN')

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

        self.assertEquals(2061, len(events))
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

        config = Config(cache_dir='/tmp')

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

        config = Config()

        scrape_events(config, start_time, ['PKIN', 'PKOUT'])

    def test_location_scrape(self):
        import pytz
        from cityiq.scrape import LocationEventScraper
        from datetime import datetime
        from cityiq import CityIq, Config

        config = Config(cache_dir='/tmp')

        c = CityIq(config)

        locations = list(c.parking_zones)  # [100:105]

        start_time = pytz.timezone('US/Pacific').localize(datetime(2018, 8, 1, 0, 0))
        end_time = pytz.timezone('US/Pacific').localize(datetime.now())

        print(len(locations))

        s = LocationEventScraper(config, locations, 'PKIN', start_time, end_time, max_workers=4)
        for r in s.get_events():
            print(len(r))
