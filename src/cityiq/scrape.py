# -*- coding: utf-8 -*-
"""
Scrape and store events from the API
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from .api import CityIq

logger = logging.getLogger(__name__)


class EventScraper(object):

    def __init__(self, config, start_time, event_types):

        self.config = config
        self.start_time = start_time.replace(minute=0, second=0)
        self.event_types = event_types

        self.cache = Path(self.config.events_cache)

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

        r = list(c.events(start_time=start_time, span=span, event_type=event_type))

        return r

    async def _get_events(self, start_time, span):
        """
        Async get of all types of events.
        """

        ts = start_time

        max_span = 15 * 60

        q, rem = divmod(span, max_span)

        spans = [max_span] * q

        if rem:
            spans += [rem]

        loop = asyncio.get_event_loop()
        futures = []

        for span in spans:
            d = timedelta(seconds=span)
            for event_type in self.event_types:
                futures.append(loop.run_in_executor(None, self.get_type_events, ts.timestamp(), span, event_type))
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

        for i in range(4):
            try:
                return self.get_events(start_time, span)
            except HTTPError as e:
                if e.response.status_code == requests.codes.SERVICE_UNAVAILABLE:  # 503
                    logger.debug(f"ERROR {e}: will try again after {sleep_time} seconds")
                    sleep(sleep_time)
                    sleep_time *= 2
                    continue
                else:
                    raise

    def _make_filename(self, st):

        fn_base, _ = str(st.replace(tzinfo=None).isoformat()).split(':', 1)

        fn = f'{fn_base}_{"_".join(sorted(self.event_types))}.json'

        return self.cache.joinpath(fn)

    def yield_file_names(self):

        d = timedelta(hours=1)

        st = self.start_time

        while st < datetime.now().astimezone(self.start_time.tzinfo):
            fn_path = self._make_filename(st)
            yield st, fn_path, fn_path.exists()

            st += d

    def scrape_events(self):

        logger.debug("scrape: Starting at {} for events {}".format(self.start_time, self.event_types))

        for st, fn_path, exists in self.yield_file_names():
            if not exists:
                logger.debug(f"{fn_path}: fetching")

                r = self.try_get_events(st, 1 * 60 * 60)

                with fn_path.open('w') as f:
                    json.dump(r, f)

                logger.debug(f"{fn_path}: wrote")

            else:
                logger.debug(f"{fn_path}: exists")

    def iterate_records(self):

        for st, fn_path, exists in self.yield_file_names():
            if exists:
                with fn_path.open() as f:
                    for e in json.load(f):
                        yield e

    def pair(self):
        """Yield paired events, consisting of a locationUid, time in and time out"""
        import pandas as pd
        from operator import itemgetter
        from tqdm import tqdm

        keys = ['timestamp', 'locationUid', 'eventType']
        ig = itemgetter(*keys)

        rows = [ig(e) for e in self.iterate_records()]
        df = pd.DataFrame(rows, columns=keys)
        df['timestamp'] = pd.to_datetime(df.timestamp, unit='ms')

        g = df.sort_values('timestamp').groupby('locationUid')

        def yield_clean_events(df):
            """Clean the events by removing duplicates.
            In a string of duplicated events for a single location -- such as multiple PKOUT,
            yield only the last one. """

            events = [(r.eventType, r.timestamp) for _, r in group.iterrows()]

            events = list(sorted(events, key=lambda r: r[1])) + ['END']

            found_in = False

            for i in range(len(events) - 1):
                event = events[i]
                next_event = events[i + 1]

                if not found_in:
                    if event[0] == 'PKIN':
                        found_in = True
                    else:
                        continue

                if event[0] != next_event[0]:
                    yield event

        def yield_debounced_events(events):

            last_in = None

            for e in events:
                if last_in is None and e[0] == 'PKIN':
                    last_in = e[1]
                    yield e

                elif last_in is not None and e[0] == 'PKOUT' and (e[1] - last_in).seconds > 2 * 60:
                    last_in = None
                    yield e

        def yield_paired_events(events):

            last = None

            for e in events:
                if e[0] == 'PKIN':
                    assert last is None
                    last = e
                elif e[0] == 'PKOUT':
                    assert last[0] == 'PKIN'
                    yield [last[1], e[1]]
                    last = None

        def convert_group_frame(group):

            events = [e for e in yield_paired_events(yield_debounced_events(yield_clean_events(group)))]

            t = pd.DataFrame({'locationUid': gname, 'pkin': [e[0] for e in events], 'pkout': [e[1] for e in events]})

            if len(t):
                t['duration'] = ((t['pkout'] - t['pkin']).dt.seconds / 60).round(0).astype(int)

            return t

        frames = []
        for gname, _ in tqdm(g):
            group = g.get_group(gname)
            frames.append(convert_group_frame(group))

        df = pd.concat(frames, sort=True, ignore_index=True)

        df['duration'] = (df.pkout - df.pkin).dt.seconds

        return df
