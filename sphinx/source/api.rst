
Using the API
=============

API objects are the primary way to get access to assets and events. :py:class:`CityIq` is the top level access
object. The API offers access to Locations, Events and Events.

Typically, you will construct :py:class:`CityIq` from a :py:class:`Config`. If a configuration is not specific,
the system will look for the file in default locations. You can also override individual configuration parameters
with keyword arguments to the constructor.

Metadata Access
---------------

Metadata, for both locations and assets, can be fetched with property accessors. The bounding box for the queries can
be set in the configuration, or on the  :py:class:`CityIq` constructor.

The asset metadata properties are:

- :py:attr:`CityIq.assets` : All assets
- :py:attr:`CityIq.nodes` : Nodes, the parents for other assets on a pole
- :py:attr:`CityIq.cameras` : All assets
- :py:attr:`CityIq.em_sensors` : ?
- :py:attr:`CityIq.env_sensors` : Environmental sensors

The location metadata properties are:

- :py:attr:`CityIq.locations` : All locations
- :py:attr:`CityIq.walkways` :
- :py:attr:`CityIq.parking_zones` :
- :py:attr:`CityIq.traffic_lane` :

Events can be fetched with :py:func:`cityiq.api.CityIq.events`

Each of these acessor properties or functions returns a generator that generates objects of a specific type,
one base class for each of Locations, Assets or Events:

- :py:class:`Asset`
- :py:class:`Location`
- :py:class:`Event`

.. code-block:: python

    bbox = '32.718987:-117.174244,32.707356:-117.154850'

    c = CityIq(bbox=bbox) # Use default config, override bbox

    # Get Locations
    locations = list(c.locations)

    # Get the assets at this location:
    for location in locations:
        do_something_with(location.assets
