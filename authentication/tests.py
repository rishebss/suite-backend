from datetime import timedelta

from django.conf import settings
from django.test import SimpleTestCase


class AuthTokenSettingsTests(SimpleTestCase):
    def test_token_lifetimes_are_long_enough_to_keep_users_signed_in(self):
        self.assertGreaterEqual(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"], timedelta(hours=24))
        self.assertGreaterEqual(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta(days=7))
