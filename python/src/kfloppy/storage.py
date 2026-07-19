from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def sanitize_filename(name: str) -> str:
    candidate = Path(name).name.strip()
    cleaned = []
    for character in candidate:
        if character.isalnum() or character in {".", "_", "-", " "}:
            cleaned.append(character)
        elif character in {"/", "\\", ":"}:
            continue
        else:
            cleaned.append("_")
    sanitized = "".join(cleaned).strip()
    return sanitized.upper() or "UNNAMED"


@dataclass(slots=True)
class WriteSession:
    path: Path
    buffer: bytearray

    def append(self, data: bytes) -> None:
        self.buffer.extend(data)

    def finish(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(bytes(self.buffer))
        return len(self.buffer)


class MF2Root:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, name: str) -> Path:
        return self.root / sanitize_filename(name)

    def exists(self, name: str) -> bool:
        return self.resolve(name).exists()

    def read_bytes(self, name: str) -> bytes:
        return self.resolve(name).read_bytes()

    def begin_write(self, name: str, overwrite: bool = True) -> WriteSession:
        path = self.resolve(name)
        if path.exists() and not overwrite:
            raise FileExistsError(path)
        return WriteSession(path=path, buffer=bytearray())

    def list_files(self) -> list[str]:
        return sorted(entry.name for entry in self.root.iterdir() if entry.is_file())
