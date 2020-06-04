=============
Using the CLI
=============

The CityIq module includes two programs that can access a CityIQ system,
:program:`ciq_events` to download events and :program:`ciq_nodes` to
get locations and assets. The package also includes the :program:`ciq_config`
create and dump the config file.

**ciq_events**: Download events
-------------------------------

The :program:`ciq_events` downloads events from the CityIq system and caches the
events locally in CSV files, one file per day per event per asset. The :program:`ciq_events`
program can both download the events and, with the :option:`-O`, write combined CSV files.
The :option:`-O` option will produce  a directory of CSV file, with one file
for each asset, holding events over the entire date range.

.. autoprogram:: cityiq.cli.events:parser
    :prog: ciq_events

**ciq_nodes**: Download assets and locations
--------------------------------------------

.. autoprogram:: cityiq.cli.nodes:parser
    :prog: ciq_nodes


**ciq_config**: Manage the configuration file
---------------------------------------------

.. autoprogram:: cityiq.cli.config:parser
    :prog: ciq_config
