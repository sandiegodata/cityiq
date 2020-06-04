
==========
CityIQ API
==========


This module and command line tool provides access to the CityIQ API, with
particular focus on getting metadata and parking events. The interface includes
a basic access object for getting metadata and events, a scraper object for
mass downloading events, and a command line tool for downloading and processing
events.

Quickstart
==========

Install the module with pip:

.. code-block:: bash

    pip install cityiq

Then generate a configuration file with:

.. code-block:: bash

    ciq_config  -w

Edit the file with your credentials and other information for your system. The
default file is configured for the San Diego system, but you may have to `update
the client id and password <https://www.sandiego.gov/sustainability/energy-and-water-efficiency/programs-projects/smart-city>`_.

You can list the nodes, assets and locations in the system with the :program:`ciq_nodes`
program:

.. code-block:: bash

    ciq_nodes --locations # display locations a JSON lines
    ciq_nodes --cameras # display camera assets as JSON lines
    # etc

You can also dump all assets or all locations to CSV files.

.. code-block:: bash

    ciq_nodes -A assets.csv
    ciq_nodes -L locations.csv

Getting events is a two step process, and can be done with either the CLI programs
or the Python API. To get events with the CLI, fors download them to the cache.
The cache location is defined in the configuration file, and should have at least
100GB of free space.

First, download and cache the events. The download will run for all of the
assets that have the given event, over the whole time range. On the San Diego system,
time ranges longer than a few months can take days to download.

.. code-block:: bash

    ciq_events -e BICYCLE -s 2020-01-01 -f 2020-02-01

The downloaded data is stored in the cache as CSV files, which you can load directly
in which pandas or dask, or convert to one CSV file per asset:

.. code-block:: bash

    ciq_events -e BICYCLE -s 2020-01-01 -f 2020-02-01

You can combine them into a single file with:

.. code-block:: bash

    cat  $(ls -1 | head -1) | head -n1 > combined.csv
    for f in *.csv; do cat "`pwd`/$f" | tail -n +2 >> combined.csv; done


Contents
========

.. toctree::
   :maxdepth: 1

   Configuration <config>
   Using the CLI <cli>
   Using the API <api>
   Module Reference <api/modules>



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
