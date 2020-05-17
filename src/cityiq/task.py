import json
import logging
import threading
from pathlib import Path
from time import sleep

from cityiq.api import CityIqObject
from requests import HTTPError

from .util import json_serial


logger = logging.getLogger(__name__)

class FetchTask(object):
    """A task for fetching from the CityIQ API, suitable for use with AsyncIO. It handles
    mulltiple retries and caching"""

    def __init__(self, access_object: CityIqObject, event_type, start_time, end_time, is_short = False, overwrite=False):

        self.access_object = access_object
        self.overwrite = overwrite
        self.is_short = False

        self.event_type = event_type
        self.start_time = start_time
        self.end_time = end_time

        self.config = self.access_object.client.config

        self.object_cache = Path(Path(self.config.cache_objects)).joinpath(self.access_object.object_sub_dir)

        self.processed = 0
        self.wrote = 0
        self.errors = 0
        self.existed = 0

        self.cache_name = access_object.cache_path(self.start_time, self.event_type, is_short)

        logger.debug(f"New fetch task {self.cache_name}")

    def run(self):
        """
        Get the events of one type
        :param start_time:
        :param span:  time span in seconds
        :param event_type:
        :param tz_name:
        :return:
        """
        logger.debug(f"Run fetch task {self.cache_name}")

        if self.make_task_path(self.event_type, self.start_time, self.end_time) is False:
            return False, self.cache_name

        delay = 5
        last_exception = None
        for i in range(5):  # 5 retries on errors
            try:
                r = self.access_object.get_events(self.event_type, self.start_time, self.end_time)
                break
            except HTTPError as e:
                logger.error('{} Failed. Retry in  {} seconpds: {}'.format(self.cache_name, delay, e))
                err = {
                    'location': self.access_object.uid,
                    'event_type': self.event_type,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'request_url': e.request.url,
                    'request_headers': dict(e.request.headers),
                    'response_headers': dict(e.response.headers),
                    'response_body': e.response.text
                }

                fn = 'loc-{}-{}-{}-{}'.format(self.access_object.uid, self.event_type, self.start_time.date(), self.end_time.date())

                with Path(self.access_object.client.config.cache_errors).joinpath(fn).open('w') as f:
                    json.dump(err, f, default=json_serial, indent=4)

                delay *= 2 # Delay backoff
                delay = delay if delay <= 60 else 60
                sleep(delay)
                self.errors += 1
                last_exception = e
        else:
            if last_exception:
                logger.error("{} Giving up.")
                raise last_exception

        d = {'start_time': self.start_time,
             'end_time': self.end_time,
             'obj_type': str(type(self.access_object)),
             'obj_uid': self.access_object.uid,
             'event_type': self.event_type,
             'events': r}

        self.write_results(d)

        return True, self.cache_name

    def make_task_path(self, event_type, start_time, end_time):
        """Create a task path for writing the results of the task, and return
        it if it does not exist. If it does, return False"""

        self.processed += 1

        if self.cache_name.exists() and not self.overwrite:
            logger.info("{} exists".format(str(self.cache_name)))
            self.existed += 1
            return False
        else:
            return self.cache_name

    def write_results(self, result):

        try:
            self.cache_name.parent.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Another thread may have created the directory
            pass
        except AttributeError:
            raise  # The token is not a Path

        last_exc = None
        for i in range(3):
            try:
                with self.cache_name.open('w') as f:
                    json.dump(result, f, default=json_serial)
                    break
            except FileNotFoundError:
                # Not sure what's going on with this error

                logger.error(f"File Not Found Error for {str(self.cache_name)}")
                sleep(5)

        else:
            raise last_exc

        self.wrote += 1
        logger.info("{} wrote".format(str(self.cache_name)))


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
