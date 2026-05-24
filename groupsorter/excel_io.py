"""Excel file loading (including password-protected files) and export."""

from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl import load_workbook as _xl_load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .domain import Person


def open_workbook(path: str | Path, password: str | None = None) -> Workbook:
    """Load an Excel workbook, decrypting it first if a password is provided.

    Raises:
        ValueError: if the password is wrong or the file cannot be opened.
    """
    path = Path(path)
    if password:
        try:
            import msoffcrypto

            with path.open("rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                office_file.load_key(password=password)
                decrypted = io.BytesIO()
                office_file.decrypt(decrypted)
            decrypted.seek(0)
            return _xl_load_workbook(decrypted, data_only=True)
        except Exception as exc:
            raise ValueError(f"Could not open file with the provided password: {exc}") from exc
    else:
        try:
            return _xl_load_workbook(path, data_only=True)
        except Exception as exc:
            # Some encrypted files raise an error even without a password prompt
            if "encrypted" in str(exc).lower() or "password" in str(exc).lower():
                raise ValueError("This file appears to be password-protected.") from exc
            raise


def is_password_protected(path: str | Path) -> bool:
    """Return True if the file appears to be password-protected.

    Raises OSError if the file cannot be read (e.g. not found, permission denied).
    """
    import msoffcrypto
    try:
        with Path(path).open("rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            return office_file.is_encrypted()
    except OSError:
        raise
    except Exception:
        return False


def sheet_names(wb: Workbook) -> list[str]:
    return wb.sheetnames


def column_headers(ws: Worksheet) -> list[str]:
    """Return non-empty header values from the first row."""
    headers = []
    for cell in ws[1]:
        val = cell.value
        if val is not None:
            headers.append(str(val))
    return headers


def read_people(
    ws: Worksheet,
    name_col: str,
    dob_col: str,
    gender_col: str | None = None,
) -> list[Person]:
    """Read people from a worksheet using the given column header names."""
    headers = [str(cell.value) if cell.value is not None else "" for cell in ws[1]]
    try:
        name_idx = headers.index(name_col)
        dob_idx = headers.index(dob_col)
    except ValueError as exc:
        raise ValueError(f"Column not found in sheet: {exc}") from exc

    gender_idx: int | None = None
    if gender_col is not None:
        try:
            gender_idx = headers.index(gender_col)
        except ValueError as exc:
            raise ValueError(f"Column not found in sheet: {exc}") from exc

    people: list[Person] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        name_val = row[name_idx] if name_idx < len(row) else None
        dob_val = row[dob_idx] if dob_idx < len(row) else None

        if name_val is None and dob_val is None:
            continue  # skip blank rows

        name = str(name_val).strip() if name_val is not None else "(no name)"
        dob, raw = _parse_dob(dob_val)

        gender: str | None = None
        raw_gender: str = ""
        if gender_idx is not None:
            gender_val = row[gender_idx] if gender_idx < len(row) else None
            gender, raw_gender = _parse_gender(gender_val)

        people.append(Person(name=name, dob=dob, raw_dob=raw, gender=gender, raw_gender=raw_gender))
    return people


def _parse_gender(value: object) -> tuple[str | None, str]:
    """Parse a gender cell. Returns (normalised, raw) where normalised is 'M', 'F', or None."""
    if value is None:
        return None, ""
    raw = str(value).strip()
    upper = raw.upper()
    if upper in ("M", "MALE"):
        return "M", raw
    if upper in ("F", "FEMALE"):
        return "F", raw
    return None, raw


def _parse_dob(value: object) -> tuple[date | None, str]:
    """Try to parse a cell value as a date. Returns (date_or_None, raw_string)."""
    if value is None:
        return None, ""
    if isinstance(value, datetime):
        return value.date(), str(value.date())
    if isinstance(value, date):
        return value, str(value)
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date(), raw
        except ValueError:
            continue
    return None, raw


def export_results(
    path: str | Path,
    groups: list[list[Person]],
    anomalies: list[Person],
    gender_anomalies: list[Person] | None = None,
) -> None:
    """Write group sheets + an Anomalies sheet to a new Excel file."""
    wb = Workbook()
    wb.remove(wb.active)

    all_people = [p for group in groups for p in group]
    include_gender = any(p.gender is not None for p in all_people) or gender_anomalies is not None

    for i, group in enumerate(groups, 1):
        ws = wb.create_sheet(title=f"Group {i}")
        headers: list[str] = ["Name", "Date of Birth"]
        if include_gender:
            headers.append("Gender")
        ws.append(headers)
        for person in group:
            dob_str = f"{person.dob.strftime('%b')} {person.dob.day}, {person.dob.year}" if person.dob else person.raw_dob
            row: list[object] = [person.name, dob_str]
            if include_gender:
                row.append(person.gender or "")
            ws.append(row)
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=0)
            ws.column_dimensions[col[0].column_letter].width = max_len + 4

    ws_a = wb.create_sheet(title="Anomalies")
    ws_a.append(["Name", "Date of Birth", "Note"])
    for person in anomalies:
        dob_str = (
            f"{person.dob.strftime('%b')} {person.dob.day}, {person.dob.year}" if person.dob else f"(unreadable: {person.raw_dob})"
        )
        note = "DOB outside expected range" if person.dob else "DOB missing or unreadable"
        ws_a.append([person.name, dob_str, note])
    if gender_anomalies:
        ws_a.append([])
        ws_a.append(["── Gender Anomalies ──", "", ""])
        for person in gender_anomalies:
            dob_str = (
                f"{person.dob.strftime('%b')} {person.dob.day}, {person.dob.year}" if person.dob else f"(unreadable: {person.raw_dob})"
            )
            note = (
                f"Gender unrecognised: {person.raw_gender!r}"
                if person.raw_gender
                else "Gender missing"
            )
            ws_a.append([person.name, dob_str, note])
    for col in ws_a.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws_a.column_dimensions[col[0].column_letter].width = max_len + 4

    wb.save(path)
