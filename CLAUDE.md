# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Before running any Python commands, ask the user which virtual environment to use or whether to create one. All dependencies are declared in `pyproject.toml`.

```bash
# Install (including dev tools)
pip install -e ".[dev]"

# Run the GUI app
python -m groupsorter

# Run tests
pytest

# Run a single test file
pytest tests/test_sorter.py

# Lint
ruff check .
```

## Packaging for distribution

```bash
# Produces dist/GroupSorter (macOS .app or Windows .exe)
pyinstaller --onefile --windowed --name GroupSorter groupsorter/main.py
```

## Architecture

```text
groupsorter/
├── main.py       # Entry point — calls gui.App().mainloop()
├── gui.py        # Full tkinter GUI; orchestrates all other modules
├── excel_io.py   # Load .xlsx (+ password decrypt via msoffcrypto), read rows, export results
├── anomaly.py    # Person dataclass + find_anomalies()
├── sorter.py     # sort_groups(mode="mixed"|"isolated"), _proportional_allocate()
└── date_utils.py # School year calc, 6 standard age groups, sub_ranges() splitter
```

### Key design points

- **Age groups** are based on a July 1 cutoff. `date_utils.suggested_age_groups()` auto-calculates the 6 standard UK school year bands for the current school year. The final band (Y11–Y13) spans 3 years and produces 3 sub-ranges; all others span 2 years.
- **`sub_ranges(start, end)`** splits any date range into 1-school-year (July 1 – June 30) bands.
- **Mixed mode**: people from each sub-range are distributed round-robin across all groups so every group gets an even spread of ages.
- **Isolated mode**: groups are allocated proportionally to sub-ranges (`_proportional_allocate`), then people within each sub-range are distributed round-robin among that sub-range's groups.
- **Anomalies** (DOB outside range or missing) are excluded before sorting and shown separately. `excel_io.export_results()` writes one sheet per group plus an Anomalies sheet.
- **Password-protected files**: `excel_io.is_password_protected()` detects them; `load_workbook(path, password=...)` decrypts via `msoffcrypto` into a `BytesIO` buffer before passing to `openpyxl`.
