
import json
import logging
import threading
from pathlib import Path
from time import sleep
from datetime import date
from cityiq.api import CityIqObject
from requests import HTTPError
from typing import Dict, Tuple, Sequence

from .util import json_serial


logger = logging.getLogger(__name__)


def generate_days(start_time, end_time, include_end=False):
    """ Generate day ranges for the request


    :param start_time:
    :param end_time:
    :param include_end: If True, range will include end date, if False, it will stop one day before
    :return:
    """


    from dateutil.relativedelta import relativedelta

    d1 = relativedelta(days=1)

    st = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    et = end_time.replace(hour=0, minute=0, second=0, microsecond=0)

    if include_end is True:
        et = et + d1

    while st < et:
        yield st
        st += d1

class EventTask(object):
    """Base class for operations on a single object, event type and day. These tasks
    can be run in parallel and be subclassed to provide specific operations. """

    def __init__(self, access_object: CityIqObject, event_type, dt: date):

        self.access_object = access_object
        self.event_type = event_type
        self.dt = dt

        self.cache_file = self.access_object.cache_file(None, self.event_type, self.dt)

        self.processed = False
        self.downloaded = None # True or false depending on wether in cache.

        self.http_errors = 0
        self.errors = 0


    def __str__(self):
        return f"<{self.access_object} {self.event_type} {self.dt}>"

    def exists(self):
        return self.cache_file.exists()

    @classmethod
    def make_tasks(cls, objects: Sequence[CityIqObject], event_types: Sequence[str],
                   start_date: date, end_date: date):

        if isinstance(event_types, str):
            event_types = [event_types]

        for dt in generate_days(start_date, end_date):
            for o in objects:
                for et in event_types:
                    yield cls(o, et, dt)

    def run(self):
        raise NotImplementedError

class DownloadTask(EventTask):
    """An event task that downloads the events for a single location or asset, day and event type"""

    def robust_download(self):
        """
        Get the events of one type
        :param start_time:
        :param span:  time span in seconds
        :param event_type:
        :param tz_name:
        :return:
        """
        #logger.debug(f"Run fetch task {str(self)}")

        delay = 5
        last_exception = None
        for i in range(5):  # 5 retries on errors
            try:

                r = self.access_object.get_events_day(self.event_type, self.dt)

                break
            except HTTPError as e:
                logger.error('{} Failed. Retry in  {} seconds: {}'.format(str(self), delay, e))
                err = {
                    'location': self.access_object.uid,
                    'event_type': self.event_type,
                    'dt': self.dt,
                    'request_url': e.request.url,
                    'request_headers': dict(e.request.headers),
                    'response_headers': dict(e.response.headers),
                    'response_body': e.response.text
                }

                fn = '{}-{}-{}'.format(self.access_object.uid, self.event_type, self.dt.isoformat())

                p = Path(self.access_object.client.config.cache_errors).joinpath(fn)

                if not p.parent.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)

                with p.open('w') as f:
                    json.dump(err, f, default=json_serial, indent=4)

                delay *= 2 # Delay backoff
                delay = delay if delay <= 60 else 60
                sleep(delay)
                self.http_errors += 1
                last_exception = e
            except Exception as e:
                self.http_errors += 1
                logger.error(f"Error '{type(e)}: {e}' for {self.access_object}")
                last_exception = e
        else:
            if last_exception:
                logger.error(f"{last_exception} Giving up.")
                raise last_exception

        #logger.debug(f"Finished fetch task {str(self)}")

        d = {'dt': self.dt,
             'obj_type': str(type(self.access_object)),
             'obj_uid': self.access_object.uid,
             'event_type': self.event_type,
             'response': r}

        return d


class DataframeTask(EventTask):

    def run(self):

        import pandas as pd
        try:
            from pandas import json_normalize
        except ImportError:
            from pandas.io.json import json_normalize

        try:
            d = self.cache_file.read()
            return json_normalize(d)
        except Exception as e:
            print(f"Error '{type(e)}: {e}' in {self.cache_file.path}")
            return None


class DownloadDataframeTask(DownloadTask):

    def run(self):

        import pandas as pd
        try:
            from pandas import json_normalize
        except ImportError:
            from pandas.io.json import json_normalize

        try:
            self.robust_download()
            d = self.cache_file.read()
            return json_normalize(d)
        except Exception as e:
            print(f"Error '{type(e)}: {e}' in {self.cache_file.path}")
            return None


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
