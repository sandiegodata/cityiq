# -*- coding: utf-8 -*-
"""

"""

from datetime import datetime, timezone

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
