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
import logging
import pickle
from pathlib import Path
from time import time

import pytz
import requests
from cityiq.util import event_to_zone
from slugify import slugify
from dateutil.parser import parse
from datetime import date, datetime, timezone

from .config import Config
from .exceptions import ConfigurationError, TimeError


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

    def cache_path(self, date, event_type, is_short=False):

        prefix = self.uid[:2] if self.uid else 'none'

        return self.client.object_cache.joinpath(
            Path(
                f'{self.object_sub_dir}/{prefix}/{self.uid}/{date.year}/{date.month}/{date.date().isoformat()}-{event_type}.json'))

    def get_fetch_task(self, event_type, start_time, end_time):
        from dateutil.relativedelta import relativedelta
        from .task import FetchTask

        d1 = relativedelta(days=1)

        today = self.client.tz.localize(datetime.datetime.now()).date()

        is_short = end_time.date() - d1 >= today

        return FetchTask(self, event_type, start_time, end_time)

    def __str__(self):
        return "<{}: {}>".format(type(self).__name__, self.data)


class Event(CityIqObject):
    types = ['PKIN', 'PKOUT', 'PEDEVT', 'TFEVT', 'TEMPERATURE', 'PRESSURE', 'ORIENTATION', 'METROLOGY', 'HUMIDITY',
             'ENERGY_TIMESERIES', 'ENERGY_ALERT']


class CityIq(object):
    object_sub_dir = 'object'  # Reset in sub dir
    assets_search_suffix = '/api/v2/metadata/assets/search'
    locations_search_suffix = '/api/v2/metadata/locations/search'
    events_url_suffix = '/api/v2/event/locations/events'

    asset_url_suffix = '/api/v2/metadata/assets/{uid}'
    location_url_suffix = '/api/v2/metadata/location/{uid}'

    def __init__(self, config=None, cache_metadata=True, **kwargs):
        CityIq
        if config:
            self.config = config
        else:
            self.config = Config(**kwargs)

        self._token = None

        self.tz = pytz.timezone(self.config.timezone)

        self.cache_metadata = cache_metadata

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
            return  self.tz.localize(dt)
        except ValueError:
            # Already localized:
            return dt

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

        headers = {
            'Authorization': 'Bearer ' + self.token
        }

        zone = zone if zone else self.config.default_zone

        if zone:
            headers['Predix-Zone-Id'] = zone

        if params:
            # Not using the requests param argument b/c it will urlencode, and these query
            # parameters can't be url encoded.
            url = url + '?' + "&".join("{}={}".format(k, v) for k, v in params.items())

        r = requests.get(url, headers=headers, *args, **kwargs)

        try:
            r.raise_for_status()
        except Exception:
            headers['Authorization'] = headers['Authorization'][:30]+'...' # Bearer token is really long
            print('------')
            print('url             : ', url)
            print('request headers : ', headers)
            print('status code     : ', r.status_code)
            print('response headers: ', headers)
            print('body            : ', r.text)
            print('------')
            raise

        return r

    def _get_page(self, url, page, zone, bbox, query):

        params = {
            'page': page,
            'size': 5000,
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
        return dclass(self, e)

    def _new_location(self, e):
        from cityiq.location import (Location)

        dclass = Location.dclass_map.get(e['locationType'], Location)  # probably fragile

        return dclass(self, e)

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

    def get_asset(self, asset_uid):

        r = self.http_get(self.config.metadata_url + self.asset_url_suffix.format(uid=asset_uid))
        return self._new_asset(r.json())

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

    def get_locations(self, location_type=None, zone=None, bbox=None):

        cache_key = f"locations-{None if location_type == ' ' else location_type}-{str(zone)}-{str(bbox)}"

        assets = self.get_meta_cache(cache_key)

        if assets:
            for a in assets:
                a.client = self
            return assets

        raise Exception(cache_key)

        # A space ' ' is interpreted as querying for all records, while a blank '' is
        # an error.
        query = ('locationType', location_type if location_type else ' ')

        locations = []

        for e in self.get_pages(self.config.metadata_url + self.locations_search_suffix,
                                query=query, zone=zone, bbox=bbox):
            locations.append(self._new_location(e))

        self.set_meta_cache(cache_key, locations)

        return locations

    def get_location(self, asset_uid):

        r = self.http_get(self.config.metadata_url + self.location_url_suffix.format(uid=asset_uid))
        return self._new_location(r.json())

    @property
    def locations(self):
        return self.get_locations(' ')

    @property
    def locations_dataframe(self):
        from pandas import DataFrame
        from cityiq.location import Location
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

        if bbox is None:  # it may also be False
            bbox = self.config.bbox

        params = {
            # 'locationType': event_to_location_type(event_type),
            'eventType': event_type,
            'startTime': int(start_time.timestamp()*1000),
            'endTime': int(end_time.timestamp()*1000),
            'pageSize': 20000
        }

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
                return records

    def events(self, start_time=None, end_time=None, bbox=None, event_type=' '):
        """

        :param start_time:
        :param end_time:
        :param age:  if start_time is not specified, the start time in terms of seconds before the end time
        :return:
        """

        raise NotImplementedError("Maybe don't ever call for events from client, Always from Asset or Location")

        start_time = self.convert_time(start_time)
        end_time = self.convert_time(end_time)

        url = self.config.event_url + self.events_url_suffix

        bbox = bbox or self.config.bbox

        return self._events(url, event_type, start_time, end_time, bbox=bbox)

        logger.debug("Ending events")

    @property
    def total_bounds(self):
        """Return a bounding box for the system from all of the assets. This will be affected by the
        bbox set in the config, so it should usually be smaller than the one in the config"""
        assets = list(self.get_assets())

        lats = [a.lat for a in assets]
        lons = [a.lon for a in assets]

        return "{}:{},{}:{}".format(max(lats), max(lons), min(lats), min(lons))

    def load_locations(self, path):
        from .location import Location

        locations = []

        with Path(path).open() as f:
            from csv import DictReader
            for o in DictReader(f):
                locations.append(Location(self, o))

        return locations
