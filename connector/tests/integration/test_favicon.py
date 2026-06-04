"""Integration tests for favicon/icon routes on the mock server."""

import pytest
import requests

from tests.conftest import _get_config


class TestFaviconRoutes:
    """Favicon and icon routes should return 204 instead of 404."""

    @pytest.fixture(autouse=True)
    def _server_url(self, _mock_server_process):
        base_url, _, _, _ = _get_config()
        # Strip /api suffix to get server root
        self.server_url = base_url.rsplit("/api", 1)[0]

    def test_favicon_ico_returns_204(self):
        resp = requests.get(f"{self.server_url}/favicon.ico", timeout=5)
        assert resp.status_code == 204

    def test_apple_touch_icon_returns_204(self):
        resp = requests.get(f"{self.server_url}/apple-touch-icon.png", timeout=5)
        assert resp.status_code == 204

    def test_apple_touch_icon_precomposed_returns_204(self):
        resp = requests.get(
            f"{self.server_url}/apple-touch-icon-precomposed.png", timeout=5
        )
        assert resp.status_code == 204
