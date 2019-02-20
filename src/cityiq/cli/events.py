#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" The ciq_events program is used to scrape and process events. To properly
run the program, two directories should be specified in the configuration:

- ``events_cache``: The directory where hourly event fiels will be specified
- ``cache_dir``: The directory where processed event files will be written.

To scrape events from the API, run :option:`ciq_events --scrape --start_time
<isotime>`. If ``<isotime>`` is omitted, the program will start from the
``start_time`` specified in the config. This will download events from the
start time in hourly batches, and save one file per hour.

To process events, first break up the hourly event files by location with
:option:`ciq_events --split` command. This will create one CSV file per
location per month. Then, re-combine and renormalize the data with
:option:`ciq_events --normalize`, which will write a CSV file to the local directory.

The final output file will have columns for `delta`, which is the number of
cars that went into or out of a parking zone per 15 minute interval. However,
there are a lot of suprious events, so the `delta_norm` has a normalized value
that tries to remove the spurious events.

These programs can produce a lot of data. For the San Diego system, the
extracted PKIN and PKOUT events for September 2018 through Feb 2019 is 21GB,
and the download process takes several days. The final processed CSV file, with
records at 15 minute intervals, is about 81MB and akes about an hour to process.

For instance:

.. code-block:: bash

    $ ciq_events -s -e PKIN -e PKOUT -t 20190901
    $ ciq_events -S
    $ ciq_events -n

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

    group.add_argument('-S', '--split', help='Split scraped records into month and location files', action='store_true')

    group.add_argument('-n', '--normalize', help='Dedupe and normalize',
                       action='store_true')

    parser.add_argument('-e', '--event', action='append', help='Specify an event type for the scraper')

    parser.add_argument('-T', '--threads', type=int, help='Number of threads to use for fetching data')

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

    if not args.event:
        args.event = ['PKIN', 'PKOUT']

    s = EventScraper(config, start_time, args.event, max_workers=args.threads)

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

    elif args.split:
        print("Splitting scraped files")
        s.run_split_locations(use_tqdm=True)

    elif args.normalize:

        from cityiq.clean_events import clean_events

        df = clean_events(s)

        t_min, t_max = df.index.min(), df.index.max()

        fn = "cityiq-{}-{}-{}.csv".format(
            '_'.join(sorted(args.event)),
            "{}{:02d}{:02d}".format(t_min.year, t_min.month, t_min.day),
            "{}{:02d}{:02d}".format(t_max.year, t_max.month, t_min.day),
        )

        df.to_csv(fn)

        print("Wrote ", fn)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
