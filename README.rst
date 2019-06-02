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

The generated file is configured for the San Diego system. To you this system , you will just need to add your client id and secret.

The code will look for this file in several places in this order:

- The path specified by the ``CITYIQ_CONFIG`` env var
- ``.city-iq.yaml`` in the current dir
- ``city-iq.yaml`` in the current dir
- ``.city-iq.yaml`` in the user's home dir

Use
===

After generating a config file you can run the ``ciq_`` programs to get events, assets and locations. The ``ciq_assets``
will list all of the system assets as JSON lines::

    $ ciq_assets



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
