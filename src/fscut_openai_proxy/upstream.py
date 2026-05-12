import httpx

from fscut_openai_proxy.auth import AuthManager, RefreshClient
from fscut_openai_proxy.config import Settings
from fscut_openai_proxy.errors import UpstreamAuthExpiredError, UpstreamRateLimitError


class UpstreamClient:
    def __init__(self, settings: Settings, auth_manager: AuthManager) -> None:
        self._settings = settings
        self._auth_manager = auth_manager
        self._refresh_client = RefreshClient(settings.upstream.base_url, auth_manager.token_store)

    def _do_post(self, payload: dict[str, object]) -> httpx.Response:
        try:
            token = self._auth_manager.current_access_token()
        except RuntimeError:
            self._refresh_client.refresh()
            token = self._auth_manager.token_store.load().access_token
        endpoint = httpx.URL(
            f"{self._settings.upstream.base_url}/api/agents/chat/{self._settings.upstream.agent_endpoint}"
        )
        return httpx.post(
            str(endpoint),
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
            timeout=300.0,
        )

    def post_chat(self, payload: dict[str, object]) -> httpx.Response:
        response = self._do_post(payload)
        if response.status_code == 401:
            self._refresh_client.refresh()
            response = self._do_post(payload)
        if response.status_code == 401:
            raise UpstreamAuthExpiredError()
        if response.status_code == 429:
            raise UpstreamRateLimitError()
        response.raise_for_status()
        return response
