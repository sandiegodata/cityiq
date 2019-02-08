# -*- coding: utf-8 -*-
"""

"""

import base64
import json
import logging
from binascii import crc32
from pathlib import Path
from time import time

import requests

logger = logging.getLogger(__name__)


def get_cached_token(cache_path, uaa, client, secret):
    """
        Return a cached access token from the CityIQ service. Returns just the token. Use _get_token() to get the
        full response

        :param cache_path: Directory where cached token will be stored, if a directory or token name if a file
        :param uaa: Url to the user authentication service
        :param client:
        :param secret:
        :return: A token string

        If a directory is specified in cache_dir, the file name will be 'cityiq-token-<crc>.json', with the CRC32 of the
        source url. The token will be expired after 8 hours.

        """

    EXPIRE_TIME = (8 * 60 * 60)

    token_path = Path(cache_path)

    if token_path.is_dir():
        token_path = token_path.joinpath('cityiq-token-{:X}.json'.format(crc32(str(uaa).encode('ascii'))))

    # Expire the token
    try:
        if token_path.exists() and token_path.stat().st_ctime + EXPIRE_TIME < time():
            logger.debug('token: expired; deleting')
            token_path.unlink()
    except FileNotFoundError:
        # This can happen in a concurrency case, where another process has changed the token
        pass

    if token_path.exists():
        logger.debug('token: exists')
        with token_path.open() as f:
            response_text = f.read()
            data = json.loads(response_text)

    else:
        logger.debug('token: fetching')
        data = _get_token(uaa, client, secret)

        with token_path.open('w') as f:
            f.write(json.dumps(data))

    return data['access_token']


def get_token(uaa, client, secret):
    """
        Get an access token from the CityIQ service. Returns just the token. Use _get_token() to get the full response

        :param uaa: Url to the user authentication service
        :param client:
        :param secret:
        :return:
        """

    return _get_token(uaa, client, secret)['access_token']


def _get_token(uaa, client, secret):
    """
    Get an access token from the CityIQ service. Returns the full JSON response

    :param uaa: Url to the user authentication service
    :param client:
    :param secret:
    :return:
    """

    uaa += '/oauth/token'

    cs = (client + ':' + secret).encode('ascii')

    credentials = base64.b64encode(cs)

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache',
        'Authorization': b'Basic ' + credentials
    }
    params = {
        'client_id': client,
        'grant_type': 'client_credentials'
    }

    response = requests.post(uaa, headers=headers, data=params)

    response.raise_for_status()

    return response.json()
