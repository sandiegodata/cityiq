# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE
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
import json
import logging
import pickle
from datetime import date, datetime
from pathlib import Path
from time import time

import pytz
import requests
from cityiq.util import event_to_zone
from cityiq.util import run_async
from dateutil.parser import parse
from slugify import slugify

from .config import Config
from .exceptions import ConfigurationError, TimeError, CityIqError
from .util import json_serial, log_message

logger = logging.getLogger(__name__)


class CityIqObject(object):

    def __init__(self, client, data, use_cache=True):
        self.client = client

        # The object is specified with a uid, so convert it to data.
        if isinstance(data, str):
            data = {self.uid_key: data}

        self.data = data
        self.use_cache = use_cache

    def __getattr__(self, item):
        try:
            return self.data[item]
        except KeyError:
            raise AttributeError(item)

    def update(self):
        """Make an uncached call to the API to replace the data in this object"""

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

    def get_fetch_task(self, event_type, start_time, end_time):
        from dateutil.relativedelta import relativedelta
        from .task import FetchTask

        d1 = relativedelta(days=1)

        today = self.client.tz.localize(datetime.datetime.now()).date()

        return FetchTask(self, event_type, start_time, end_time)

    @property
    def events_url(self):
        """Return the URL for fetching events, called from get_events() in the base class. """
        return self.client.config.event_url + self.events_url_suffix.format(uid=self.uid)

    def cache_file(self, fetch_func=None, event_type=None, dt=None, group=None):
        return CacheFile(self.client.config.cache_objects, self, fetch_func=fetch_func,
                         event_type=event_type, dt=dt, group=group)

    def write(self):
        """Write data to the cache"""
        self.cache_file().write(self.data)

    def get_events(self, event_type, start_time, end_time=None):
        start_time = self.client.convert_time(start_time)
        end_time = self.client.convert_time(end_time)

        return self.client._events(self.events_url, event_type, start_time, end_time, bbox=False)

    def get_day_cache_file(self, event_type, dt):
        from dateutil.relativedelta import relativedelta

        dt = self.client.convert_time(dt)

        d1 = relativedelta(days=1)

        start_time = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + d1

        def ff():
            r = self.client._events(self.events_url, event_type, start_time, end_time, bbox=False)
            return r

        return self.cache_file(ff, event_type, dt)

    def get_events_day(self, event_type, dt):
        """Get events for a single day, from the start of the day of the given date to the next day, exclusive"""

        return self.get_day_cache_file(event_type, dt).run()

    def __str__(self):
        return "<{}: {}>".format(type(self).__name__, self.data)


class CacheFile(object):
    """Represents a cached file of records for one location or asset, one type of event,
    and one day. Or, if the date and event type are omitted, just the information
    about an asset or location"""

    def __init__(self, cache_path, access_object, fetch_func=None, event_type=None, dt=None, group=None):
        """

        :param cache_path: Path to the base object cache
        :param access_object: An Asset or Location object
        :param event_type: Event type string
        :param dt: Date ( day )
        :param group:  If event type and dt are non, an extra path component for the cache file


        The `event_type` and `dt` values must either both both None, or both not none.
        If they are non-None, the cache file is for a single-da revent request response.
        If they are both None, the file is for a request related to the object, such as metadata

        """

        self._fetch_func = fetch_func
        self._cache_path = Path(cache_path)
        self._access_object = access_object
        self._event_type = event_type
        self._group = group
        self._dt = dt

        self.path  # Just check that it's ok

        self.today = self._access_object.client.convert_time('now').replace(hour=0, minute=0, second=0, microsecond=0)

        self._write = self._dt is None or self._dt < self.today  # Don't write cache for today.

    def run(self):

        assert self._fetch_func is not None, "Got None fetch_func"

        if self.exists():
            return self.read()
        else:
            v = self._fetch_func()
            self.write(v)
            return v

    @property
    def path(self):
        """The filesystem path to the cache file"""
        ao = self._access_object

        uid = ao.uid
        object_sub_dir = ao.object_sub_dir

        prefix = uid[:2] if uid else 'none'

        if self._dt is not None and self._event_type is not None and self._group is None:

            return self._cache_path.joinpath(
                Path(
                    f'{object_sub_dir}/{prefix}/{uid}/{self._event_type}/{self._dt.year}-{self._dt.month:02}/'
                    + f'{uid}-{self._dt.date().isoformat()}-{self._event_type}.json'))

        elif self._dt is None and self._event_type is None:

            file_name = 'object' if self._group is None else self._group

            return self._cache_path.joinpath(Path(f'{object_sub_dir}/{prefix}/{uid}/{file_name}.json'))
        else:
            raise CityIqError("Bad combination of event_type and dt: either both are None or both not None,"
                              "and group can't be used with them. "
                              "group={}, dt={}, event_type={}".format(self._group, self._dt, self._event_type))

    def exists(self):
        # TODO. Return false if the file is too old? At least for caching assets and locations
        return self.path.exists()

    def delete(self):
        if self.exists():
            return self.path.unlink()

    def read(self):
        """"""
        with self.path.open('r') as f:
            logger.info("Reading {}".format(str(self.path)))
            return json.load(f)

    def write(self, result):

        if not self._write:
            logger.info("Won't write for today {} or later {}".format(self.today, str(self.path)))
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Another thread may have created the directory
            pass
        except AttributeError:
            raise  # The token is not a Path

        with self.path.open('w') as f:
            json.dump(result, f, default=json_serial)

        logger.info("wrote {}".format(str(self.path)))


class Event(CityIqObject):
    types = ['PKIN', 'PKOUT', 'PEDEVT', 'TFEVT', 'TEMPERATURE', 'PRESSURE', 'ORIENTATION', 'METROLOGY', 'HUMIDITY',
             'ENERGY_TIMESERIES', 'ENERGY_ALERT']


class CityIq(object):
    object_sub_dir = 'object'  # Reset in sub dir
    assets_search_suffix = '/api/v2/metadata/assets/search'
    locations_search_suffix = '/api/v2/metadata/locations/search'
    events_url_suffix = '/api/v2/event/locations/events'

    asset_url_suffix = '/api/v2/metadata/assets/{uid}'
    location_url_suffix = '/api/v2/metadata/locations/{uid}'

    def __init__(self, config=None, cache_metadata=True, cache_events=True, **kwargs):
        CityIq
        if config:
            self.config = config
        else:
            self.config = Config(**kwargs)

        self._token = None

        self.tz = pytz.timezone(self.config.timezone)

        self.cache_metadata = cache_metadata
        self.cache_events = cache_events

        self.metadata_cache = Path(self.config.cache_meta)

        self.metadata_cache.mkdir(exist_ok=True, parents=True)

        self.object_cache = Path(Path(self.config.cache_objects))

        if self.cache_metadata and not self.metadata_cache.is_dir():
            raise ConfigurationError("Metadata cache '{}' is not a directory ".format(self.metadata_cache))

    def get_meta_cache(self, key):

        too_old_time = 60 * 60 * 24  # one day

        if not self.cache_metadata:
            return None

        key = slugify(key)

        p = self.metadata_cache.joinpath(key).with_suffix('.pkl')

        if p.exists():
            with p.open('rb') as f:

                if p.stat().st_mtime + too_old_time < time():
                    return None

                return pickle.load(f)

        else:
            return None

    def set_meta_cache(self, key, value):

        if not self.cache_metadata:
            return None

        key = slugify(key)

        p = self.metadata_cache.joinpath(key).with_suffix('.pkl')

        with p.open('wb') as f:
            pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)

    def clear_meta_cache(self):

        for e in self.metadata_cache.glob('*'):
            e.unlink()

    def convert_time(self, t):
        """Convert a variety of time formats into the millisecond format
        used by the CityIQ interface. Converts naieve times to the configured timezone"""

        now = datetime.now()

        def is_micros(v):
            """Return true if an integer time is in microseconds, by checking
            if the value is very large or small compared to the current time in seconds. """

            # if v is a CityIq time for now, a will be 1000
            a = v / now.timestamp()

            if a > 100 or a < 0.1:  # Both so I don't have to check which way the ratio goes ...
                return True

        if isinstance(t, (int, float)):
            if is_micros(t):
                dt = datetime.fromtimestamp(t / 1000)
            else:
                dt = datetime.fromtimestamp(t)
        elif isinstance(t, str):
            if t == 'now':  # Useless but consistent
                dt = now
            else:
                dt = parse(t)
        elif isinstance(t, (date, datetime)):
            dt = t

        elif t is None:
            dt = now
        else:
            raise TimeError(f"Unknown time value {t}, type: {type(t)}")

        try:
            return self.tz.localize(dt)
        except ValueError:
            # Already localized:
            return dt

    @property
    def token(self):

        from .token import get_cached_token, get_token

        if not self._token:

            if self.config.cache_meta:
                self._token = get_cached_token(self.config.cache_meta, self.config.uaa_url,
                                               self.config.client_id, self.config.secret)

            else:
                self._token = get_token(self.config.uaa_url, self.config.client_id, self.config.secret)

        return self._token

    def request_headers(self, zone=None):
        headers = {
            'Authorization': 'Bearer ' + self.token
        }

        zone = zone if zone else self.config.default_zone

        if zone:
            headers['Predix-Zone-Id'] = zone

        return headers

    def process_url(self, url, params):
        if params:
            # Not using the requests param argument b/c it will urlencode, and these query
            # parameters can't be url encoded.
            url = url + '?' + "&".join("{}={}".format(k, v) for k, v in params.items())

        return url

    def _http_get(self, url, zone=None, params=None, *args, **kwargs):

        url = self.process_url(url, params)

        logger.debug(url)

        r = requests.get(url, headers=self.request_headers(zone), *args, **kwargs)

        try:
            r.raise_for_status()
        except Exception as e:

            logger.error(log_message(r) + r.text)
            raise

        return r

    def http_get(self, url, zone=None, params=None, *args, **kwargs):
        return self._http_get(url, zone, params, *args, **kwargs)

    def _get_page(self, url, page, zone, bbox, query):

        params = {
            'page': page,
            'size': 2000,
            'bbox': bbox,
        }

        if query:
            params['q'] = "{}:{}".format(*query)

        logger.debug("CityIq: get_page url={} page={}".format(url, str(page)))
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

    def _new_asset(self, e):
        from cityiq.asset import Asset

        dclass = Asset.dclass_map.get(e['assetType'], Asset)  # probably fragile

        if 'eventTypes' in e and not e['eventTypes']:
            e['eventTypes'] = []

        return dclass(self, e, use_cache=self.cache_events)

    def _new_location(self, e):
        from cityiq.location import (Location)

        dclass = Location.dclass_map.get(e['locationType'], Location)  # probably fragile

        return dclass(self, e, use_cache=self.cache_events)

    def get_assets(self, device_type=None, zone=None, bbox=None, use_cache=None):

        cache_key = f"assets-{(device_type or 'none').replace(' ', 'X')}-{str(zone)}-{str(bbox)}"

        assets = self.get_meta_cache(cache_key)

        if assets:
            for a in assets:
                a.client = self
            return assets

        # A space ' ' is interpreted as querying for all records, while a blank '' is
        # an error.

        query = ('assetType', device_type if device_type is not None else ' ')

        assets = []

        for e in self.get_pages(self.config.metadata_url + self.assets_search_suffix,
                                query=query, zone=zone, bbox=bbox):
            assets.append(self._new_asset(e))

        self.set_meta_cache(cache_key, assets)

        return assets

    def get_asset(self, asset_uid, use_cache=True):
        from cityiq.asset import Asset

        ff = lambda: self.http_get(self.config.metadata_url + self.asset_url_suffix.format(uid=asset_uid)).json()

        cf = CacheFile(self.config.cache_objects, Asset(self, asset_uid), fetch_func=ff)

        return self._new_asset(cf.run())

    @property
    def assets(self):
        """Return all system assets"""
        return self.get_assets(' ')

    @property
    def asset_dataframe(self):
        """Return assets in row form in a pandas Dataframe"""
        from cityiq.asset import Asset
        from pandas import DataFrame

        return DataFrame([e.row for e in self.assets], columns=Asset.row_header)

    @property
    def nodes(self):
        """Return all nodes"""
        return self.get_assets('NODE')

    @property
    def cameras(self):
        """Return camera assets"""
        return self.get_assets('CAMERA')

    @property
    def env_sensors(self):
        """Return environmental sensors"""
        return self.get_assets('ENV_SENSOR')

    @property
    def em_sensors(self):
        """Return some other kind of sensor. Electro-magnetic? """
        return self.get_assets('EM_SENSOR')

    @property
    def mics(self):
        """Return microphone assets"""
        return self.get_assets('MIC')

    def assets_by_event(self, event_types):

        for a in self.assets:
            if a.has_events(event_types):
                yield a

    def get_locations(self, location_type=None, zone=None, bbox=None):
        """Get all locations, options for a zone or bounding box"""
        cache_key = f"locations-{None if location_type == ' ' else location_type}-{str(zone)}-{str(bbox)}"

        assets = self.get_meta_cache(cache_key)

        if assets:
            for a in assets:
                a.client = self
            return assets

        # A space ' ' is interpreted as querying for all records, while a blank '' is
        # an error.
        query = ('locationType', location_type if location_type else ' ')

        locations = []

        for e in self.get_pages(self.config.metadata_url + self.locations_search_suffix,
                                query=query, zone=zone, bbox=bbox):
            locations.append(self._new_location(e))

        self.set_meta_cache(cache_key, locations)

        return locations

    def get_location(self, location_uid, use_cache=True):
        """Get a single location by its uid"""

        from .location import Location

        def ff():
            url = self.config.metadata_url + self.location_url_suffix.format(uid=location_uid)
            r = self.http_get(url)
            return r.json()

        l = Location(self, location_uid)

        cf = CacheFile(self.config.cache_objects, l, fetch_func=ff)

        return self._new_location(cf.run())

    @property
    def locations(self):
        """Return all locations"""
        return self.get_locations(' ')

    @property
    def locations_dataframe(self):
        from pandas import DataFrame
        from cityiq.location import Location
        return DataFrame([e.row for e in self.locations], columns=Location.row_header)

    @property
    def walkways(self):
        for l in self.locations:
            if l.locationType == 'WALKWAY':
                yield l

    @property
    def traffic_lanes(self):
        for l in self.locations:
            if l.locationType == 'TRAFFIC_LANE':
                yield l

    @property
    def parking_zones(self):
        for l in self.locations:
            if l.locationType == 'PARKING_ZONE':
                yield l

    def locations_by_event(self, event_types):

        if set(event_types) & {'PKIN', 'PKOUT'}:
            return self.parking_zones
        elif set(event_types) & {'PEDEVT'}:
            return self.walkways
        elif set(event_types) & {'TFEVT'}:
            return self.traffic_lanes
        elif set(event_types) & {'BICYCLE'}:
            return self.traffic_lanes
        else:
            locations = []

        return locations

    def _event_params(self, start_time, end_time, event_type, bbox=None):

        start_time = self.convert_time(start_time)
        end_time = self.convert_time(end_time)

        if bbox is None:  # it may also be False
            bbox = self.config.bbox

        params = {
            # 'locationType': event_to_location_type(event_type),
            'eventType': event_type,
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'pageSize': 20000
        }

        logger.debug(f"Param range {start_time} to {end_time}")

        if bbox:
            params['bbox'] = bbox

        return params

    def _events(self, url, event_type, start_time, end_time, bbox=None):
        """"""

        page = 0
        records = []

        while True:

            params = self._event_params(start_time, end_time, event_type, bbox=bbox)

            r = self.http_get(url, params=params, zone=event_to_zone(self.config, event_type))

            try:
                d = r.json()
            except Exception:
                print(r.text)
                raise

            content = d['content']
            records += content
            md = d['metaData']

            if md['request_limit'] < md['totalRecords']:
                page += 1
                start_time = int(md['endTs'])

            else:

                logger.debug(f"Got {len(records)} events")
                return records

    def make_tasks(self, fetch_tasks_class, objects, events, start_time, end_time):
        """Fetch, and cache, events requests for a set of assets or locations """

        start_time = self.convert_time(start_time)
        end_time = self.convert_time(end_time)

        return list(fetch_tasks_class.make_tasks(objects, events, start_time, end_time))

    def run_async(self, tasks, workers=4):
        """Run a set of tasks, created with make_tasks, with multiple workers """

        for task, result in run_async(tasks, workers=workers):
            yield task, result

    def run_sync(self, tasks):
        """Run all of the tasks, one at a time, and return the combined results"""

        for t in tasks:
            yield t, t.run()


    @property
    def total_bounds(self):
        """Return a bounding box for the system from all of the assets. This will be affected by the
        bbox set in the config, so it should usually be smaller than the one in the config

        Order is: lat_max, lon_min, lat_min, lon_max

        """
        assets = list(self.get_assets())

        lats = [float(a.lat) for a in assets]
        lons = [float(a.lon) for a in assets]

        return max(lats), min(lons), min(lats), max(lons)

    @property
    def total_bounds_str(self):
        """Total bounds bounding box, in the form of the city_iq config"""

        return "{0}:{1},{2}:{3}".format(*self.total_bounds)

    def load_locations(self, path):
        from .location import Location

        locations = []

        with Path(path).open() as f:
            from csv import DictReader
            for o in DictReader(f):
                locations.append(Location(self, o))

        return locations
