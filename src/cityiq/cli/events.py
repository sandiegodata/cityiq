#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" The ciq_events program is used to scrape and process events.

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

    parser.add_argument('-t', '--start-time', help='Starting time, in iso format. If not specified, use the '
                                                   "configuration value 'start_time' ")
    parser.add_argument('-f', '--end-time', help='Ending time, in iso format. ')

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-e', '--enumerate', help='List the files that will be crated by a complete scrape')

    group.add_argument('-i', '--iterate', help='Iterate over stored events returning JSON lines')

    group.add_argument('-l', '--list', help='List the cached files. Same options as scrape, or "all" ')

    group.add_argument('-s', '--scrape', help="Scrape new events. Value is 'parking', 'ped' or 'traffic' ")

    parser.add_argument('-T', '--threads', type=int, default=4, help='Number of threads to use for fetching data')

    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")

    _logger.setLevel(loglevel)


def group_to_events(group):

    if group == 'parking':
        events = ['PKIN', 'PKOUT']
    elif group == 'ped':
        events = ['PEDEVT']
    elif group == 'traffic':
        events = ['TFEVT']
    elif group == 'all':
        events = None
    else:
        print("ERROR: Unkown event group: {} ".format(group))
        sys.exit(1)


    return events

def group_to_locations(c, group):

    if group == 'parking':
        locations = list(c.parking_zones)  # Get all of the locations
    elif group == 'ped':
        locations = list(c.walkways)  # Get all of the locations
    elif group == 'traffic':
        locations = list(c.traffic_lanes)  # Get all of the locations
    else:
        locations = []

    return locations



def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """

    from datetime import datetime, timezone

    from cityiq import Config, CityIq
    from cityiq.scrape import LocationEventScraper
    from cityiq.scrape import logger as scrape_logger
    from dateutil.parser import parse as parse_dt

    args = parse_args(args)

    if args.loglevel:
        setup_logging(args.loglevel)

    tz = datetime.now(timezone.utc).astimezone().tzinfo

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

    if args.end_time:
        end_time = parse_dt(args.end_time).replace(tzinfo=tz)
    else:
        # Only scrape up to the most recent full month
        end_time = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz=None).replace(day=1)

    if args.enumerate:

        s = LocationEventScraper(config, None, group_to_events(args.enumerate), start_time, end_time)

        for loc in s.generate_file_names(): #s.list():
            print(loc)

    elif args.iterate:

        s = LocationEventScraper(config, None, group_to_events(args.iterate), start_time, end_time)

        for loc in s.generate_records():
            print(loc)

    elif args.list:

        s = LocationEventScraper(config, None, group_to_events(args.list), start_time, end_time)

        for loc in s.generate_file_names(): #s.list():
            print(loc)

    elif args.scrape:

        #scrape_logger.setLevel(logging.DEBUG)

        c = CityIq(config)

        events = group_to_events(args.scrape)
        locations = group_to_locations(c, args.scrape)

        print('Starting')

        from time import time
        lt = st = time()
        count = 0
        skipped = 0

        s = LocationEventScraper(config, locations, events, start_time, end_time, max_workers=args.threads,
                                 post_cb=False)

        for i, result in enumerate(s.get_events()):

            if time() - lt > 10:
                lt = time()
                delta_t = time() - st
                print('Wrote {}, {}/sec; skipped {} '.format(count, round((count / delta_t)), skipped ))

            if result[0] is False:
                skipped +=1
                continue

            s.write_results(*result)
            count += 1

            _logger.info(result[1])


        print("Finished")
        print(f"{s.processed} processed;  {s.wrote} wrote; {s.errors} errors; {s.existed} existed")




def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
