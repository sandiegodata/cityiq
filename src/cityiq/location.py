# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

from cityiq.api import CityIqObject

from cityiq.asset import Asset
from requests import HTTPError
import json
import logging
from .util import json_serial, grouper
from pathlib import Path

logger = logging.getLogger(__name__)

class Location(CityIqObject):
    object_sub_dir = 'location'
    detail_url_suffix = '/api/v2/metadata/locations/{}'
    assets_url_suffix = '/api/v2/metadata/locations/{}/assets'
    events_url_suffix = '/api/v2/event/locations/{locationUid}/events'

    row_header = 'locationUid locationType parentLocationUid  geometry'.split()

    # observed values for the assetType field
    types = ['WALKWAY', 'TRAFFIC_LANE', 'PARKING_ZONE']



    @property
    def uid(self):
        return self.locationUid

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

    def get_events(self, event_type, start_time, end_time=None, span=None, ago=None):
        start_time = self.client.convert_time(start_time)
        end_time = self.client.convert_time(end_time)

        url = self.client.config.event_url + self.events_url_suffix.format(locationUid=self.locationUid)

        return self.client._events(url, event_type, start_time, end_time, bbox=False)

    @property
    def row(self):
        """Return most important fields in a row format"""
        from operator import attrgetter

        ag = attrgetter(*Location.row_header[:-1])

        return ag(self) + (self.geometry,)


    def __getstate__(self):
        odict = self.__dict__.copy()

        del odict['client']

        return odict

    def __setstate__(self, state):
        self.__dict__.update(state)

class WalkwayLocation(Location):
    pass


class TrafficLaneLocation(Location):
    pass


class ParkingZoneLocation(Location):
    pass

# Map asset types to subclasses
Location.dclass_map = {
        'WALKWAY': WalkwayLocation,
        'TRAFFIC_LANE': TrafficLaneLocation,
        'PARKING_ZONE': ParkingZoneLocation
}