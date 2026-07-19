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

```bash
python -m pip install -e .
pykfloppy --config config/kfloppy.ini --root ..\captures
```

If you do not want to open a serial port yet, use `--dry-run`.
