import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TokenState:
    access_token: str
    refresh_token: str
    connect_sid: str
    token_provider: str


class FileBackedTokenStore:
    def __init__(self, path: Path, initial_state: TokenState) -> None:
        self._path = path
        self._state = initial_state
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._state = TokenState(**payload)
        else:
            self.save(initial_state)

    def load(self) -> TokenState:
        return self._state

    def save(self, state: TokenState) -> None:
        self._state = state
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(asdict(state), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self._path)

