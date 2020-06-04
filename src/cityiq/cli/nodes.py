#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import argparse
import csv
import json
import logging
import sys

import pandas as pd
import tqdm

from cityiq import __version__

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

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--csv', action='store_const', dest='format', const='csv', help='Write output as CSV.')
    group.add_argument('-j', '--json', action='store_const', dest='format', const='json',help='Write output as JSON.')
    group.add_argument('-l', '--jsonl', action='store_const',dest='format', const='jsonl', help='Write output as JSON lines.')

    parser.add_argument('-o', '--output',nargs='?', type=argparse.FileType('w'),
                       default=sys.stdout,
                        help='Output file name. If not specified, write to stdout, except for -M, which is always writen to a file. ')

    parser.add_argument('-F', '--no-cache', help="Don't use cached metadata; force a request to the API",
                       action="store_true")

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-M', '--asset-map-csv', help='Write a CSV file that maps assets to locations ')

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

    node_type = [ a for a in acessors if getattr(args, a) == True]
    if node_type:
        node_type = node_type[0]
    else:
        node_type = None

    try:
        if args.asset_map_csv:
            print("Building asset to locations map. This is really slow.")
            with open(args.asset_map_csv, 'w') as f, tqdm.tqdm() as p:
                w = csv.writer(f)
                w.writerow('assetUid parentAssetUid assetType locationUid parentLocationUid locationType geometry'.split())

                for a in c.assets:
                    for l in a.locations:
                        w.writerow([a.assetUid, a.parentAssetUid, a.assetType, l.locationUid,
                                    l.parentLocationUid, l.locationType, l.geometry.wkt])
                        p.update(1)
        elif node_type:
            nodes = []
            for n in getattr(c, node_type):
                nodes.append(n)

            if args.format=='csv':
                df = json_normalize(a.as_dict(wkt=True) for a in c.assets)
                df.to_csv(args.output)
            elif args.format=='json':
                json.dump([n.as_dict(wkt=True) for n in nodes],args.output)
            elif args.format == 'jsonl':
                for n in nodes:
                    print(json.dumps(n.as_dict(wkt=True)), file=args.output)

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
