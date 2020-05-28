from cityiq.api import CityIqObject


class Asset(CityIqObject):
    object_sub_dir = 'asset'
    uid_key = 'assetUid'
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
        """Asset details, which appears to be just re-fetching the object data.
        On some systems it may return additional data.

        Most importantly, the read is not cached, so it can be used to return the
        online/offline state of an asset without a time delay. """
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.assetUid)

        r = self.client.http_get(url)

        a = Asset(self.client,r.json())

        a.write()

        return a


    @property
    def parent(self):
        url = self.client.config.metadata_url + self.detail_url_suffix.format(self.parentAssetUid)

        r = self.client.http_get(url)

        return Asset(self.client, r.json())

    @property
    def locations(self):
        """Locations at this asset"""
        from cityiq.location import Location

        def ff():
            url = self.client.config.metadata_url + self.locations_url_suffix.format(self.assetUid)
            r = self.client.http_get(url)
            return r.json()

        r = self.cache_file(ff, group='locations').run()

        for e in r['locations']:
            yield Location(self.client, e)

    @property
    def children(self):
        """Sub assets of this asset"""

        def ff():
            url = self.client.config.metadata_url + self.children_url_suffix.format(self.assetUid)
            r = self.client.http_get(url)
            return r.json()

        r = self.cache_file(ff, group='children').run()

        for e in r['assets']:
            yield Asset(self.client, e)

    @property
    def event_types(self):
        """Return event types records"""
        return self.eventTypes

    def event_type(self, type):
        """Return a specific event type record"""
        pass

    def has_events(self,events):
        if isinstance(events, str):
            events = [events]

        return set(self.event_types) & set(events)

    def get_events(self, event_type, start_time, end_time=None):
        from cityiq.task import DownloadTask

        start_time = self.client.convert_time(start_time)
        end_time = self.client.convert_time(end_time)

        tasks = DownloadTask.make_tasks([self], event_type, start_time, end_time)

        results = list(r[1] for r in self.client.run_sync(tasks))

        return results



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
