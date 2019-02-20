"""

API objects are the primary way to get access to assets and events. :py:class:`CityIq` is the top level access
object. The API offers access to Locations, Events and Events.

Typically, you will construct :py:class:`CityIq` from a :py:class:`Config`. If a configuration is not specific,
the system will look for the file in default locations. You can also override individual configuration parameters
with keyword arguments to the constructor.

Metadata Access
---------------

Metadata, for both locations and assets, can be fetched with property accessors. The bounding box for the queries can
be set in the configuration, or on the  :py:class:`CityIq` constructor.

The asset metadata properties are:

- :py:attr:`CityIq.assets` : All assets
- :py:attr:`CityIq.nodes` : Nodes, the parents for other assets on a pole
- :py:attr:`CityIq.cameras` : All assets
- :py:attr:`CityIq.em_sensors` : ?
- :py:attr:`CityIq.env_sensors` : Environmental sensors

The location metadata properties are:

- :py:attr:`CityIq.locations` : All locations
- :py:attr:`CityIq.walkways` :
- :py:attr:`CityIq.parking_zones` :
- :py:attr:`CityIq.traffic_lane` :

Events can be fetched with :py:func:`cityiq.api.CityIq.events`

Each of these acessor properties or functions returns a generator that generates objects of a specific type,
one base class for each of Locations, Assets or Events:

- :py:class:`Asset`
- :py:class:`Location`
- :py:class:`Event`

.. code-block:: python

    bbox = '32.718987:-117.174244,32.707356:-117.154850'

    c = CityIq(bbox=bbox) # Use default config, override bbox

    # Get Locations
    locations = list(c.locations)

    # Get the assets at this location:
    for location in locations:
        do_something_with(location.assets



"""

import datetime
import logging
import threading
import time

import pytz
import requests

from .config import Config
from .exceptions import CityIqError, ConfigurationError

logger = logging.getLogger(__name__)


class CityIqObject(object):

    def __init__(self, client, data):
        self.client = client
        self.data = data

    def __getattr__(self, item):
        try:
            return self.data[item]
        except KeyError:
            raise AttributeError(item)

    @property
    def geometry(self):
        """Return a Shapely polygon for the coordinates"""
        from shapely.geometry import Point, Polygon, LineString

        def numify(e):
            a, b = e.split(':')
            return float(b), float(a)

        if not hasattr(self, 'coordinatesType') or self.coordinatesType == 'GEO':

            vertices = [numify(e) for e in self.coordinates.split(',')]

            if len(vertices) == 1:
                return Point(vertices)
            elif len(vertices) == 2:
                return LineString(vertices)
            else:
                return Polygon(vertices)

    def __str__(self):
        return "<{}: {}>".format(type(self).__name__, self.data)


class Asset(CityIqObject):
    detail_url_suffix = '/v2/metadata/assets/{}'
    locations_url_suffix = '/v2/metadata/assets/{}/locations'
    children_url_suffix = '/v2/metadata/assets/{}/subAssets'

    row_header = 'assetUid assetType parentAssetUid mediaType events geometry'.split()

    # observed values for the assetType field
    types = ['NODE', 'EM_SENSOR', 'MIC', 'ENV_SENSOR', 'CAMERA']

    # Map asset types to subclasses
    dclass_map = {'NODE': 'NodeAsset',
                  'CAMERA': 'CameraAsset',
                  'EM_SENSOR': 'EmSensorAsset',
                  'XENV_SENSOR': 'EnvSensorAsset',
                  'MIC': 'MicSensorAsset'
                  }

    def __new__(cls, *args, **kwargs):

        dclass_name = Asset.dclass_map.get(args[1]['assetType'], Asset.__name__)  # probably fragile

        dclass = globals()[dclass_name]

        obj = super(CityIqObject, cls).__new__(dclass)

        return obj

    @property
    def lat(self):
        return self.coordinates.split(':')[0]

    @property
    def lon(self):
        return self.coordinates.split(':')[1]

    @property
    def detail(self):
        """Asset details"""
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        return Asset(self.client, r.json())

    @property
    def parent(self):
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.parentAssetUid)

        r = self.client.http_get(url)

        return Asset(self.client, r.json())

    @property
    def locations(self):
        """Assets at this location"""
        url = self.client.config.metadata_url + self.locations_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        for e in r.json()['locations']:
            yield Location(self.client, e)

    @property
    def children(self):
        """Sub assets of this asset"""
        url = self.client.config.metadata_url + self.children_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        for e in r.json()['assets']:
            yield Asset(self.client, e)

    @property
    def row(self):
        """Return most important fields in a row format"""
        from operator import attrgetter

        def evt_list(events):
            return ','.join(sorted(set(events or [])))

        ag = attrgetter(*Asset.row_header[:-2])

        return ag(self) + (evt_list(self.eventTypes), self.geometry)


class NodeAsset(Asset):
    pass


class CameraAsset(Asset):
    pass


class EnvSensorAsset(Asset):
    pass


class EmSensorAsset(Asset):
    pass


class MicSensorAsset(Asset):
    pass


class Location(CityIqObject):
    detail_url_suffix = '/v2/metadata/locations/{}'
    assets_url_suffix = '/v2/metadata/locations/{}/assets'
    events_url_suffix = '/v2/locations/{locationUid}/events?eventType={eventType}&startTime={startts}&' \
                        'endTime={endts}'

    row_header = 'locationUid locationType parentLocationUid  geometry'.split()

    # observed values for the assetType field
    types = ['WALKWAY', 'TRAFFIC_LANE', 'PARKING_ZONE']

    # Map asset types to subclasses
    dclass_map = {
        'WALKWAY': 'WalkwayLocation',
        'TRAFFIC_LANE': 'TrafficLaneLocation',
        'PARKING_ZONE': 'ParkingZoneLocation'
    }

    def __new__(cls, *args, **kwargs):
        dclass_name = Location.dclass_map.get(args[1]['locationType'], Location.__name__)  # probably fragile

        dclass = globals()[dclass_name]

        obj = super(CityIqObject, cls).__new__(dclass)

        return obj

    @property
    def detail(self):
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.locationUid)

        r = self.client.http_get(url)

        return r.json()

    @property
    def assets(self):
        """Assets at this location"""
        url = self.client.config.metadata_url + self.assets_url_suffix.format(self.locationUid)

        r = self.client.http_get(url)

        for e in r.json()['assets']:
            yield Asset(self.client, e)

    def events(self, eventType, start_time, end_time=None, span=None, ago=None):
        start_time, end_time = se_time(self, start_time, end_time, ago, span)

        url = self.client.config.metadata_url + self.format(
            locationUid=self.locationUid, eventType=eventType,
            startts=start_time.timestamp() * 1000, endts=end_time.timestamp() * 100
        )

        r = self.client.http_get(url)

        return r.json()

    @property
    def row(self):
        """Return most important fields in a row format"""
        from operator import attrgetter

        ag = attrgetter(*Location.row_header[:-1])

        return ag(self) + (self.geometry,)


class WalkwayLocation(Location):
    pass


class TrafficLaneLocation(Location):
    pass


class ParkingZoneLocation(Location):
    pass


class Event(CityIqObject):
    types = ['PKIN', 'PKOUT', 'PEDEVT', 'TFEVT', 'TEMPERATURE', 'PRESSURE', 'ORIENTATION', 'METROLOGY', 'HUMIDITY',
             'ENERGY_TIMESERIES', 'ENERGY_ALERT']


class EventWorker(threading.Thread):
    """Thread worker for websociet events"""

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


def current_time():
    '''Return the epoch time in miliseconds'''
    return int(round(time.time() * 1000, 0))


def time_ago(days=None, hours=None, minutes=None, seconds=None):
    t = time.time()

    if seconds:
        t -= seconds

    if minutes:
        t -= minutes * 60

    if hours:
        t -= hours * 60 * 60

    if days:
        t -= days * 60 * 60 * 26

    return int(round(t * 1000, 0))


def se_time(start_time=None, end_time=None, ago=None, span=None):
    if start_time:
        try:
            int(start_time)
        except TypeError:
            start_time = start_time.timestamp()

    if end_time:
        try:
            int(end_time)
        except TypeError:
            end_time = end_time.timestamp()

    if ago and span:
        raise CityIqError("Specify either age or span, but not both")

    if ago and not end_time:
        raise CityIqError("If age is specified, end_time must be also")

    if span and not start_time:
        raise CityIqError("If span is specified, start_time must be also")

    if not end_time:
        if start_time and span:
            end_time = (start_time + span) * 1000
        else:
            end_time = current_time()
    else:
        end_time = int(end_time * 1000)

    if not start_time:
        if ago:
            start_time = end_time - (ago * 1000)

        else:
            start_time = time_ago(minutes=15)
    else:
        start_time = int(start_time * 1000)

    return int(start_time), int(end_time)


class CityIq(object):
    assets_search_suffix = '/v2/metadata/assets/search'
    locations_search_suffix = '/v2/metadata/locations/search'

    events_url = '/v2/locations/events?bbox={bbox}&locationType={location_type}&eventType={event_type}&startTime={' \
                 'start_time}&endTime={end_time}&pageSize=100'

    def __init__(self, config=None, **kwargs):

        if config:
            self.config = config
        else:
            self.config = Config(**kwargs)

        self._token = None

        self.tz = pytz.timezone(self.config.timezone)

    @property
    def token(self):

        from .token import get_cached_token, get_token

        if not self._token:

            if self.config.cache_dir:
                self._token = get_cached_token(self.config.cache_dir, self.config.uaa_url,
                                               self.config.client_id, self.config.secret)

            else:
                self._token = get_token(self.config.uaa_url, self.config.client_id, self.config.secret)

        return self._token

    def http_get(self, url, zone=None, params=None, *args, **kwargs):

        zone = zone if zone else self.config.default_zone

        if params:
            # Not using the requests param argument b/c it will urlencode, and these query
            # parameters can't be url encoded.
            url = url + '?' + "&".join("{}={}".format(k, v) for k, v in params.items())

        headers = {
            'Authorization': 'Bearer ' + self.token
        }

        if zone:
            headers['Predix-Zone-Id'] = zone

        r = requests.get(url, headers=headers, *args, **kwargs)

        try:
            r.raise_for_status()
        except Exception:
            # print('url: ', url)
            # print('headers: ', headers)
            raise

        return r

    def _get_page(self, url, page, zone, bbox, query):

        params = {
            'page': page,
            'size': 20000,
            'bbox': bbox,
        }

        if query:
            params['q'] = "{}:{}".format(*query)

        r = self.http_get(url, zone, params)

        return r.json()

    def get_pages(self, url, query=None, zone=None, bbox=None):

        zone = zone if zone else self.config.zone

        if not zone:
            ConfigurationError("Must specify a zone, either in the get_assets call, or in the config")

        bbox = bbox if bbox else self.config.bbox

        if not zone:
            ConfigurationError("Must specify a bounding box (bbox) , either in the get_assets call, or in the config")

        page = 0
        index = 0
        while True:
            r = self._get_page(url, page, zone, bbox, query)

            content = r['content']

            for e in content:
                e['index'] = index
                e['page'] = page
                e['total'] = r['totalElements']
                yield e
                index += 1

            if r['last']:
                break

            page += 1

    def get_assets(self, device_type=None, zone=None, bbox=None):

        # A space ' ' is interpreted as querying for all records, while a blank '' is
        # an error.
        query = ('assetType', device_type if device_type is not None else ' ')

        for e in self.get_pages(self.config.metadata_url + self.assets_search_suffix,
                                query=query, zone=zone, bbox=bbox):
            yield Asset(self, e)

    @property
    def assets(self):
        """Return all system assets"""
        yield from self.get_assets(' ')

    @property
    def asset_dataframe(self):
        """Return assets in row form in a pandas Dataframe"""
        from pandas import DataFrame
        return DataFrame([e.row for e in self.assets], columns=Asset.row_header)

    @property
    def nodes(self):
        """Return all nodes"""
        yield from self.get_assets('NODE')

    @property
    def cameras(self):
        """Return camera assets"""
        yield from self.get_assets('CAMERA')

    @property
    def env_sensors(self):
        """Return environmental sensors"""
        yield from self.get_assets('ENV_SENSOR')

    @property
    def em_sensors(self):
        """Return some other kind of sensor. Electro-magnetic? """
        yield from self.get_assets('EM_SENSOR')

    @property
    def mics(self):
        """Return microphone assets"""
        yield from self.get_assets('MIC')

    def get_locations(self, location_type=None, zone=None, bbox=None):

        # A space ' ' is interpreted as querying for all records, while a blank '' is
        # an error.
        query = ('locationType', location_type if location_type is not None else ' ')

        for e in self.get_pages(self.config.metadata_url + self.locations_search_suffix,
                                query=query, zone=zone, bbox=bbox):
            yield Location(self, e)

    @property
    def locations(self):
        return self.get_locations(' ')

    @property
    def locations_dataframe(self):
        from pandas import DataFrame
        return DataFrame([e.row for e in self.locations], columns=Location.row_header)

    @property
    def walkways(self):
        return self.get_locations('WALKWAY')

    @property
    def traffic_lanes(self):
        return self.get_locations('TRAFFIC_LANE')

    @property
    def parking_zones(self):
        return self.get_locations('PARKING_ZONE')

    def _event_params(self, start_time, end_time, event_type, bbox=None):

        bbox = bbox or self.config.bbox

        if event_type in ('PKIN', 'PKOUT'):
            zone = self.config.parking_zone
            location_type = 'PARKING_ZONE'
        elif event_type == 'PEDEVT':
            location_type = 'WALKWAY'
            zone = self.config.pedestrian_zone
        elif event_type == 'TFEVT':
            location_type = 'TRAFFIC_LANE'
            zone = self.config.traffic_zone
        else:
            raise CityIqError("Unknown event type: '{}' ".format(event_type))

        params = {
            'bbox': bbox,
            'locationType': location_type,
            'eventType': event_type,
            'startTime': start_time,
            'endTime': end_time,
            'pageSize': 20000
        }

        return zone, params

    def _events_page(self, start_time, end_time, bbox, event_type):

        events_url = '/v2/locations/events'

        zone, params = self._event_params(start_time, end_time, event_type, bbox=bbox)

        r = self.http_get(self.config.event_url + events_url, params=params, zone=zone)

        try:
            return r.json()
        except Exception:
            print(r.text)
            raise

    def events(self, start_time=None, end_time=None, age=None, span=None, bbox=None, event_type=' '):
        """

        :param start_time:
        :param end_time:
        :param age:  if start_time is not specified, the start time in terms of seconds before the end time
        :return:
        """

        start_time, end_time = se_time(start_time, end_time, age, span)

        logger.debug("Starting events start_time={} end_time={}, event_type={}".format(
            datetime.datetime.utcfromtimestamp(start_time / 1000),
            datetime.datetime.utcfromtimestamp(end_time / 1000),
            event_type
        ))

        page = 0
        while True:

            data = self._events_page(start_time, end_time, bbox, event_type)

            meta = data['metaData']

            if len(data['content']) == 0:
                break

            min_ts = 2 ** 64
            max_ts = 0

            for i, e in enumerate(data['content']):
                e['page'] = page
                e['page_item'] = i
                min_ts = min(min_ts, int(e['timestamp']))
                max_ts = max(max_ts, int(e['timestamp']))
                yield e

            # If the end time is not the end time we asked for then
            # run another request to get the rest of the events.
            start_time_r, end_time_r = int(meta['startTs']), int(meta['endTs'])

            assert (start_time_r == start_time)

            # 3*60== three minutes, the approximate settling time of events.  ( Or so I'm told ... )
            if end_time_r == end_time or min_ts == max_ts or (end_time - max_ts) / 1000 < 3 * 60:
                break

            assert end_time > end_time_r

            start_time = max_ts  # end_time_r

            page += 1

        logger.debug("Ending events")

    def events_async(self, events=["PKIN", "PKOUT"]):
        """Use the websocket to get events. The websocket is run in a thread, and this
        function is a generator that returns results. """
        from queue import Queue
        import json

        q = Queue()

        w = EventWorker(self, events, q)

        w.start()

        while True:
            item = q.get()
            if item is None:
                break
            yield json.loads(item)
            q.task_done()

    @property
    def total_bounds(self):
        """Return a bounding box for the system from all of the assets. This will be affected by the
        bbox set in the config, so it should usually be smaller than the one in the config"""
        assets = list(self.get_assets())

        lats = [a.lat for a in assets]
        lons = [a.lon for a in assets]

        return "{}:{},{}:{}".format(max(lats), max(lons), min(lats), min(lons))
