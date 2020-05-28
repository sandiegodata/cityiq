# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE
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
from .exceptions import ConfigurationError
import yaml


class Config(object):

    def __init__(self, path=None, **kwargs):
        """

        :param path: A path in which to look for config. Prepended to search paths

        kwargs set top level value.

        Special handling for cache keys; kwargs of the
        form "cache_object" will set the 'object' key of the top level
        'cache' dict. So to change the object cache: Config(cache_object="/tmp")

        Equivalently, the values in the config file in the 'cache" dict are flattened,
        so 'cache->meta' is translated to 'cache_meta'


        """

        self.parameters = 'client_id secret bbox zone  uaa_url metadata_url event_url _config_file ' \
                          'start_time cache_dir events_cache timezone'.split()

        self.env_vars = {e: f"CITYIQ_{e.upper()}" for e in self.parameters}

        if not path:
            self._paths = [
                Path.cwd().joinpath('.city-iq.yaml'),
                Path.cwd().joinpath('city-iq.yaml'),
                Path.home().joinpath('.city-iq.yaml'),
            ]
        else:
            if Path(path).is_dir():
                self._paths = [ Path(path).joinpath(e) for e in ['.city-iq.yaml', 'city-iq.yaml']]
            else:
                self._paths = [Path(path)]

        if environ.get('CITYIQ_CONFIG'):
            self._paths = [Path(environ.get('CITYIQ_CONFIG'))] + self._paths


        self._kwargs = kwargs

        self._config = self._load_config()

        if 'cache' in self._config:
            for k, v in self._config['cache'].items():
                self._config['cache_'+k] = v

            del self._config['cache']



    def _load_config(self):
        """
        Load a YAML configuration from the first configuration file that is found to exist
        :return:
        """

        for p in self._paths:
            if p.exists():
                with p.open() as f:
                    c = yaml.safe_load(f)
                    if c:
                        c['_config_file'] = str(p)
                    return c
        else:
            raise ConfigurationError(f"Didn't find a config file in paths: {self._paths}")

        return {}

    @property
    def which(self):
        return self._config_file

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

    def __str__(self):
        import yaml
        return yaml.dump(self.dict, default_flow_style=False)
