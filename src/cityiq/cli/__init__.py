"""

The CityIq module includes two programs that can access a CityIQ system, 
:program:`ciq_events` to download events and :program:`ciq_nodes` to 
get locations and assets. 

**ciq_events**: Download events
===============================

.. autoprogram:: cityiq.cli.events:make_parser()
    :prog: ciq_events

**ciq_nodes**: Download assets and locations
=============================================

.. autoprogram:: cityiq.cli.nodes:make_parser()
    :prog: ciq_nodes

"""