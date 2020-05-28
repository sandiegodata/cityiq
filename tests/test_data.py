"""

"""

import logging

from cityiq.api import CityIq
from cityiq.task import DownloadDataframeTask, DownloadTask

from .support import CityIQTest

import pandas as pd
try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize

logging.basicConfig(level=logging.ERROR)


class TestData(CityIQTest):


    def load_frame_1(self):
        """Download multi-threaded, the combine synchronously."""

        events = ['BICYCLE']

        c = CityIq(self.config)

        assets = list(c.assets_by_event(events))[:10]

        tasks = c.make_tasks(DownloadTask, assets, events, '2020-01-01', '2020-01-11')

        frames = [json_normalize(task.cache_file.read()) for task, result in c.run_async(tasks)]

        df = pd.concat(frames)

        print(len(df))


    def load_frame_2(self):
        """DOwnload and convert to dataframe are both async"""

        events = ['BICYCLE']

        c = CityIq(self.config)

        assets = list(c.assets_by_event(events))[:10]

        tasks = c.make_tasks(DownloadDataframeTask, assets, events, '2020-01-01', '2020-01-11')

        frames = [result for task, result in c.run_async(tasks)]

        df = pd.concat(frames)

        print(len(df))


    def test_load_frame(self):

        self.load_frame_1()
        self.load_frame_2()


    def test_basic(self):
        events = ['BICYCLE']

        c = CityIq(self.config)

        assets = list(c.assets_by_event(events))

        tasks = c.make_tasks(assets, events, '2020-01-01', '2020-01-11')

        self.assertEqual(2270, len(tasks))

        import pandas as pd

        try:
            from pandas import json_normalize
        except ImportError:
            from pandas.io.json import json_normalize

        def load_frame(task):
            try:
                d = task.cache_file.read()
                return json_normalize(d)
            except Exception as e:
                print(f"Error {e} in {task.path}")
                return None

        #frames = [load_frame(task) for task, result in c.run_async(tasks) ]

        frames = [json_normalize(task.cache_file.read()) for task, result in c.run_async(tasks)]

        df = pd.concat(frames)

        print(len(df))

        print(df.head())
