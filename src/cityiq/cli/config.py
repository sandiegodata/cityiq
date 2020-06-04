#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import argparse
import logging
import sys
from pathlib import Path

from cityiq import __version__

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def make_parser():
    """Create or print the ``cityiq`` module configuration.

    You can create a new configuration file with the ``-w`` option or
    print the configuration with ``-p``


    """

    parser = argparse.ArgumentParser(description=make_parser.__doc__)

    parser.add_argument('--version', action='version', version='cityiq {ver}'.format(ver=__version__))

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-w', '--write', help="Write a new default config file to the current directory, "
                                             "or with -u to the user's directory ", action='store_true')

    parser.add_argument('-u', '--user', help="With --write, write to the user's home directory, ~/.cityiq.yaml",
                       action='store_true')

    parser.add_argument('-F', '--force', help="With --write, force overwritting",
                        action='store_true')

    group.add_argument('-p', '--print', help='Print the config file', action='store_true')

    return parser

parser = make_parser()

def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """

    from cityiq import Config



    args =  parser.parse_args(args)

    config = Config()

    if args.write:
        p = Path(__file__).parent.joinpath('default-config.yaml')

        with p.open() as f:
            d = f.read()

        if args.user:
            fn = Path('~/.city-iq.yaml').expanduser()
        else:
            fn = Path('./city-iq.yaml').resolve()

        if fn.exists():
            if args.force:
                fn.unlink()
            else:
                print("Error: {} exists, not overwritting".format(fn))
                sys.exit(1)

        with open(fn, 'w') as f:
            f.write(d)

        print("Wrote ", fn)

    elif args.print:
        import yaml
        if not config.client_id:
            print("ERROR: Did not get valid config file. Use --config option or CITYIQ_CONFIG env var")
        else:
            print("Using config:", config._config_file)

        print(yaml.dump(config.dict, default_flow_style=False))

    else:
        parser.print_usage()


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
