#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import argparse
import logging
import sys

from cityiq import __version__
from cityiq.iterate import EventIterator, ParkingIterator, PedestrianIterator
from cityiq.cli.util import group_to_events, group_to_locations

from cityiq import Config, CityIq, AuthenticationError

from cityiq.util import grouper
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

max_workers = 8
chunksize = 1

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)

def parse_args(args):
    """Manipulate the CityIQ cache."""
    parser = argparse.ArgumentParser(
        description=parse_args.__doc__ )
    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-c', '--config', help='Path to configuration file')

    parser.add_argument('-s', '--start-time', help='Starting time, in iso format. If not specified, use the '
                                                   "configuration value 'start_time' ")
    parser.add_argument('-e', '--end-time', help='Ending time, in iso format. ')

    parser.add_argument('-E', '--event', help='Specify an event type to scrape')

    parser.add_argument('-l', '-locations', help='Scrape locations associated with each asset')


    return parser.parse_args(args)

def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def run():
    """Entry point for console_scripts
    """

    main(sys.argv[1:])

def main(args):
    """Main entry point allowing external calls"""








if __name__ == "__main__":
    run()
