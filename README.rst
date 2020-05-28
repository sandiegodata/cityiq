==========
CityIQ API
==========

This module and command line tool provides access to the CityIQ_ API, with
particular focus on getting metadata and parking events. The interface includes
a basic access object for getting metadata and events, a scraper object for
mass downloading events, and a command line tool for downloading and processing
events.

Installation
============

Use pip::

    $ pip install cityiq

Configuration
=============

The program requires a configuration file that hold credentials and urls. You can generate a default configuration with ::

    $ ciq_config  -w

Or, to write the config to ``~/.city-iq.yaml`` ::

    $ ciq_config -wu

The generated file is configured for the San Diego system. To use this system , you will just need to add your client id and secret.

The code will look for this file in several places in this order:

- The path specified by the ``CITYIQ_CONFIG`` env var
- ``.city-iq.yaml`` in the current dir
- ``city-iq.yaml`` in the current dir
- ``.city-iq.yaml`` in the user's home dir

Command Line
============

Getting assets and locations
----------------------------

Run the ``ciq_assets`` program to get assets and locations. For instance, to print
out walkways as JSON lines::

    $ ciq_assets --walkways

Or, to write all locations to a CSV file:

    $ ciq_assets -L locations.csv

Run ``ciq_assets -h`` to see all of the options

Getting events
--------------

The ``ciq__events`` program will scrape and cache events. It requests events
for a single or set of events at a time, and makes requests to the API
for all of the locations in the system. The requests are for a time range that begins
with the date specified either with the `--start-time` option, or the 'start_time:'
configuration in the config file.

For instance, to scrape pedestrian event::

  $ ciq_events -s ped

The program will report the number of events it has downloaded and written,
as well as the number that have been skipped because they are cached. To list the
files that have been cached with the ``-l`` option::

  $ ciq_events -l ped

You can iterate the records from the cached files with the ``-i`` option::

  $ ciq_events -i ped


The Documentation_ has more details, but not much more.



Devlopment
==========


Committing
----------

The project scaffold gets the version number for the module from git. To get the version number::

    $ python setup.py --version

Set the version with a tag. The version numbers are specified with PEP440_ ::

    $ git tag 0.0.1

Publishing
----------

Publish the project to to PyPI_ with twine::

    pip install twine
    twine upload dist/*

Scaffolding
-----------

This project has been set up using PyScaffold 3.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.


.. _CityIQ: https://developer.currentbyge.com/cityiq
.. _PEP440: http://www.python.org/dev/peps/pep-0440/
.. _PyPI: https://pypi.org/
.. _Scraping: https://sandiegodata.github.io/cityiq/html/index.html#module-cityiq.cli.events
.. _Documentation: https://sandiegodata.github.io/cityiq/
