"""Anomaly detection: identify people whose DOB falls outside the expected range."""

from dataclasses import dataclass
from datetime import date


@dataclass
class Person:
    name: str
    dob: date | None      # None if the DOB cell was blank or unparseable
    raw_dob: str = ""     # original cell value, for display when dob is None
    gender: str | None = None  # "M", "F", or None (not loaded / blank / invalid)


def find_anomalies(
    people: list[Person],
    start_date: date,
    end_date: date,
) -> list[Person]:
    """Return people whose DOB is outside [start_date, end_date] or missing."""
    anomalies = []
    for person in people:
        if person.dob is None or not (start_date <= person.dob <= end_date):
            anomalies.append(person)
    return anomalies


def find_gender_anomalies(people: list[Person]) -> list[Person]:
    """Return people whose gender is None (blank or not M/F in the source data)."""
    return [p for p in people if p.gender is None]


def format_anomaly_report(anomalies: list[Person], start_date: date, end_date: date) -> str:
    if not anomalies:
        return "No DOB anomalies found — all DOBs are within the expected range."

    lines = [
        f"Expected range: {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}",
        f"DOB anomalies found: {len(anomalies)}",
        "",
    ]
    for p in anomalies:
        dob_str = p.dob.strftime("%d %b %Y") if p.dob else f"(unreadable: {p.raw_dob!r})"
        lines.append(f"  {p.name}  —  DOB: {dob_str}")
    return "\n".join(lines)


def format_gender_anomaly_report(anomalies: list[Person]) -> str:
    if not anomalies:
        return "No gender anomalies found — all gender values are present and valid."

    lines = [
        f"Gender anomalies found: {len(anomalies)}",
        "(missing or not M/F — excluded from sorting)",
        "",
    ]
    for p in anomalies:
        dob_str = p.dob.strftime("%d %b %Y") if p.dob else "(unknown DOB)"
        lines.append(f"  {p.name}  —  DOB: {dob_str}  —  Gender: (missing)")
    return "\n".join(lines)
