import sys


def group_to_events(group):

    if group == 'parking':
        events = ['PKIN', 'PKOUT']
    elif group == 'ped':
        events = ['PEDEVT']
    elif group == 'bicycle':
        events = ['BICYCLE']
    elif group == 'traffic':
        events = ['TFEVT']
    elif group == 'env':
        events = ['TEMPERATURE','HUMIDITY','PRESSURE']
    elif group == 'all':
        events = None
    else:
        print("ERROR: Unkown event group: {} ".format(group))
        sys.exit(1)


    return events


def group_to_locations(c, group):

    if group == 'parking':
        locations = list(c.parking_zones)  # Get all of the locations
    elif group == 'ped':
        locations = list(c.walkways)  # Get all of the locations
    elif group == 'traffic':
        locations = list(c.traffic_lanes)  # Get all of the locations
    elif group == 'bicycle':
        locations = list( set(c.cameras))   # Get all of the locations
    elif group == 'env':
        raise Exception("Environment events must be linked to assets, not Locations. sorry")
    else:
        locations = []

    return locations