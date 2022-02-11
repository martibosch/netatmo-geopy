"""Authentication."""

import requests_oauthlib
from oauthlib import oauth2

from . import settings

__all__ = ["NetatmoConnect"]


class RefreshOAuth2Session(requests_oauthlib.OAuth2Session):
    """RefreshOAuth2Session."""

    # see https://github.com/requests/requests-oauthlib/issues/260
    def request(self, *args, **kwargs):
        try:
            return super().request(*args, **kwargs)
        except oauth2.TokenExpiredError:
            self.token = self.fetch_token(**self.auto_refresh_kwargs)
            self.token_updater(self.token)
            return super().request(*args, **kwargs)


class NetatmoConnect(object):
    """NetatmoConnect."""

    _session = None
    _token = None

    def __init__(self, client_id, client_secret, username, password, *args, **kwargs):
        super(NetatmoConnect, self).__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.scope = "read_station"

    def token_updater(self, token):
        """Token updater."""
        self._token = token

    @property
    def session(self):
        """Session."""
        if self._session is None:
            self._session = RefreshOAuth2Session(
                client=oauth2.LegacyApplicationClient(
                    client_id=self.client_id, scope=self.scope
                ),
                token=self.token,
                token_updater=self.token_updater,
                auto_refresh_kwargs={
                    "token_url": settings.OAUTH2_TOKEN_URL,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": self.username,
                    "password": self.password,
                },
            )
        return self._session

    @property
    def token(self):
        """Token."""
        if self._token is None:
            self._token = RefreshOAuth2Session(
                client=oauth2.LegacyApplicationClient(
                    client_id=self.client_id, scope=self.scope
                )
            ).fetch_token(
                token_url=settings.OAUTH2_TOKEN_URL,
                client_id=self.client_id,
                client_secret=self.client_secret,
                username=self.username,
                password=self.password,
            )
        return self._token
