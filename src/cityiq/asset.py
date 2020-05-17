from cityiq.api import CityIqObject


class Asset(CityIqObject):
    object_sub_dir = 'asset'
    detail_url_suffix = '/api/v2/metadata/assets/{}'
    locations_url_suffix = '/api/v2/metadata/assets/{}/locations'
    children_url_suffix = '/api/v2/metadata/assets/{}/subAssets'
    events_url_suffix = '/api/v2/event/assets/{uid}/events'

    row_header = 'assetUid assetType parentAssetUid mediaType events geometry'.split()

    # observed values for the assetType field
    types = ['NODE', 'EM_SENSOR', 'MIC', 'ENV_SENSOR', 'CAMERA']

    # Map asset types to subclasses



    @property
    def uid(self):
        return self.assetUid

    @property
    def lat(self):
        return self.coordinates.split(':')[0]

    @property
    def lon(self):
        return self.coordinates.split(':')[1]

    @property
    def detail(self):
        """Asset details"""
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        return Asset(self.client, r.json())

    @property
    def parent(self):
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.parentAssetUid)

        r = self.client.http_get(url)

        return Asset(self.client, r.json())

    @property
    def locations(self):
        """Locations at this asset"""
        from cityiq.location import Location

        url = self.client.config.metadata_url + self.locations_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        for e in r.json()['locations']:
            yield Location(self.client, e)

    @property
    def children(self):
        """Sub assets of this asset"""
        url = self.client.config.metadata_url + self.children_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        for e in r.json()['assets']:
            yield Asset(self.client, e)

    @property
    def event_types(self):
        """Return event types records"""
        return self.eventTypes

    def event_type(self, type):
        """Return a specific event type record"""
        pass


    def get_events(self, event_type, start_time, end_time=None):

        start_time = self.client.convert_time(start_time)
        end_time = self.client.convert_time(end_time)


        url = self.client.config.event_url + self.events_url_suffix.format(uid=self.uid)

        return self.client._events(url, event_type, start_time, end_time, bbox=False)

    @property
    def row(self):
        """Return most important fields in a row format"""
        from operator import attrgetter

        def evt_list(events):
            return ','.join(sorted(set(events or [])))

        ag = attrgetter(*Asset.row_header[:-2])

        return ag(self) + (evt_list(self.eventTypes), self.geometry)

    def __getstate__(self):
        odict = self.__dict__.copy()

        del odict['client']

        return odict

    def __setstate__(self, state):
        self.__dict__.update(state)


class NodeAsset(Asset):
    pass


class CameraAsset(Asset):
    pass


class EnvSensorAsset(Asset):
    pass


class EmSensorAsset(Asset):
    pass


class MicSensorAsset(Asset):
    pass


Asset.dclass_map = {'NODE': NodeAsset,
                  'CAMERA': CameraAsset,
                  'EM_SENSOR': EmSensorAsset,
                  'ENV_SENSOR': EnvSensorAsset,
                  'MIC': MicSensorAsset
                  }