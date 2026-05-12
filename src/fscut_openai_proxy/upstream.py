import httpx

from fscut_openai_proxy.auth import AuthManager
from fscut_openai_proxy.config import Settings


class UpstreamClient:
    def __init__(self, settings: Settings, auth_manager: AuthManager) -> None:
        self._settings = settings
        self._auth_manager = auth_manager

    def post_chat(self, payload: dict[str, object]) -> httpx.Response:
        token = self._auth_manager.current_access_token()
        endpoint = httpx.URL(
            f"{self._settings.upstream.base_url}/api/agents/chat/{self._settings.upstream.agent_endpoint}"
        )
        return httpx.post(
            str(endpoint),
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
            timeout=300.0,
        )
