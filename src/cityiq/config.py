"""
The CityIq module and programs require a configuration file that hold credentials and urls. You can generate a default
configuration with ::

    ciq_config  -w

The generated file is configured for the San Diego system. To you this system , you will just need to add your
client id and secret to the file.

The  :py:class:`Config` object can be constructed can constructed on a path where the config file is location. If none
is specified it will look for this file in several places, in this order:

- The path specified in the constructor
- The path specified by the ``CITYIQ_CONFIG`` env var
- ``.city-iq.yaml`` in the current dir
- ``city-iq.yaml`` in the current dir
- ``.city-iq.yaml`` in the user's home dir

Each of the configuration files can be overridden with a keywork in the ``Config`` object constructor, and each value
can be accessed as an attribute or an index:


.. code-block:: python

    # Load from well-known file and override cache_dir
    c = Config(cache_dir='/tmp')

    print(c.cache_dir)
    print(c['cache_dir'])

"""

from os import environ
from pathlib import Path

import yaml


class Config(object):

    def __init__(self, path=None, **kwargs):
        """

        :param path:
        :param client_id:
        :param secret:
        :param uaa_url:
        :param metadata_url:
        :param bbox:
        :param zone:

        """

        self.parameters = 'client_id secret bbox zone  uaa_url metadata_url event_url _config_file ' \
                          'start_time cache_dir events_cache timezone'.split()

        self.env_vars = {e: f"CITYIQ_{e.upper()}" for e in self.parameters}

        self._paths = [
            Path.cwd().joinpath('.city-iq.yaml'),
            Path.cwd().joinpath('city-iq.yaml'),
            Path.home().joinpath('.city-iq.yaml'),
        ]

        if environ.get('CITYIQ_CONFIG'):
            self._paths = [Path(environ.get('CITYIQ_CONFIG'))] + self._paths

        if path:
            self._paths = [Path(path)] + self._paths

        self._kwargs = kwargs

        self._config = self._load_config()

    def _load_config(self):
        """
        Load a YAML configuration from the first configuration file that is found to exist
        :return:
        """

        for p in self._paths:
            if p.exists():
                with p.open() as f:
                    c = yaml.load(f)
                    c['_config_file'] = str(p)
                    return c

        return {}

    @property
    def dict(self):

        d = {k: self[k] for k in self.parameters}

        for k, v in self._config.items():
            if k not in d:
                d[k] = v

        return d

    def __getattr__(self, item):

        try:
            return self._kwargs[item]
        except KeyError:
            pass

        try:
            return environ[self.env_vars[item]]
        except KeyError:
            pass

        try:
            return self._config[item]
        except KeyError:
            pass

        if item not in self.parameters:
            raise AttributeError(item)

        return None

    def __getitem__(self, item):
        try:
            return self.__getattr__(item)
        except AttributeError:
            raise IndexError(item)
