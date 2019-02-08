"""

"""

from os import environ

from cityiq.config import Config

from .support import CityIQTest


class TestConfig(CityIQTest):

    def test_basic(self):
        c1 = self.test_data('config1.yaml')
        c2 = self.test_data('config2.yaml')

        c = Config(c1)

        with self.assertRaises(AttributeError):
            self.assertEqual('client1', c.client)

        self.assertEqual('client1', c.client_id)

        c = Config(c1, client_id='client3')

        self.assertEqual('client3', c.client_id)

        #
        # ENV VARS

        environ['CITYIQ_CONFIG'] = c2

        c = Config()

        self.assertEqual('client2', c.client_id)

        environ['CITYIQ_CLIENT_ID'] = 'client4'

        self.assertEqual('client4', c.client_id)

        c = Config(client_id='client5')

        self.assertEqual('client5', c.client_id)

        #
        # User dir. Requires the user has a file at ~.city-iq.yaml

        # Path.home().joinpath('.city-iq.yaml').exists(),

        c = Config()

        del environ['CITYIQ_CLIENT_ID']
        print(c.client_id)
