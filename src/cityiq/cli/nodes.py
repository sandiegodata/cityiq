#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import argparse
import logging
import sys

from cityiq import __version__
import csv
import tqdm

import pandas as pd

try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)

acessors = 'assets', 'nodes', 'cameras', 'env_sensors', 'em_sensors ', 'mics', \
           'locations', 'walkways', 'traffic_lanes', 'parking_zones'

def make_parser():
    """Get assets and locations for a CityIQ system

    """
    parser = argparse.ArgumentParser(description=make_parser.__doc__)
    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    parser.add_argument('-v', '--verbose', dest="loglevel", help="set loglevel to INFO", action='store_const',
                        const=logging.INFO)

    parser.add_argument('-vv', '--very-verbose', dest="loglevel", help="set loglevel to DEBUG", action='store_const',
                        const=logging.DEBUG)

    parser.add_argument('-C', '--config', help='Path to configuration file')

    parser.add_argument('-F', '--no-cache', help="Don't use cached metadata; force a request to the API",
                       action="store_true")

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-M', '--asset-map-csv', help='Write a CSV file that maps assets to locations ')

    group.add_argument('-A', '--assets-csv', help='Write all assets assets to a CSV file. ')

    group.add_argument('-L', '--locations-csv', help='Write all assets assets to a CSV file. ')


    for a in acessors:
        group.add_argument(f'--{a}', help=f'Print all {a} as JSON lines', action="store_true")


    return parser

parser=make_parser()


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

    from cityiq import Config, CityIq, AuthenticationError

    args = parser.parse_args(args)
    setup_logging(args.loglevel)

    if args.config:
        config = Config(args.config)

    else:
        config = Config()

    if not config.client_id:
        print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")

    c = CityIq(config, cache_metadata= not args.no_cache)

    try:
        if args.asset_map_csv:
            print("Building asset to locations map. This is really slow.")
            with open(args.asset_map_csv, 'w') as f, tqdm.tqdm() as p:
                w = csv.writer(f)
                w.writerow('assetUid parentAssetUid assetType locationUid parentLocationUid locationType'.split())

                for a in c.assets:
                    for l in a.locations:
                        w.writerow([a.assetUid, a.parentAssetUid, a.assetType, l.locationUid, l.parentLocationUid, l.locationType])
                        p.update(1)
        elif args.assets_csv:
            df = json_normalize(a.data for a in c.assets)
            df.to_csv(args.assets_csv)
        elif args.locations_csv:
            df = json_normalize(a.data for a in c.locations)
            df.to_csv(args.locations_csv)
        else:
            for a in acessors:
                if getattr(args, a) == True:
                    for l in getattr(c, a):
                        print(l)


    except AuthenticationError:
        print("ERROR: Authentication failed. Check your username and password, or the authentication UAA url")
        sys.exit(1)
    except ModuleNotFoundError as e:
        print(e)
        print("ERROR: writing a CSV requires Pandas and Shapley: pip|conda install pandas shapley")
        sys.exit(1)



def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
