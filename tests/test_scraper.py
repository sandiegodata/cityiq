"""

"""

import logging
from pathlib import Path

from cityiq.api import CityIq, logger as api_logger
from cityiq.config import Config
from cityiq.task import logger as task_logger, generate_months, generate_days

from .support import CityIQTest

logging.basicConfig()


class TestScraper(CityIQTest):

    def setUp(self):
        #api_logger.setLevel(logging.DEBUG)
        task_logger.setLevel(logging.DEBUG)
        self.config = Config(Path(__file__).parent.joinpath())

    def test_generate_tasks(self):
        c = CityIq(self.config)

        locations = c.locations

        tasks = list(FetchTask.make_tasks(locations[:10], ['PKIN', 'PKOUT'],
                                     c.convert_time('2019-01-01'), c.convert_time('2019-04-11')))

        #for t in tasks:
        #    t.run()

        print(sum(t.exists() for t in tasks))

        self.assertEqual(2000,len(tasks))


    def test_async_scrape(self):
        from tqdm import tqdm
        c = CityIq(self.config)

        #task_logger.setLevel(logging.DEBUG)

        events = ['BICYCLE'] # '['PKIN', 'PKOUT']

        assets = list(c.assets_by_event(events))[:4]

        tasks = c.make_tasks(assets, events, '2020-01-01', '2020-01-10')

        df = c.events_dataframe(tasks)

        print(len(df))
        print(df.head().T)

    def test_generate_time(self):
        c = CityIq(self.config)
        st = c.convert_time('2019-01-01')
        et = c.convert_time('2020-01-01')

        for sm, em in generate_months(st, et):
            print(sm, em)
            for sd, ed in generate_days(sm, em):
                print ('    ', sd.date(), ed.date())


