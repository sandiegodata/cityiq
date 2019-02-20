# -*- coding: utf-8 -*-
"""



"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from .api import CityIq
from .exceptions import CityIqError

logger = logging.getLogger(__name__)


class EventScraper(object):
    event_locations_dir = 'event-locations'

    def __init__(self, config, start_time, event_types, max_workers=None):

        self.config = config
        self.start_time = start_time.replace(minute=0, second=0)
        self.event_types = event_types

        self.cache = Path(self.config.events_cache)

        self.max_workers = max_workers

        if not self.cache.exists() or not self.cache.is_dir():
            raise CityIq("The cache dir ('{}') must exist and be a directory".format(self.cache))

    def get_type_events(self, start_time, span, event_type):
        """
        Get the events of one type
        :param start_time:
        :param span:  time span in seconds
        :param event_type:
        :param tz_name:
        :return:
        """

        assert span <= 15 * 60, span

        c = CityIq(self.config)

        r = list(c.events(start_time=int(start_time), span=span, event_type=event_type))

        return r

    async def _get_events(self, start_time, span):
        """
        Async get of all types of events.
        """
        import concurrent

        ts = start_time

        max_span = 15 * 60

        q, rem = divmod(span, max_span)

        spans = [max_span] * q

        if rem:
            spans += [rem]

        loop = asyncio.get_event_loop()
        futures = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for span in spans:
                d = timedelta(seconds=span)
                for event_type in self.event_types:
                    futures.append(loop.run_in_executor(pool, self.get_type_events, ts.timestamp(), span, event_type))
                ts = ts + d

        group = asyncio.gather(*futures)

        return await group

    def get_events(self, start_time, span):

        loop = asyncio.get_event_loop()

        results = loop.run_until_complete(self._get_events(start_time, span))

        return list(chain(*results))

    def try_get_events(self, start_time, span):
        """Run get_events and try to be resilient to some errors"""
        from requests.exceptions import HTTPError
        import requests
        from time import sleep
        sleep_time = 20

        last_e = None
        for i in range(4):
            try:
                return self.get_events(start_time, span)
            except HTTPError as e:
                if e.response.status_code == requests.codes.SERVICE_UNAVAILABLE:  # 503
                    logger.debug(f"ERROR {e}: will try again after {sleep_time} seconds")
                    sleep(sleep_time)
                    sleep_time *= 2
                    last_e = e
                    continue
                else:
                    raise
        else:
            raise last_e

    def _make_filename(self, st):

        fn_base, _ = str(st.replace(tzinfo=None).isoformat()).split(':', 1)

        fn = f'{fn_base}_{"_".join(sorted(self.event_types))}.json'

        return self.cache.joinpath(fn)

    def yield_file_names(self, start=None, end=None):

        d = timedelta(hours=1)

        if start is None:
            start = self.start_time

        if end is None:
            end = datetime.now().astimezone(self.start_time.tzinfo)

        while start < end:
            fn_path = self._make_filename(start)
            yield start, fn_path, fn_path.exists()

            start += d

    def yield_months(self):
        '''Yield the results of yield_file_names'''
        from dateutil.relativedelta import relativedelta

        this_month = self.start_time.replace(day=1)

        while this_month < datetime.now().astimezone(self.start_time.tzinfo):
            next_month = this_month + relativedelta(months=1)
            yield this_month, list(self.yield_file_names(this_month, next_month))

            this_month = next_month

    def scrape_events(self):

        logger.debug("scrape: Starting at {} for events {}".format(self.start_time, self.event_types))

        for st, fn_path, exists in self.yield_file_names():

            if not exists:
                logger.debug(f"{fn_path}: fetching")

                r = self.try_get_events(st, 1 * 60 * 60)

                with fn_path.open('w') as f:
                    json.dump(r, f)

                logger.debug(f"{fn_path}: wrote {len(r)} records")

            else:
                logger.debug(f"{fn_path}: exists")

    def iterate_records(self, records=None):
        """For a set of file name records ( from yield_file_names), yield event objects  """
        if records is None:
            records = self.yield_file_names()

        for st, fn_path, exists in records:
            try:
                if exists:
                    with fn_path.open() as f:
                        o = json.load(f)
                        for e in o:
                            yield e
            except Exception as e:
                raise CityIqError("Failed to load scraped file {} : {}".format(str(fn_path), e))

    def split_locations(self, use_tqdm=False):
        """Split the scraped event files into sperate files per month and location,
        which are required for later stages of processing. """

        from operator import itemgetter
        import pandas as pd

        keys = ['timestamp', 'locationUid', 'eventType']
        ig = itemgetter(*keys)

        if use_tqdm:
            from tqdm.auto import tqdm

        else:
            def tqdm(g, *args, **kwargs):
                yield from g

        cache = Path(self.config.cache_dir).joinpath(self.event_locations_dir)

        locations = set()

        for m in tqdm(list(self.yield_months()), desc='Months'):

            recs = []

            for r in self.iterate_records(tqdm(m[1], desc='Build dataframe')):
                recs.append(ig(r))

            if not recs:
                continue

            df = pd.DataFrame(recs, columns=keys).sort_values('timestamp')
            grp = df.groupby('locationUid')

            for name, frame in tqdm(grp, desc='Iterate groups'):
                locations.add(name)
                cache.joinpath(name).mkdir(parents=True, exist_ok=True)
                fn = cache.joinpath('{}/{}.csv'.format(name, m[0].date().isoformat()))
                frame.to_csv(fn)

    def iterate_splits(self, use_tqdm=False, locations=None):
        """Iterate over the splits produced by split_locations"""

        cache = Path(self.config.cache_dir).joinpath(self.event_locations_dir)

        if not locations:
            locations = [e.name for e in cache.glob('*')]

        if use_tqdm:
            from tqdm.auto import tqdm
            locations = tqdm(locations)

        for location in locations:
            locations_dir = cache.joinpath(location)
            if locations_dir.is_dir():
                yield location, [e for e in locations_dir.glob('*.csv')]
