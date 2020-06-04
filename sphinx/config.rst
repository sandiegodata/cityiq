Configuration
=============

The CityIq module and programs require a configuration file that holds
credentials and urls. You can generate a default configuration with ::

    ciq_config  -w

The generated file is configured for the San Diego system. To use this system,
you will just need to add your client id and secret to the file. ( The default
file has credentials for San Diego, which may work if they are not expired . )

The :py:class:`Config` object can be constructed on a path
where the config file is location. If none is specified it will look for this
file in several places, in this order:
s

- The path specified in the constructor
- The path specified by the ``CITYIQ_CONFIG`` env var
- ``.city-iq.yaml`` in the current dir
- ``city-iq.yaml`` in the current dir
- ``.city-iq.yaml`` in the user's home dir

Each of the configuration files can be overridden with a keyword in the
``Config`` object constructor, and each value can be accessed as an attribute
or an index. The nested cache values are special. To access or set them, preceede the key
with `cache_`.

.. code-block:: python

    c = Config(default_zone = 'SD-IE-TRAFFIC', cache_objects='/Volumes/foobar)

    print(c.default_zone)
    print(c['cache_objects'])

You can also set configuration values with environmental variables, by
uppercasing the variable name and prefixing it with ``CITYIQ_``:

.. code-block:: bash

    $ CITYIQ_CACHE_OBJECTS=/tmp/foo/bar ciq_config -p

    ...
    cache_errors: /Volumes/SSD_Extern/cityiq2/errors
    cache_meta: /Volumes/SSD_Extern/cityiq2/meta
    cache_objects: /tmp/foo/bar
    ...

