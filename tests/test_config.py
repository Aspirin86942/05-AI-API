from pathlib import Path

from fscut_openai_proxy.config import default_state_path, resolve_config_path


def test_default_config_path_is_project_config(monkeypatch) -> None:
    monkeypatch.delenv("FSCUT_PROXY_CONFIG", raising=False)
    monkeypatch.setenv("APPDATA", "C:/Users/example/AppData/Roaming")

    assert resolve_config_path() == Path("config.toml")


def test_env_config_path_still_overrides_default(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    monkeypatch.setenv("FSCUT_PROXY_CONFIG", str(config_path))

    assert resolve_config_path() == config_path


def test_default_state_path_stays_next_to_project_config() -> None:
    assert default_state_path(Path("config.toml")) == Path("token-state.json")

