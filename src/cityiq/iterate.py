# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE
"""



"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytz
from cityiq.util import event_type_to_locations
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta

from .api import CityIq

logger = logging.getLogger(__name__)

# Date of the last month
last_month = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz=None).replace(day=1)
next_month = last_month + relativedelta(months=1)


def convert_start_dt(dt):
    if dt == 'last':
        return last_month
    elif isinstance(dt, datetime):
        return dt
    else:
        tz = datetime.now(timezone.utc).astimezone().tzinfo
        return parse_dt(dt).replace(tzinfo=tz)


def convert_end_dt(dt):
    tz = datetime.now(timezone.utc).astimezone().tzinfo

    if dt == 'last':
        # scrape and replace only the last month
        return next_month
    elif isinstance(dt, datetime):
        return dt
    elif dt:
        return parse_dt(dt).replace(tzinfo=tz)
    else:
        # Only scrape up to the most recent full month
        return last_month


class EventIterator(object):

    def __init__(self, config, event_types, objects=None, start_time=None, end_time=None):
        """

        :param config:

        :param event_types:
        :param objects:
        :param start_time:
        :param end_time:
        """

        if objects:
            self._objects = objects if isinstance(objects, (list, tuple)) else [objects]
        else:
            self._objects = None

        self.config = config

        self.tz = pytz.timezone(self.config.timezone)

        # If we are processing the last month, it will be overwritten
        if start_time == 'last' and end_time == 'last':
            self.overwrite = True
        else:
            self.overwrite = False

        self.start_time = convert_start_dt(start_time or config.start_time)
        self.end_time = convert_end_dt(end_time)

        if not isinstance(event_types, (list, tuple)):
            event_types = [event_types]

        self.event_types = event_types

    @property
    def objects(self):

        if not self._objects:
            c = CityIq(self.config)
            self._objects = event_type_to_locations(c, self.event_types)

        assert self._objects is not None

        return self._objects

    @property
    def object_cache(self):

        sub_dir = self._objects[0].object_sub_dir
        return Path(Path(self.config.cache_objects)).joinpath(sub_dir)

    def request_months(self):
        """Generate month ranges for the request"""

        from dateutil.relativedelta import relativedelta

        m1 = relativedelta(months=1)

        st = self.start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        et = self.end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        while st < et + m1:
            yield st, st + m1
            st += m1

    def request_days(self):
        """Generate day ranges for the request"""

        from dateutil.relativedelta import relativedelta

        m1 = relativedelta(days=1)

        st = self.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        et = self.end_time.replace(hour=0, minute=0, second=0, microsecond=0)

        while st < et + m1:
            yield st, st + m1
            st += m1

    def generate_file_frames(self):
        """Yield location,time,event tuples for all of the files that would be scraped"""
        from dateutil.relativedelta import relativedelta

        d1 = relativedelta(days=1)

        today = self.tz.localize(datetime.now()).date()

        for object in self.objects:
            for st, et in self.request_days():
                for event_type in self.event_types:
                    yield object, st, et, event_type, et.date() - d1 >= today

    def list(self):

        if self.event_types and self.event_types[0]:
            yield from self.generate_file_names()
        else:

            yield from self.object_cache.glob('**/*.json')

    def generate_location_paths(self):
        '''Return all of the locations that have been previously downloaded for at least one monthly event file'''

        for group_code in self.object_cache.iterdir():
            if group_code.is_dir():
                for e in group_code.iterdir():
                    if e.is_dir():
                        yield

    def location_event_files(self, p):
        """For a location event file, return a structure holding all of the event file, organized by
         type and date"""

        from collections import defaultdict

        d = defaultdict(list)

        for e in p.glob('**/*.json'):
            year = e.parent.name
            month, event = e.stem.split('-')

            d[event].append(('{}{:02}'.format(year, int(month)), e))

        for k in d.keys():
            d[k] = sorted(d[k])

        return d

    def generate_location_files(self):
        for p in self.generate_location_paths():
            yield p, self.location_event_files(p)

    def generate_location_data(self, event_names):
        """Yield all of the data for events for each location"""

        if not isinstance(event_names, (list, tuple)):
            event_names = [event_names]

        for location_path, d in self.generate_location_files():
            for event_name, files in d.items():
                if event_name in event_names:
                    yield location_path.name, location_path, files

    def generate_records(self, locations=None):
        '''Dump all data as JSON lines records. Yields the events from each
        cached file'''

        for file in self.list():
            if file.exists():
                with file.open() as f:
                    d = json.load(f)
                    yield from d['events']

    def __iter__(self):
        '''Dump all data as a header and rows of data'''

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


class ParkingIterator(EventIterator):
    header = tuple('timestamp locationUid assetUid eventType'.split())

    def __init__(self, config, objects=None, start_time=None, end_time=None):
        super().__init__(config, ['PKIN', 'PKOUT'], objects, start_time, end_time)

    def _extract_row(self, rec):
        return (rec['timestamp'], rec['locationUid'], rec['assetUid'], rec['eventType'])

    def __iter__(self):
        '''Dump all data as a header and rows of data'''

        def iter_records():
            for file in self.list():
                if file.exists():
                    with file.open() as f:
                        d = json.load(f)
                        for e in d['events']:
                            yield e

        header_yielded = False

        for e in iter_records():

            if header_yielded is False:
                header_yielded = True
                yield self.header

            yield self._extract_row(e)


class PedestrianIterator(EventIterator):

    def __init__(self, config, objects=None, start_time=None, end_time=None):
        super().__init__(config, ['PEDEVT'], objects, start_time, end_time)

    header = tuple('timestamp locationUid assetUid direction speed count'.split())

    def _extract_row(self, rec):

        common = (rec['timestamp'], rec['locationUid'], rec['assetUid'])

        m = rec['measures']

        if float(m['pedestrianCount']) > 0:
            yield common + (m['direction'], float(m['speed']), float(m['pedestrianCount']))

        if float(m['counter_direction_pedestrianCount']) > 0:
            yield common + (m['counter_direction'], float(m['counter_direction_speed']),
                            float(m['counter_direction_pedestrianCount']))

    def generate_location_data(self):
        return super().generate_location_data(['PEDEVT'])

    def generate_csv_files(self):
        """Return extant csv aggregate files produced by ciq_agregate"""
        for d in self.generate_location_paths():
            p = d.joinpath('ped.csv')
            if p.exists():
                yield p

    def dataframe(self):
        """Return a dataframe of all cached CSV files"""

        import pandas as pd

        # the usecols is skipping the first column, the index

        return pd.concat([pd.read_csv(f) for f in self.generate_csv_files()])

    def __iter__(self):
        '''Dump all data as a header and rows of data'''

        def iter_records():
            for file in self.list():
                if file.exists():
                    with file.open() as f:
                        d = json.load(f)
                        for e in d['events']:
                            yield e

        header_yielded = False

        for e in iter_records():

            if header_yielded is False:
                header_yielded = True
                yield self.header

            yield from self._extract_row(e)
