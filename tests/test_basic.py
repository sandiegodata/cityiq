"""

"""

import logging
from datetime import datetime
from pathlib import Path
from pprint import pprint
from cityiq.api import CityIq, CacheFile
from cityiq.config import Config
from cityiq.util import event_type_to_location_type
from cityiq.api import CityIq, logger as api_logger
from cityiq.task import logger as task_logger
from .support import CityIQTest
from cityiq.task import generate_days

logging.basicConfig()

class TestBasic(CityIQTest):



    def test_config_paths(self):
        self.assertEqual('/tmp/cityiq/objects', self.config.cache_objects)

    def test_get_token(self):
        c = CityIq(self.config)

        self.assertTrue(len(c.token) > 100)

    def test_time(self):

        c = CityIq(self.config)

        dt = c.tz.localize(datetime(2020, 1, 1, 0, 0, 0))

        for t in ('2020-01-01', 1577865600, datetime(2020, 1, 1, 0, 0, 0)):
            self.assertEqual(dt, c.convert_time(t))

        now = c.tz.localize(datetime.now())

        for t in ('now', None):
            self.assertEqual(int(now.timestamp()), int(c.convert_time(t).timestamp()))

        print(c.convert_time('now').replace(hour=0, minute=0, second=0, microsecond=0))

    def test_cache_assets_locations(self):
        from time import time

        c = CityIq(self.config)

        c.clear_meta_cache()

        # These should take gonger because
        # they are making the full request
        t = time()
        o = c.get_locations()
        self.assertGreater(time() - t, 1)
        self.assertGreater(len(o), 500)

        t = time()
        c.get_assets()
        self.assertGreater(time() - t, 4)
        o = self.assertGreater(len(o), 500)

        # These should be fast, because they are cached.
        t = time()
        o = c.get_locations()
        self.assertLess(time() - t, 1)
        self.assertGreater(len(o), 500)

        t = time()
        o = c.get_assets()
        self.assertLess(time() - t, 1)
        self.assertGreater(len(o), 500)

    def test_total_bbox(self):

        c = CityIq(self.config)

        bb = c.total_bounds

        print(bb)
        print(c.total_bounds_str)

        a = (bb[2] - bb[0]) * (bb[1] - bb[3])

        self.assertEqual(0.13, round(a, 2))





    def test_event_overlaps(self):

        from cityiq.task import request_ranges

        from dateutil.relativedelta import relativedelta

        d1 = relativedelta(days=1)

        c = CityIq(self.config)

        extant = list(generate_days(c.convert_time('2020-01-01'), c.convert_time('2020-01-05'))) + \
                list(generate_days(c.convert_time('2020-01-10'), c.convert_time('2020-01-15'))) + \
                list(generate_days(c.convert_time('2020-01-20'), c.convert_time('2020-01-25')))

        extant = [ e[0] for e in extant]

        rr = request_ranges(c.convert_time('2020-01-01'), c.convert_time('2020-02-01'), extant)

        dts = sorted(c.convert_time(e[0]).date().isoformat() for e in rr)
        dte = sorted(c.convert_time(e[1]).date().isoformat() for e in rr)

        self.assertEqual(dts, ['2020-01-05', '2020-01-15', '2020-01-25'])
        self.assertEqual(dte, ['2020-01-10', '2020-01-20', '2020-02-01'])

    def test_cache_file(self):

        c = CityIq(self.config)

        dt = c.convert_time('2020-01-01')

        l = c.get_location('09a66ff9a2c0cb63106fe0054412c2af')

        cf = CacheFile(self.config.cache_objects, l, event_type='PKIN', dt=dt, format='csv')

        print(cf.path)

        # Bare CF
        cf.delete()
        self.assertFalse(cf.exists())

        cf.write(['foo!'])

        self.assertTrue(cf.exists())
        self.assertEqual(cf.read()[0], 'foo!')

        # From the location
        cf = l.cache_file(event_type='PKIN', dt=dt)

        self.assertTrue(cf.exists(), cf.path)
        self.assertEqual(cf.read()[0], 'foo!')

        cf.delete()
        self.assertFalse(cf.exists())

        cf.write(['foo!'])

        self.assertTrue(cf.exists())
        self.assertEqual(cf.read()[0], 'foo!')




    def test_consec_days_raw(self):
        """Test that two requests for consecutive days returns the
        same number of records as one request for both days. """

        import requests, json

        c = CityIq(self.config)

        headers = c.request_headers(zone='SD-IE-PARKING')

        def make_url(start, end):
            url = 'https://sandiego.cityiq.io/api/v2/event/locations/0d152fbd26c5baad229556c01d3eb43b/events'

            params = c._event_params(start, end, 'PKIN', bbox=False)
            url = c.process_url(url, params)

            return params, url,

        p, url = make_url('2020-01-01', '2020-01-03')

        r1 = requests.get(url, headers=headers)

        r1.raise_for_status()
        print(json.dumps(r1.json()['metaData'], indent=4))
        l1 = int(r1.json()['metaData']['totalRecords'])

        p, url = make_url('2020-01-01', '2020-01-02')

        r2 = requests.get(url, headers=headers)
        l2 = int(r2.json()['metaData']['totalRecords'])

        p, url = make_url('2020-01-02', '2020-01-03')

        r3 = requests.get(url, headers=headers)
        l3 = int(r3.json()['metaData']['totalRecords'])

        print(l1, l2, l3, l2 + l3)

        self.assertEquals(l1, l2 + l3)



    def test_nodes(self):

        c = CityIq(self.config)

        n_childs = 0

        for i, n in enumerate(c.nodes):
            for c in n.children:
                n_childs += 1

            if i > 5:
                break

        self.assertEqual(42, n_childs)

    def test_locations_detail(self):

        c = CityIq(self.config)

        for l in c.locations[60:70]:
            print(l.data.keys())
            d = l.detail
            print(d)


    def test_has_event(self):

        c = CityIq(self.config)

        for i, n in enumerate(c.assets_by_event('TFEVT')):
            print(i, n.uid, n.assetType)

    def test_detail(self):

        c = CityIq(self.config)

        assets = c.assets

        a = assets[50]

        pprint(a.detail.data)

        children = list(a.children)

        pprint(children[0].parent.detail.data)

        for c in children:
            print(c)


    def test_list_by_event(self):

        c = CityIq(self.config)

        for a in c.assets_by_event('PEDEVT'):
            print(a)



    def test_dont_cache_today(self):
        from dateutil.relativedelta import relativedelta

        c = CityIq(self.config)
        api_logger.setLevel(logging.INFO)

        assets = list(c.assets_by_event('BICYCLE'))

        now =c.convert_time('now').replace(hour=0, minute=0, second=0, microsecond=0)

        d1 = relativedelta(days=2)

        st = now - d1
        et = now + d1

        assets[100].get_events('BICYCLE',st, et)
