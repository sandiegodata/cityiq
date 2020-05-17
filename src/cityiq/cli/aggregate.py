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

columns = 'timestamp,locationuid,direction,speed,count'.split(',')



__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Aggregate events into CSV files. The CSV files are written to the cache directory for each location
    """
    parser = argparse.ArgumentParser(
        description=parse_args.__doc__ )
    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-c', '--config', help='Path to configuration file')


    parser.add_argument('-t', '--start-time', help='Starting time, in iso format. If not specified, use the '
                                                   "configuration value 'start_time' ")
    parser.add_argument('-f', '--end-time', help='Ending time, in iso format. ')

    #group = parser.add_mutually_exclusive_group()

    parser.add_argument('event_group', help="Event group name: 'ped', 'traffic' or 'parking' ")


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


    args = parse_args(args)


    if args.loglevel:
        setup_logging(args.loglevel)

    if args.config:
        config = Config(args.config)

    else:
        config = Config()

    if not config.client_id:
        print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")

    print("Using config:", config._config_file)

    if args.event_group == 'ped':
        s = PedestrianIterator(config,  start_time=args.start_time, end_time=args.end_time)
    elif args.event_group == 'parking':
        s = ParkingIterator(config, start_time=args.start_time, end_time=args.end_time)
    else:
        s = EventIterator(config, group_to_events(args.event_group),start_time=args.start_time, end_time=args.end_time)

    from tqdm import tqdm

    t = tqdm(desc='converting')
    exists = 0
    converted = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for chunk in grouper(max_workers*chunksize, s.generate_location_data()):
            futures = []
            for e in chunk:
                location, location_path, event_files = e

                csv_path = location_path.joinpath(f"{args.event_group}.csv")

                if not csv_path.exists():
                    print(csv_path)
                    futures.append(executor.submit(run_task, csv_path, event_files ))
                else:
                    exists += 1
                    t.set_postfix({'exists': exists, 'converted': converted})
                    t.update()

            for f in as_completed(futures):
                converted += 1
                t.set_postfix({'exists': exists, 'converted': converted})
                t.update()

def run():
    """Entry point for console_scripts
    """

    #main(sys.argv)
    print(sys.argv)
    main(sys.argv[1:])


def run_task(csv_path, event_files):
    import json

    def _extract_row(rec):

        common = (rec['timestamp'], rec['locationUid'])

        m = rec['measures']

        try:
            if float(m['pedestrianCount']) > 0:
                yield common + (m['direction'], float(m['speed']), float(m['pedestrianCount']))
        except KeyError:
            print(m)

        if float(m['counter_direction_pedestrianCount']) > 0:
            yield common + (m['counter_direction'], float(m['counter_direction_speed']),
                            float(m['counter_direction_pedestrianCount']))

    def _extract_rows():
        for date, path in event_files:
            with path.open() as f:
                d = json.load(f)
                for r in d['events']:
                    for e in _extract_row(r):
                        yield e

    df = pd.DataFrame(list(_extract_rows()), columns=columns)
    df['time'] = pd.to_datetime((df.timestamp / 1000).round(0).astype(int), unit='s')

    df = df.sort_values(['time', 'speed', 'direction']) \
        .set_index('time') \
        .groupby(['locationuid', 'direction']) \
        .resample('15Min') \
        .agg({
        'speed': 'mean',
        'count': 'sum'
    })

    try:
        df = df.reset_index().sort_values(['time', 'speed', 'direction'])
    except KeyError:  # Empty dataframe
        return False

    df = df[df['count'] > 0][['time', 'locationuid', 'direction', 'speed', 'count']]

    if len(df) > 0:
        df.to_csv(str(csv_path), index=False)

    return csv_path

if __name__ == "__main__":
    run()
