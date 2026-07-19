# pyKfloppy

Python rewrite of the KFLOPPY serial floppy emulator for FANUC RJ2 / PS-100 / PS-200 controllers.

## Current status

This first implementation slice provides:

- serial config loading
- stream parsing for STX/EOT framed commands
- MF2-style host directory mapping
- basic command handling for `SLF`, `DFF`, `RTS`, `CLR`, and `RQS`
- a CLI entry point

## Run

### Option 1: Direct module execution (no install)

From the `python/` directory:
```bash
cd python
python -m kfloppy --config config/kfloppy.ini --root ..\captures --dry-run
```

### Option 2: Using the convenience runner script

From the `python/` directory:
```bash
cd python
python run_kfloppy.py --config config/kfloppy.ini --root ..\captures --dry-run
```

Or from the workspace root:
```bash
python run_kfloppy.py --config python/config/kfloppy.ini --root captures --dry-run
```

### Option 3: Install and use as a command

```bash
cd python
python -m pip install -e .
pykfloppy --config config/kfloppy.ini --root ..\captures --dry-run
```

### All available options

```bash
python run_kfloppy.py --help
```

Common flags:
- `--config <path>` - Path to INI config file (optional)
- `--root <path>` - Override MF2 root directory
- `--port <port>` - Serial port (COM1, /dev/ttyS0, etc.)
- `--baudrate <rate>` - Baud rate (default 19200)
- `--parity <N|E|O>` - Parity (default N)
- `--timeout <seconds>` - Serial timeout (default 1.0)
- `--dry-run` - Start without opening a serial port
- `--verbose` - Enable debug logging

## Debug In VS Code

Use the workspace launch configurations in `.vscode/launch.json`:

- **pyKfloppy: Dry Run** - validates startup and config without touching serial hardware.
- **pyKfloppy: Serial Emulator** - opens the configured serial port and waits for controller traffic.
- **pyKfloppy: Serial Emulator (Choose Port)** - prompts for a COM port each time you start debugging.

Quick steps:

1. Open the Run and Debug panel.
2. Select one of the `pyKfloppy` launch profiles.
3. Press `F5`.

At startup you should see logs like:

- `Starting pyKfloppy (...)`
- `Serial config: ...`
- `Serial transport connected; waiting for controller traffic`

If no traffic arrives, the emulator now logs every 10 seconds:

- `No serial data received yet; still waiting`
