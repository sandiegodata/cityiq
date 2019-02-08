"""

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

        self.parameters = 'client_id secret bbox zone cache_dir  uaa_url metadata_url event_url _config_file'.split()

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
