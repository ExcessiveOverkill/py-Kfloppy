from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Protocol

from .config import AppConfig
from .protocol import ACK, NAK, CommandEvent, ControlEvent, DataEvent, StreamParser, decode_ascii_argument
from .storage import MF2Root, WriteSession


class SerialPort(Protocol):
    def read(self, size: int = 1) -> bytes: ...
    def write(self, data: bytes) -> int: ...
    def close(self) -> None: ...


@dataclass(slots=True)
class SessionState:
    selected_read_path: Path | None = None
    selected_read_bytes: bytes = b""
    selected_read_offset: int = 0
    directory_listing: bytes = b""
    directory_offset: int = 0
    write_session: WriteSession | None = None
    write_expected_length: int | None = None
    write_received: int = 0


class KFloppyServer:
    def __init__(self, config: AppConfig, transport: SerialPort | None = None) -> None:
        self.config = config
        self.transport = transport
        self.root = MF2Root(config.storage_root)
        self.parser = StreamParser()
        self.state = SessionState()
        self.logger = logging.getLogger("pykfloppy")
        self.logger.setLevel(logging.DEBUG if config.verbose else logging.INFO)

    def handle_bytes(self, data: bytes) -> None:
        for event in self.parser.feed(data):
            self._handle_event(event)

    def flush(self) -> None:
        for event in self.parser.flush():
            self._handle_event(event)

    def run_forever(self) -> None:
        if self.transport is None:
            raise RuntimeError("No transport configured")
        while True:
            chunk = self.transport.read(1024)
            if not chunk:
                continue
            self.handle_bytes(chunk)

    def _send(self, data: bytes) -> None:
        if self.transport is not None:
            self.transport.write(data)

    def _ack(self) -> None:
        self._send(bytes([ACK]))

    def _nak(self) -> None:
        self._send(bytes([NAK]))

    def _handle_event(self, event) -> None:
        if isinstance(event, CommandEvent):
            self._handle_command(event)
            return
        if isinstance(event, DataEvent):
            self._handle_data(event.raw)
            return
        if isinstance(event, ControlEvent):
            if event.code == ACK:
                self.logger.debug("Received ACK")
            elif event.code == NAK:
                self.logger.debug("Received NAK")

    def _handle_command(self, event: CommandEvent) -> None:
        command = event.command
        argument = decode_ascii_argument(event.argument)

        if command == "SLF":
            self._handle_select_file(argument)
        elif command in {"DIR", "LST", "DTR"}:
            self._handle_directory_request(argument)
        elif command in {"RTR", "RDR", "RDL"}:
            self._handle_read_transfer(argument)
        elif command == "DFF":
            self._handle_define_file(argument)
        elif command == "RTS":
            self._handle_receive_transfer(argument)
        elif command == "CLR":
            self._handle_clear()
        elif command == "RQS":
            self._handle_status_request()
        else:
            self.logger.info("Unknown command %s %s", command, argument)
            self._nak()

    def _handle_select_file(self, argument: str) -> None:
        path = self.root.resolve(argument)
        if path.exists():
            self.state.selected_read_path = path
            self.state.selected_read_bytes = path.read_bytes()
            self.state.selected_read_offset = 0
            self.logger.info("Received read file request: %s", path.name)
            self._ack()
            return

        self.state.selected_read_path = None
        self.state.selected_read_bytes = b""
        self.state.selected_read_offset = 0
        self.logger.info("Error opening file %r for read", path.name)
        self._nak()

    def _handle_directory_request(self, argument: str) -> None:
        listing = self._build_directory_listing(argument)
        self.state.directory_listing = listing
        self.state.directory_offset = 0
        self.logger.info("Directory requested")
        self._ack()
        self._send_directory_chunk()

    def _handle_read_transfer(self, argument: str) -> None:
        if self.state.selected_read_path is None:
            self.logger.info("Read transfer requested without a selected file")
            self._nak()
            return

        if argument:
            try:
                chunk_size = int(argument)
            except ValueError:
                chunk_size = self._block_size()
        else:
            chunk_size = self._block_size()

        self.logger.info("Read a data block")
        self._ack()
        self._send_read_chunk(chunk_size)

    def _handle_define_file(self, argument: str) -> None:
        session = self.root.begin_write(argument, overwrite=True)
        self.state.write_session = session
        self.state.write_expected_length = None
        self.state.write_received = 0
        self.logger.info("Receiving file %r", session.path.name)
        self._ack()

    def _handle_receive_transfer(self, argument: str) -> None:
        try:
            expected_length = int(argument or "0")
        except ValueError:
            expected_length = 0
        self.state.write_expected_length = expected_length or None
        self.logger.info("Received write block request: length=%s", self.state.write_expected_length)
        self._ack()

    def _handle_clear(self) -> None:
        if self.state.write_session is not None:
            written = self.state.write_session.finish()
            self.logger.info("File transferred, %d bytes", written)
            self.state.write_session = None
            self.state.write_expected_length = None
            self.state.write_received = 0
        elif self.state.selected_read_path is not None:
            self.logger.info("File closed")
            self.state.selected_read_path = None
            self.state.selected_read_bytes = b""
            self.state.selected_read_offset = 0
        elif self.state.directory_listing:
            self.logger.info("Directory request complete")
            self.state.directory_listing = b""
            self.state.directory_offset = 0
        else:
            self.logger.info("Received clear request")
        self._ack()

    def _handle_status_request(self) -> None:
        self.logger.info("Received status request")
        self._send(b"\x06\x02\x33\x04")

    def _handle_data(self, raw: bytes) -> None:
        if self.state.write_session is None:
            if raw.strip():
                self.logger.debug("Ignoring raw data outside write session: %r", raw)
            return

        self.state.write_session.append(raw)
        self.state.write_received += len(raw)
        self.logger.info("Writing a data block")

        if self.state.write_expected_length is not None and self.state.write_received >= self.state.write_expected_length:
            self.logger.debug("Received expected write length: %d", self.state.write_received)
            self.state.write_expected_length = None

    def _build_directory_listing(self, argument: str) -> bytes:
        files = self.root.list_files()
        if argument:
            needle = argument.upper()
            files = [name for name in files if needle in name.upper()]
        if not files:
            return b""
        return b"\r\n".join(name.encode("ascii", errors="ignore") for name in files) + b"\r\n"

    def _block_size(self) -> int:
        return 2048 if self.config.large_buffer else 128

    def _send_directory_chunk(self) -> None:
        if not self.state.directory_listing:
            return
        start = self.state.directory_offset
        chunk_size = self._block_size()
        chunk = self.state.directory_listing[start : start + chunk_size]
        if not chunk:
            return
        self.state.directory_offset += len(chunk)
        self._send(chunk)

    def _send_read_chunk(self, requested_size: int | None = None) -> None:
        if self.state.selected_read_path is None:
            return

        block_size = requested_size or self._block_size()
        start = self.state.selected_read_offset
        chunk = self.state.selected_read_bytes[start : start + block_size]
        if not chunk:
            self.logger.info("File transferred, %d bytes", self.state.selected_read_offset)
            self._send(b"\x04")
            return

        self.state.selected_read_offset += len(chunk)
        self._send(chunk)

