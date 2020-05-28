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

    def test_location_events_day(self):
        # api_logger.setLevel(logging.DEBUG)

        location_uids = ['09a66ff9a2c0cb63106fe0054412c2af', '0d152fbd26c5baad229556c01d3eb43b',
                         '0d1vvenvsrp7jgi27jvx']

        c = CityIq(self.config)

        locations = [c.get_location(uid) for uid in location_uids]

        # By individual days:

        events = []

        for day in ['2019-01-01', '2019-01-02']:
            for i, l in enumerate(locations):
                events += l.get_events_day('PKIN', day)

        n_events_indv = len(events)

        self.assertGreater(n_events_indv, 600)

        # By individual days, no cache:

        events = []

        for day in ['2019-01-01', '2019-01-02']:
            for i, l in enumerate(locations):
                events += l.get_events_day('PKIN', day, use_cache=False)

        self.assertEqual(n_events_indv, len(events))

        # One multi-day request
        events = []
        for i, l in enumerate(locations):
            events += l.get_events('PKIN', '2019-01-01', '2019-01-03')

        n_events_mult = len(events)
        self.assertGreater(n_events_mult, 600)

        self.assertEqual(n_events_indv, n_events_mult)

    def test_cached_events_day(self):
        # This should run fast after the first time.

        api_logger.setLevel(logging.DEBUG)

        location_uids = ['09a66ff9a2c0cb63106fe0054412c2af', '0d152fbd26c5baad229556c01d3eb43b',
                         '0d1vvenvsrp7jgi27jvx']

        c = CityIq(self.config)

        locations = [c.get_location(uid) for uid in location_uids]

        # By individual days:

        events = []

        for day in ['2019-01-01', '2019-01-02']:
            for i, l in enumerate(locations):
                events += l.get_events_day('PKIN', day, use_cache=True)

        n_events_indv = len(events)

        self.assertGreater(n_events_indv, 600)
