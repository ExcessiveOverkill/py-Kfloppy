from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


STX = 0x01
ETX = 0x03
EOT = 0x04
ACK = 0x06
NAK = 0x15


class EventKind(str, Enum):
    COMMAND = "command"
    DATA = "data"
    CONTROL = "control"


@dataclass(slots=True)
class ProtocolEvent:
    kind: EventKind
    raw: bytes


@dataclass(slots=True)
class CommandEvent(ProtocolEvent):
    command: str
    argument: bytes


@dataclass(slots=True)
class DataEvent(ProtocolEvent):
    pass


@dataclass(slots=True)
class ControlEvent(ProtocolEvent):
    code: int


class StreamParser:
    """Parse a serial byte stream into framed commands and raw data chunks."""

    def __init__(self) -> None:
        self._in_frame = False
        self._frame = bytearray()
        self._raw = bytearray()

    def feed(self, data: bytes) -> list[ProtocolEvent]:
        events: list[ProtocolEvent] = []
        for byte in data:
            if self._in_frame:
                if byte == EOT:
                    events.append(self._decode_frame(bytes(self._frame)))
                    self._frame.clear()
                    self._in_frame = False
                else:
                    self._frame.append(byte)
                continue

            if byte == STX:
                if self._raw:
                    events.append(DataEvent(kind=EventKind.DATA, raw=bytes(self._raw)))
                    self._raw.clear()
                self._in_frame = True
                self._frame.clear()
                continue

            if byte in (ACK, NAK, ETX, EOT):
                if self._raw:
                    events.append(DataEvent(kind=EventKind.DATA, raw=bytes(self._raw)))
                    self._raw.clear()
                events.append(ControlEvent(kind=EventKind.CONTROL, raw=bytes([byte]), code=byte))
                continue

            self._raw.append(byte)

        if self._raw:
            events.append(DataEvent(kind=EventKind.DATA, raw=bytes(self._raw)))
            self._raw.clear()

        return events

    def flush(self) -> list[ProtocolEvent]:
        events: list[ProtocolEvent] = []
        if self._frame:
            events.append(self._decode_frame(bytes(self._frame)))
            self._frame.clear()
            self._in_frame = False
        if self._raw:
            events.append(DataEvent(kind=EventKind.DATA, raw=bytes(self._raw)))
            self._raw.clear()
        return events

    def _decode_frame(self, payload: bytes) -> CommandEvent | DataEvent:
        if len(payload) >= 3:
            command = payload[:3].decode("ascii", errors="ignore").upper()
            remainder = payload[3:]
            if command.isalpha():
                if remainder.startswith(b"#"):
                    remainder = remainder[1:]
                return CommandEvent(
                    kind=EventKind.COMMAND,
                    raw=payload,
                    command=command,
                    argument=remainder,
                )
        return DataEvent(kind=EventKind.DATA, raw=payload)


def decode_ascii_argument(argument: bytes) -> str:
    return argument.decode("ascii", errors="ignore").strip()
