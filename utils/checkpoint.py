import json
import threading
from pathlib import Path
from typing import Any, Dict


class CheckpointStore:
    """Simple JSON checkpoint backend for resumable ETL jobs."""

    def __init__(self, checkpoint_path: str = "checkpoints/state.json") -> None:
        self.path = Path(checkpoint_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def load(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: Dict[str, Any]) -> None:
        with self._lock:
            tmp_path = self.path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        state = self.load()
        state[key] = value
        self.save(state)
