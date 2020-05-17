# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE
"""

"""


import datetime
import itertools
import time
from datetime import date, datetime, timezone
from pathlib import Path

from cityiq.exceptions import CityIqError, TimeError
from dateutil.parser import parse

local_tz = datetime.now(timezone.utc).astimezone().tzinfo


def timestamp_to_local(ts, tz):
    """Convert a UTC timestamp in milliseconds to a local time, in the timezone tz,  with no timezone"""

    return datetime.utcfromtimestamp(ts / 1000) \
        .replace(microsecond=0) \
        .replace(tzinfo=timezone.utc) \
        .astimezone(tz) \
        .replace(tzinfo=None)


def local_to_timestamp(dt, tz):
    """Convert a local time, assumed in timezone tz, into a milisecond UTC timestamp"""

    return int(dt.replace(tzinfo=tz).timestamp() * 1000)


def make_csv_file_name(cache, locationUid, event_type):
    return Path(cache).joinpath('{}/{}.csv'.format(locationUid, event_type))


def event_type_to_locations(c, events):
    if set(events) & {'PKIN', 'PKOUT'}:
        locations = list(c.parking_zones)  # Get all of the locations
    elif set(events) & {'PEDEVT'}:
        locations = list(c.walkways)  # Get all of the locations
    elif set(events) & {'TFEVT'}:
        locations = list(c.traffic_lanes)  # Get all of the locations
    else:
        locations = []

    return locations


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


def current_time():
    '''Return the epoch time in miliseconds'''
    return int(round(time.time() * 1000, 0))




def event_to_location_type(event_type):

    if event_type in ('PKIN', 'PKOUT'):
        return 'PARKING_ZONE'
    elif event_type == 'PEDEVT':
        return 'WALKWAY'
    elif event_type == 'TFEVT':
        return 'TRAFFIC_LANE'
    else:
        return None


def event_to_zone(config, event_type):

    d = {
        'PKIN': config.parking_zone,
        'PKOUT': config.parking_zone,
        'PEDEVT': config.pedestrian_zone,
        'BICYCLE': config.bicycle_zone,
        'TFEVT': config.traffic_zone,
        'TEMPERATURE': config.environmental_zone,
        'PRESSURE': config.environmental_zone,
        'METROLOGY': config.environmental_zone,
        'HUMIDITY': config.environmental_zone,

        # These are probably wrong ...
        'ORIENTATION': config.environmental_zone,
        'ENERGY_TIMESERIES': config.environmental_zone,
        'ENERGY_ALERT': config.environmental_zone
    }

    return d.get(event_type)