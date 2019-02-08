#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import argparse
import logging
import sys

from cityiq import __version__

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Fetch and dispay assets")
    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-c', '--config', help='Path to configuration file')

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-i', '--iterate', help='Iterate over stored events returning JSON lines', action='store_true')

    group.add_argument('-c', '--csv', help='Write assets to a CSV file')

    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """

    from cityiq import Config, CityIq

    args = parse_args(args)
    setup_logging(args.loglevel)

    if args.config:
        config = Config(args.config)

    else:
        config = Config()

    if not config.client_id:
        print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")

    print("Using config:", config._config_file)

    c = CityIq(config)

    if args.iterate:
        for r in c.assets:
            print(r.data)

    elif args.csv:

        df = c.pair()

        df.to_csv(args.pair)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
