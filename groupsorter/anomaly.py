"""Anomaly detection: identify people whose DOB falls outside the expected range."""

from datetime import date

from .domain import Person
from .reporting import format_anomaly_report, format_gender_anomaly_report

__all__ = [
    "Person",
    "find_anomalies",
    "find_gender_anomalies",
    "format_anomaly_report",
    "format_gender_anomaly_report",
]


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
