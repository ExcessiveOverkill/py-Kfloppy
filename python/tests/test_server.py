from pathlib import Path

from kfloppy.config import AppConfig, SerialConfig
from kfloppy.protocol import CommandEvent, EventKind
from kfloppy.server import KFloppyServer


class FakeTransport:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def read(self, size: int = 1) -> bytes:
        return b""

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def close(self) -> None:
        pass


def make_server(tmp_path: Path) -> tuple[KFloppyServer, FakeTransport]:
    transport = FakeTransport()
    config = AppConfig(
        serial=SerialConfig(),
        storage_root=tmp_path,
        log_file=tmp_path / "pykfloppy.log",
        large_buffer=False,
        verbose=False,
    )
    return KFloppyServer(config, transport=transport), transport


def test_directory_request_sends_listing(tmp_path):
    (tmp_path / "TEST1.TP").write_bytes(b"one")
    (tmp_path / "TEST2.TP").write_bytes(b"two")
    server, transport = make_server(tmp_path)

    server._handle_command(CommandEvent(kind=EventKind.COMMAND, raw=b"DIR", command="DIR", argument=b""))

    assert transport.writes[0] == b"\x06"
    assert transport.writes[1] == b"TEST1.TP\r\nTEST2.TP\r\n"


def test_read_transfer_streams_file_bytes(tmp_path):
    (tmp_path / "TEST1.TP").write_bytes(b"hello world")
    server, transport = make_server(tmp_path)

    server._handle_command(CommandEvent(kind=EventKind.COMMAND, raw=b"SLF", command="SLF", argument=b"TEST1.TP"))
    server._handle_command(CommandEvent(kind=EventKind.COMMAND, raw=b"RTR", command="RTR", argument=b"5"))

    assert transport.writes[0] == b"\x06"
    assert transport.writes[1] == b"\x06"
    assert transport.writes[2] == b"hello"
