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


def run_async(items,  workers=4):
    """Run a function in multiple threads"""

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = { executor.submit(item.run):item for item in items }

        for future in as_completed(futures):
            item = futures[future]

            try:
                result = future.result()
            except Exception as e:
                yield item, e
            else:
                yield item, result

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





def event_type_to_location_type(event_type):

        if event_type in {'PKIN', 'PKOUT'}:
            return "PARKING_ZONE"
        elif event_type == 'PEDEVT':
            return "WALKWAY"
        elif  event_type == 'TFEVT':
            return "TRAFFIC_LANE"
        elif  event_type == 'BICYCLE':
            return "TRAFFIC_LANE"
        else:
            raise CityIqError("Unknown Event type: "+event_type)

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

    return d[event_type]


def log_message(r):
    """Debugging log message for requests"""
    from textwrap import dedent
    headers = r.request.headers
    url = r.request.url

    headers['Authorization'] = headers['Authorization'][:5] + '...'  # Bearer token is really long

    m = f"""

    url             : {url}
    request headers : {headers}
    status code     : {r.status_code}
    response headers: {headers}

    """

    return dedent(m)