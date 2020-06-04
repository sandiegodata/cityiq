#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" The ciq_events program is used to scrape and process events.

"""

import argparse
import logging
import sys

from progress.bar import ShadyBar as Bar

from cityiq import CityIqError, __version__
from cityiq.task import DownloadTask
from cityiq.util import event_type_to_location_type

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)

valid_events = ['PKIN', 'PKOUT', 'PEDEVT', 'TFEVT', 'BICYCLE']
ve_string = ','.join(valid_events)


class ProgressBar(Bar):
    _downloaded = 0
    _extant = 0

    @property
    def downloaded(self):
        return self._downloaded

    @property
    def extant(self):
        return self._extant

    def update_task(self, task):
        if task.downloaded is True:
            self._downloaded += 1
        elif task.downloaded is False:
            self._extant += 1

def make_parser():
    """Download events and load them into the cache.

    The :program:`ciq_events` program will request events from a CityIQ system, one
    day at a tim, and cache the results. It will request the events from
    assets, based on which assets have ``eventTypes`` with the requested events.

    Because the program will request events for all of the assets that report an
    event type and makes one request per day, it can generate very large numbers of
    requests and take many hours to run. For instance this request:

    ciq_events -s 2020-01-01 -e 2020-06-01-01 PKIN PKOUT

    generates about 800,000 requests and will take a day to run.

    The `cityiq` module will not cache event requests for the current day or
    any day in the future.


    """
    parser = argparse.ArgumentParser(description=make_parser.__doc__,prog='ciq_events')

    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-a', '--assets',
                        help="Path to a CSV file of assets, of the form produced by the 'ciq_nodes' program.")

    parser.add_argument('-c', '--config', help='Path to configuration file')

    parser.add_argument('-w', '--workers', help='Number of threads to use', default=4, type=int)

    parser.add_argument('-s', '--start-time', help='Starting time, in iso format. If not specified, use the '
                                                    "configuration value 'start_time' ")
    parser.add_argument('-f', '--end-time', help='Ending time, in iso format. If not specified, end time is yesterday ')

    parser.add_argument('-e', '--events', nargs='+', help='Names of events to scrape. One or more of: '+ve_string)

    parser.add_argument('-o','--output-name',
                        help='Output file, where events are written in CSV format')

    parser.add_argument('-O', '--output', action='store_true',
                        help='Coalesce data into one CSV file per asset')

    return parser

parser = make_parser()


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")

    _logger.setLevel(loglevel)


def main(args):

    try:
        _main(args)
    except (BrokenPipeError, KeyboardInterrupt):
        pass


def _main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """

    from datetime import datetime, timezone

    from cityiq import Config, CityIq

    args = parser.parse_args(args)

    if args.loglevel:
        setup_logging(args.loglevel)

    if args.config:
        config = Config(args.config)
    else:
        config = Config()

    if not config.client_id:
        print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")
        sys.exit(1)

    start_time_str = str(args.start_time or config.start_time)

    if not start_time_str:
        print("ERROR: Must specify a start time on the command line or in the config")
        sys.exit(1)

    print("Using config:", config._config_file)

    events = [e.upper() for e in args.events]

    try:
        [event_type_to_location_type(e) for e in events]
    except CityIqError as e:
        print(f"Unknown event type: {e}. Must be . One or more of: "+ve_string)
        sys.exit(1)

    c = CityIq(config)

    end_time = c.convert_time(args.end_time)
    start_time = c.convert_time(start_time_str)

    assets = list(c.assets_by_event(events))  # Get all assets that have the Bicycle event

    if args.assets:
        from csv import DictReader
        asset_map = {a.uid: a for a in assets }

        with open(args.assets) as f:
            assets = [asset_map.get(row['assetUid']) for row in DictReader(f) if row['assetUid'] in asset_map]

    print(f"Using {len(assets)} assets")

    tasks = c.make_tasks(assets, events,  start_time, end_time)


    if not args.output:

        with ProgressBar('Downloading', max=len(tasks),
                         suffix='%(index)d of %(max)d  (%(percent).1f%%) - ETA %(eta_td)s') as bar:
            # suffix='%(index)d of %(max)d  (%(percent).1f%%) %(extant)d extant %(downloaded)d downloaded - ETA %(eta_td)s') as bar:

            for i, (task, result) in enumerate(c.run_async(tasks)):
                bar.next()
                bar.update_task(task)
    else:
        import pandas as pd
        from tqdm import tqdm
        from pathlib import Path

        event_name = '-'.join(e.lower() for e in events)

        for a in tqdm(assets, desc='Assets'):
            name = f"{event_name}_{start_time.date().isoformat()}_{end_time.date().isoformat()}/{a.uid}.csv"

            files = list(c.get_cache_files([a], events, start_time, end_time))

            frames = []
            for f in tqdm(files, desc="Frames", leave=False):
                frames.append(pd.read_csv(f))

            if frames:
                df = pd.concat(frames, sort=False)
            #    df['timestamp'] = pd.to_datetime(df.timestamp)

                p = Path(name)

                if not p.parent.exists():
                    p.parent.mkdir()

                df.to_csv(name, index=False)

    print("Done")

def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
