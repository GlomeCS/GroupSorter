# GroupSorter

A desktop application for dividing people into evenly distributed groups based on date of birth and school year age ranges. Designed for schools, youth clubs, and organisations that need to split cohorts fairly by age.

---

## Purpose

GroupSorter takes a list of people from an Excel spreadsheet (with names and dates of birth) and distributes them across a configurable number of groups. Groups can be balanced so that each contains a proportional spread of ages, or isolated so each group contains people from a single school year.

It is particularly suited to UK/Irish school year structures, using a **1 July** cutoff to define year boundaries.

---

## Features

- Load people data from `.xlsx` or `.xls` files, including **password-protected** workbooks
- Auto-detect name and date-of-birth columns from headers
- Choose from **6 pre-defined UK school year age bands** or enter a **custom date range**
- Two sorting modes:
  - **Mixed** — distributes people round-robin so each group contains a spread of ages
  - **Isolated** — groups are allocated by school year sub-range; each group contains people from only one year band
- **Anomaly detection** — identifies and separates records with missing, unparseable, or out-of-range dates of birth
- Export results to a new Excel file with one worksheet per group and a dedicated Anomalies sheet
- Preview results in the app before exporting

---

## Age Groups

Six standard UK school year bands are offered, calculated automatically for the current school year:

| Label | Stage | Ages |
|---|---|---|
| P1 & P2 | Foundation Stage | 4–6 |
| P3 & P4 | Key Stage 1 | 6–8 |
| P5 & P6 | Key Stage 2 | 8–10 |
| P7 & Year 8 | Transition | 10–12 |
| Year 9 & Year 10 | Key Stage 3 | 12–14 |
| Year 11–13 | Key Stage 4 & Post-16 | 14–17 |

Custom start and end dates (YYYY-MM-DD) can also be entered directly.

When a date range spans more than one school year, it is automatically split into **sub-ranges** at July 1 boundaries and used to drive the sorting logic.

---

## Supported Date Formats

Dates of birth in the spreadsheet are accepted in the following formats:

- `YYYY-MM-DD`
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `MM/DD/YYYY`
- `DD Mon YYYY` (e.g. `15 Jan 2010`)
- `DD Month YYYY` (e.g. `15 January 2010`)

---

## Platform

GroupSorter runs on any platform with Python 3.11+ and Tkinter (included in standard Python distributions on macOS and Windows). It can also be packaged as a standalone executable for macOS or Windows using PyInstaller — no Python installation required by end users.

---

## Requirements

- Python >= 3.11
- `openpyxl` >= 3.1
- `msoffcrypto-tool` >= 5.4
- Tkinter (bundled with Python)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/your-org/GroupSorter.git
cd GroupSorter

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install runtime dependencies
pip install -r requirements.txt

# Or, for development (includes pytest, ruff, pyinstaller)
pip install -r requirements-dev.txt
```

---

## Running

```bash
# Run the GUI app
python -m groupsorter

# Or, if installed via pip
groupsorter
```

---

## Packaging as a Standalone Executable

```bash
pyinstaller --onefile --windowed --name GroupSorter groupsorter/main.py
```

The output is placed in `dist/GroupSorter` (a `.app` bundle on macOS, `.exe` on Windows).

---

## Development

```bash
# Run tests
pytest

# Run a single test file
pytest tests/test_sorter.py

# Lint
ruff check .
```

---

## Typical Workflow

1. Launch the app
2. Load an Excel file (enter a password if the file is protected)
3. Select the sheet and identify the name and date-of-birth columns, then click **Load People**
4. Select a predefined age group or enter a custom date range
5. Optionally run **Check Anomalies** to review data quality before sorting
6. Set the number of groups and choose a sorting mode (Mixed or Isolated)
7. Click **Sort Groups** to preview the result
8. Click **Export to Excel** to save the grouped output

---

## Output Format

The exported Excel file contains:

- One worksheet per group, labelled `Group 1`, `Group 2`, etc.
- An `Anomalies` sheet listing any records that were excluded and why
- Auto-sized columns for readability
