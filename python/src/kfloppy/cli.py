from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import AppConfig, SerialConfig, load_config
from .server import KFloppyServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pyKfloppy serial floppy emulator")
    parser.add_argument("--config", type=Path, help="Path to a config file")
    parser.add_argument("--root", type=Path, help="MF2 root directory override")
    parser.add_argument("--port", help="Serial port override")
    parser.add_argument("--baudrate", type=int, help="Serial baud rate override")
    parser.add_argument("--parity", help="Serial parity override (N/E/O)")
    parser.add_argument("--stopbits", type=float, help="Serial stop bits override")
    parser.add_argument("--timeout", type=float, help="Serial timeout override")
    parser.add_argument("--dry-run", action="store_true", help="Start without opening a serial port")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def apply_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    serial = SerialConfig(
        port=config.serial.port,
        baudrate=config.serial.baudrate,
        parity=config.serial.parity,
        stopbits=config.serial.stopbits,
        timeout=config.serial.timeout,
    )
    if args.port:
        serial.port = args.port
    if args.baudrate is not None:
        serial.baudrate = args.baudrate
    if args.parity:
        serial.parity = args.parity.upper()[0]
    if args.stopbits is not None:
        serial.stopbits = args.stopbits
    if args.timeout is not None:
        serial.timeout = args.timeout
    root = args.root if args.root is not None else config.storage_root
    return AppConfig(
        serial=serial,
        storage_root=Path(root),
        log_file=config.log_file,
        large_buffer=config.large_buffer,
        verbose=args.verbose or config.verbose,
    )


def open_serial(config: SerialConfig):
    try:
        import serial
    except ImportError as exc:  # pragma: no cover - import failure path
        raise RuntimeError("pyserial is required to open a serial port") from exc

    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
    }
    return serial.Serial(
        port=config.port,
        baudrate=config.baudrate,
        parity=parity_map.get(config.parity.upper()[0], serial.PARITY_NONE),
        stopbits=config.stopbits,
        timeout=config.timeout,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = apply_overrides(load_config(args.config), args)

    logging.basicConfig(
        level=logging.DEBUG if config.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger = logging.getLogger("pykfloppy")
    logger.info(
        "Starting pyKfloppy (root=%s, dry_run=%s, verbose=%s)",
        config.storage_root,
        args.dry_run,
        config.verbose,
    )
    logger.info(
        "Serial config: port=%s baudrate=%s parity=%s stopbits=%s timeout=%s",
        config.serial.port,
        config.serial.baudrate,
        config.serial.parity,
        config.serial.stopbits,
        config.serial.timeout,
    )

    transport = None
    if not args.dry_run:
        try:
            transport = open_serial(config.serial)
        except Exception as exc:
            logger.error("Failed to open serial port %s: %s", config.serial.port, exc)
            logger.error("Check port name, permissions, and that no other app is using the port.")
            return 2

    server = KFloppyServer(config, transport=transport)

    if args.dry_run:
        logger.info("Dry run mode enabled")
        return 0

    try:
        server.run_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        if transport is not None:
            transport.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
