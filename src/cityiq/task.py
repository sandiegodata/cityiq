import logging
import logging
import threading
from datetime import date
from typing import Sequence

from cityiq.api import CacheFile
from cityiq.api import CityIqObject
from dateutil.relativedelta import relativedelta
from itertools import zip_longest

logger = logging.getLogger(__name__)


def ensure_date(v):
    try:
        return v.date()
    except AttributeError:
        return v


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


def generate_days(start_time, end_time, include_end=False):
    """ Generate day ranges for the request

    :param start_time:
    :param end_time:
    :param include_end: If True, range will include end date, if False, it will stop one day before
    :return:
    """

    d1 = relativedelta(days=1)

    try:
        st = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    except TypeError:
        # May b/c it is a date
        st = start_time

    try:
        et = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    except TypeError:
        et = end_time

    if include_end is True:
        et = et + d1

    while st < et:
        yield st, st + d1
        st += d1

def generate_months(start_time, end_time, include_end=False):
    """ Generate month ranges from the start time to the end time

    :param start_time:
    :param end_time:
    :param include_end: If True, range will include end date, if False, it will stop one day before
    :return:
    """

    m1 = relativedelta(months=1)

    st = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    et = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if include_end is True:
        et = et + m1

    while st < et:
        yield st, st + m1
        st += m1

def request_ranges(start_date, end_date, extant):

    extant = list(sorted([ ensure_date(v) for v in extant ]))

    required = list(sorted([ ensure_date(v[0]) for v in list(generate_days(start_date, end_date)) ]))


    d1 = relativedelta(days=1)

    # Group by will produces runs of dates that are in the requied list and
    # those that are. The
    from itertools import groupby
    request_dates = []
    for isin, g in groupby(required, key=lambda e: e in extant):
        g = list(g)
        if not isin:
            request_dates.append((min(g), max(g) + d1))

    return request_dates


class EventTask(object):
    """Base class for operations on a single object, event type and day. These tasks
    can be run in parallel and be subclassed to provide specific operations. """

    def __init__(self, access_object: CityIqObject, event_type, start_date:date, end_date: date):

        self.access_object = access_object
        self.event_type = event_type
        self.start_date = self.access_object.client.convert_time(start_date)
        self.end_date = self.access_object.client.convert_time(end_date)

        self.processed = False
        self.downloaded = None  # True or false depending on wether in cache.

        self.http_errors = 0
        self.errors = 0

    def __str__(self):
        return f"<{self.access_object} {self.event_type} {self.dt}>"

    def run(self):
        raise NotImplementedError()

    @classmethod
    def make_tasks(cls, objects: Sequence[CityIqObject], event_types: Sequence[str],
                   start_date: date, end_date: date):

        if isinstance(event_types, str):
            event_types = [event_types]

        for o in objects:
            for et in event_types:
                yield cls(o, et, start_date, end_date)

class DownloadTask(EventTask):

    def run(self):
        self.access_object.client.cache_events(self.access_object, self.event_type,
                                               self.start_date, self.end_date)

    @classmethod
    def make_tasks(cls, objects: Sequence[CityIqObject], event_types: Sequence[str],
                   start_date: date, end_date: date):

        # Break up the download date range into 10 day ranges.
        days = list(e[0] for e in generate_days(start_date, end_date))
        date_ranges = list(grouper(5, days))

        d1 = relativedelta(days=1)

        if isinstance(event_types, str):
            event_types = [event_types]

        for o in objects:
            for et in event_types:
                for days in date_ranges:
                    if days is None:
                        continue
                    days = [d for d in days if d] # Remove Nones

                    start = min(days)
                    end = max(days)+d1
                    yield cls(o, et, start, end)


class EventWorker(threading.Thread):
    """Thread worker for websocket events"""

    # Use this function as the entrypoint for generating async events
    @staticmethod
    def events_async(client, events=["PKIN", "PKOUT"]):
        """Use the websocket to get events. The websocket is run in a thread, and this
        function is a generator that returns results. """
        from queue import Queue
        import json
        from cityiq.task import EventWorker

        q = Queue()

        w = EventWorker(client, events, q)

        w.start()

        while True:
            item = q.get()
            if item is None:
                break
            yield json.loads(item)
            q.task_done()

    def __init__(self, client, events, queue) -> None:

        super().__init__()

        self.client = client
        self.events = events
        self.queue = queue

    def run(self) -> None:
        super().run()

        import websocket
        import json

        # websocket.enableTrace(True)

        # events = ["TFEVT"]

        if 'TFEVT' in self.events:
            zone = self.client.config.traffic_zone,
        else:
            zone = self.client.config.parking_zone

        headers = {
            'Authorization': 'Bearer ' + self.client.token,
            'Predix-Zone-Id': zone,
            'Cache-Control': 'no-cache'
        }

        def on_message(ws, message):
            self.queue.put(message)

        def on_close(ws):
            self.queue.put(None)

        def on_open(ws):
            msg = {
                'bbox': self.client.config.bbox,
                'eventTypes': self.events
            }

            ws.send(json.dumps(msg))

        ws = websocket.WebSocketApp(self.client.config.websocket_url + '/events',
                                    header=headers,
                                    on_message=on_message,
                                    on_close=on_close)
        ws.on_open = on_open

        try:
            ws.run_forever()
        except KeyboardInterrupt:
            self.queue.put(None)
