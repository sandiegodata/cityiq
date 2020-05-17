# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

"""



"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import collections
from cityiq.iterate import EventIterator
from cityiq.util import grouper

from .api import CityIqObject

logger = logging.getLogger(__name__)


class AsyncFetchRunner(object):
    """Fetch events asynchronously, using multiple workers """

    def __init__(self, config,  objects, event_types, start_time, end_time, max_workers=4):

        self.config = config
        self.objects = objects
        self.event_types = event_types if isinstance(event_types, collections.Iterable) else [event_types]
        self.start_time = start_time
        self.end_time = end_time

        self.max_workers = max_workers

        self.pool = ThreadPoolExecutor(max_workers=max_workers)

        self.processed = 0
        self.wrote = 0
        self.errors = 0
        self.existed = 0

        self.err_dir = Path(self.config.cache_errors).joinpath('scrape_errors')
        self.err_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_events(self, task_id, ciq_obj: CityIqObject, event_type, start_time, end_time):

        def _run():
            return ciq_obj.get_fetch_task(event_type, start_time, end_time).run()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.pool, _run)

    async def _get_events(self, objects=None):
        """
        Async get of all types of events.
        """

        futures = []
        task_id = 0

        ei = EventIterator(self.config, self.event_types, objects=self.objects,
                           start_time=self.start_time, end_time=self.end_time)

        for object, st, et, event_type, is_short in ei.generate_file_frames():
            futures.append(asyncio.ensure_future(self.fetch_events(task_id, object, event_type, st, et)))
            task_id += 1

        return await asyncio.gather(*futures)

    def get_events(self):

        loop = asyncio.get_event_loop()

        for objects in grouper(4, self.objects):
            results = loop.run_until_complete(self._get_events(objects))
            yield from results


class PedLocationEventScraper(AsyncFetchRunner):
    '''Generate rows for pedestrian events'''

    def __init__(self, config, locations, start_time, end_time, max_workers=4, pre_cb=None, post_cb=None):
        super().__init__(config, locations, ['PEDEVT'], start_time, end_time, max_workers, pre_cb, post_cb)

    def generate_rows(self):

        yield 'timestamp location_uid direction count speed'.split()

        for r in self.generate_records():

            m = r.get('measures', {})

            if m.get('pedestrianCount', 0) > 0:
                yield r['timestamp'], r['locationUid'], \
                      m['direction'], m['pedestrianCount'], m['speed']

            if m.get('counter_direction_pedestrianCount', 0) > 0:
                yield r['timestamp'], r['locationUid'], \
                      m['counter_direction'], m['counter_direction_pedestrianCount'], m['counter_direction_speed']

    def cache_csv_files(self, force=False):

        from tqdm.autonotebook import tqdm

        for l in tqdm(self.locations, desc='Cache CSV Files'):

            s = PedLocationEventScraper(self.config, l, self.start_time, self.end_time)

            fn = s.make_csv_file_name(l, 'PEDEVT')

            if not fn.exists() or force:
                df = s.dataframe()

                df.to_csv(fn, index=False)

    def cached_filenames(self):

        def _yield_file_names():
            for l in self.locations:
                fn = self.make_csv_file_name(l, 'PEDEVT')
                if fn.exists:
                    yield fn

        return list(_yield_file_names())

    def cached_dataframe(self, limit=None):

        from tqdm.autonotebook import tqdm
        import pandas as pd

        frames = []

        for i, l in enumerate(tqdm(self.locations, desc='Concat dataframe')):

            fn = self.make_csv_file_name(l, 'PEDEVT')

            if fn.exists():
                frames.append(pd.read_csv(fn, dtype={'location_uid': str}))

                if limit is not None and i > limit:
                    break

        return pd.concat(frames).reset_index()
