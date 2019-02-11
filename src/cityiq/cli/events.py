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
        description="Scrape and iterate over cached events")
    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-c', '--config', help='Path to configuration file')

    parser.add_argument('-t', '--start-time', help='Starting time, in iso format. ')

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-i', '--iterate', help='Iterate over stored events returning JSON lines', action='store_true')

    group.add_argument('-l', '--list', help='List the cached files', action='store_true')

    group.add_argument('-s', '--scrape', help='Scrape new events', action='store_true')

    group.add_argument('-p', '--pair', help='Pair in and out records and write a CSV file')

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

    import datetime

    from cityiq import Config
    from cityiq.scrape import EventScraper
    from cityiq.scrape import logger as scrape_logger
    from dateutil.parser import parse as parse_dt

    args = parse_args(args)
    setup_logging(args.loglevel)

    tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

    if args.config:
        config = Config(args.config)

    else:
        config = Config()

    if not config.client_id:
        print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")
        sys.exit(1)

    start_time_str = args.start_time or config.start_time

    if not start_time_str:
        print("ERROR: Must specify a start time on the command line or in the config")
        sys.exit(1)

    print("Using config:", config._config_file)

    start_time = parse_dt(start_time_str).replace(tzinfo=tz)

    print(start_time)

    s = EventScraper(config, start_time, ['PKIN', 'PKOUT'])

    if args.iterate:
        for r in s.iterate_records():
            print(r)

    elif args.list:

        for st, fn_path, exists in s.yield_file_names():
            if exists:
                print(st, fn_path)

    elif args.scrape:

        scrape_logger.setLevel(logging.DEBUG)

        s.scrape_events()

    elif args.pair:

        df = s.pair()

        df.to_csv(args.pair)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
