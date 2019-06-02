# -*- coding: utf-8 -*-
"""



"""

import asyncio
import itertools
import json
import logging
from pathlib import Path
from time import sleep

from .api import CityIq

logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    from datetime import date, datetime

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class LocationEventScraper(object):
    '''Scrape events by location. Faster '''

    location_sub_dir = 'location'

    def __init__(self, config, locations, event_types, start_time, end_time, max_workers=4,
                 pre_cb=None, post_cb=None):

        from concurrent.futures import ThreadPoolExecutor

        if locations:
            self._locations = locations if isinstance(locations, (list, tuple)) else [locations]
        else:
            self._locations = None

        self.config = config
        self.start_time = start_time
        self.end_time = end_time

        if not isinstance(event_types, (list, tuple)):
            event_types = [event_types]

        self.event_types = event_types

        self.max_workers = max_workers

        self.pool = ThreadPoolExecutor(max_workers=max_workers)

        self.pre_cb = self.make_task_path if pre_cb is None else pre_cb
        self.post_cb = self.write_results if post_cb is None else post_cb

        self.processed = 0
        self.wrote = 0
        self.errors = 0
        self.existed = 0

        self.err_dir = Path(self.config.cache['errors']).joinpath('scrape_errors')
        self.err_dir.mkdir(parents=True, exist_ok=True)

    def _event_type_to_locations(self, c,  events):

        if set(events) & {'PKIN','PKOUT'}:
            locations = list(c.parking_zones)  # Get all of the locations
        elif set(events) & {'PEDEVT'}:
            locations = list(c.walkways)  # Get all of the locations
        elif set(events) & {'TFEVT'}:
            locations = list(c.traffic_lanes)  # Get all of the locations
        else:
            locations = []

        return locations

    @property
    def locations(self):

        if not self._locations:
            c = CityIq(self.config)
            return self._event_type_to_locations(c, self.event_types)

        return self._locations

    def request_months(self):
        """Generate task and file names"""

        from dateutil.relativedelta import relativedelta

        m1 = relativedelta(months=1)

        st = self.start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        et = self.end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        while st < et:
            yield st, st + m1
            st += m1

    async def fetch_events(self, task_id, location, event_type, start_time, end_time):

        def _fetch_events(location, event_type, start_time, end_time):
            """
            Get the events of one type
            :param start_time:
            :param span:  time span in seconds
            :param event_type:
            :param tz_name:
            :return:
            """

            from .api import Location
            from requests import HTTPError

            if self.pre_cb:
                token = self.pre_cb(task_id, location, event_type, start_time, end_time)
                if token is False:  # The file has already been fetched. Carry on.
                    return False, False, False
            else:
                token = None

            delay = 5
            last_exception = None
            for i in range(5):
                loc = Location(CityIq(self.config), location.data)  # Make a copy with new client

                try:
                    r = loc.events(event_type, start_time, end_time)
                    break
                except HTTPError as e:
                    logger.error('{} Failed. Retry in  {} seconpds: {}'.format(token, delay, e))
                    err = {
                        'location': location.locationUid,
                        'event_type': event_type,
                        'start_time': start_time,
                        'end_time': end_time,
                        'request_url': e.request.url,
                        'request_headers': dict(e.request.headers),
                        'response_headers': dict(e.response.headers),
                        'response_body': e.response.text
                    }

                    fn = 'loc-{}-{}-{}-{}'.format(location.locationUid, event_type, start_time.date(), end_time.date())

                    with self.err_dir.joinpath(fn).open('w') as f:
                        json.dump(err, f, default=json_serial, indent=4)

                    delay *= 2
                    delay = delay if delay <= 60 else 60
                    sleep(delay)
                    self.errors += 1
                    last_exception = e
            else:
                if last_exception:
                    logger.error("{} Giving up.")
                    raise last_exception

            d = {'start_time': start_time,
                 'end_time': end_time,
                 'locationUid': location.locationUid,
                 'event_type': event_type,
                 'events': r}

            if self.post_cb:
                self.post_cb(task_id, token, d)

            return task_id, token, d

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.pool, _fetch_events, location, event_type, start_time, end_time)

    def generate_file_frames(self, locations=None):
        """Yield location,time,event tuples for all of the files that would be scraped"""

        if locations is None:
            locations = self.locations

        for location in locations:
            for st, et in self.request_months():
                for event_type in self.event_types:
                    yield location, st, et, event_type

    def make_file_name(self, locationUid, start, event_type):
        prefix = locationUid[:2] if locationUid else 'none'
        return Path(self.config.cache['objects']).joinpath(self.location_sub_dir, '{}/{}/{}/{}-{}.json'
                                                    .format(prefix,locationUid, start.year, start.month, event_type))

    def make_csv_file_name(self, locationUid, event_type):
        return Path(self.config.cache_dir).joinpath(self.location_sub_dir, '{}/{}.csv'
                                                    .format(locationUid, event_type))

    def generate_file_names(self):

        def extract_location(location):
            try:
                return location.locationUid
            except AttributeError:
                return location

        for location, st, et, event_type in self.generate_file_frames():
            yield self.make_file_name(extract_location(location), st, event_type)

    def create_tasks(self, locations=None):

        futures = []
        task_id = 0

        for location, st, et, event_type in self.generate_file_frames(locations):
            futures.append(asyncio.ensure_future(self.fetch_events(task_id, location, event_type, st, et)))
            task_id += 1

        return futures

    async def _get_events(self, locations=None):
        """
        Async get of all types of events.
        """

        futures = self.create_tasks(locations)

        return await asyncio.gather(*futures)

    def get_events(self):

        loop = asyncio.get_event_loop()

        for locations in grouper(4, self._locations if self.locations else []):
            results = loop.run_until_complete(self._get_events(locations))
            yield from results

    def make_task_path(self, task_id, location, event_type, start_time, end_time):
        """Create a task path for writing the results of the task, and return
        it if it does not exist. If it does, return False"""

        p = self.make_file_name(location.locationUid, start_time, event_type)

        self.processed += 1

        if p.exists():
            logger.info("{} exists".format(str(p)))
            self.existed += 1
            return False
        else:
            return p

    def write_results(self, task_id, token, result):

        try:
            token.parent.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Another thread may have created the directory
            pass
        except AttributeError:
            raise # The token is not a Path

        last_exc = None
        for i in range(3):
            try:
                with token.open('w') as f:
                    json.dump(result, f, default=json_serial)
                    break
            except FileNotFoundError:
                # Not sure what's going on with this error

                logger.error(f"File Not Found Error for {str(token)}")
                sleep(5)

        else:
            raise last_exc

        self.wrote += 1
        logger.info("{} wrote".format(str(token)))



    def list_extant_locations(self):
        '''Return all of the locations that have been previously downloaded for at least one monthly event file'''

        p = Path(self.config.cache_dir).joinpath(self.location_sub_dir)

        return list(e.name for e in p.iterdir() if e.is_dir())

    def list(self):

        if self.event_types and self.event_types[0]:
            yield from self.generate_file_names()

        else:
            p = Path(self.config.cache_dir).joinpath(self.location_sub_dir)
            yield from p.glob('**/*.json')

    def generate_records(self, locations=None):
        '''Dump all data as JSON lines records'''

        for file in self.list():
            if file.exists():
                with file.open() as f:
                    d = json.load(f)
                    yield from d['events']

    def generate_rows(self):
        '''Dump all data as JSON lines records'''

        from operator import itemgetter

        ig = None

        def iter_files():
            for file in self.list():
                if file.exists():
                    with file.open() as f:
                        d = json.load(f)
                        for e in d['events']:
                            yield e

        for e in iter_files():
            e.update(e['properties'])
            e.update(e['measures'])
            del e['properties']
            del e['measures']

            if ig is None:
                ig = itemgetter(*sorted(e.keys()))
                yield tuple(sorted(e.keys()))

            yield ig(e)

    def dataframe(self):
        import pandas as pd

        rows = list(self.generate_rows())

        if rows:
            return pd.DataFrame(rows[1:], columns=rows[0])
        else:
            return None


class PedLocationEventScraper(LocationEventScraper):
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
