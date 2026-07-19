from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import configparser


@dataclass(slots=True)
class SerialConfig:
    port: str = "COM1"
    baudrate: int = 19200
    parity: str = "N"
    stopbits: float = 1.0
    timeout: float = 1.0


@dataclass(slots=True)
class AppConfig:
    serial: SerialConfig
    storage_root: Path
    log_file: Path
    large_buffer: bool = True
    verbose: bool = False


def default_config(config_path: str | Path | None = None) -> AppConfig:
    base = Path(config_path).resolve().parent if config_path else Path.cwd()
    return AppConfig(
        serial=SerialConfig(),
        storage_root=base / "mf2",
        log_file=base / "pykfloppy.log",
        large_buffer=True,
        verbose=False,
    )


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return default_config(None)

    config_path = Path(path)
    if not config_path.exists():
        return default_config(config_path)

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    section = parser["kfloppy"] if parser.has_section("kfloppy") else None

    def get_value(key: str, default: str) -> str:
        if section is None:
            return default
        return section.get(key, default)

    def get_int(key: str, default: int) -> int:
        if section is None:
            return default
        return section.getint(key, fallback=default)

    def get_float(key: str, default: float) -> float:
        if section is None:
            return default
        return section.getfloat(key, fallback=default)

    def get_bool(key: str, default: bool) -> bool:
        if section is None:
            return default
        return section.getboolean(key, fallback=default)

    serial = SerialConfig(
        port=get_value("port", "COM1"),
        baudrate=get_int("baudrate", 19200),
        parity=get_value("parity", "N").upper()[0],
        stopbits=get_float("stopbits", 1.0),
        timeout=get_float("timeout", 1.0),
    )
    storage_root = Path(get_value("storage_root", str(config_path.parent / "mf2")))
    log_file = Path(get_value("log_file", str(config_path.parent / "pykfloppy.log")))
    return AppConfig(
        serial=serial,
        storage_root=storage_root,
        log_file=log_file,
        large_buffer=get_bool("large_buffer", True),
        verbose=get_bool("verbose", False),
    )
