"""Core domain entities."""

from dataclasses import dataclass
from datetime import date


@dataclass
class Person:
    name: str
    dob: date | None      # None if the DOB cell was blank or unparseable
    raw_dob: str = ""     # original cell value, for display when dob is None
    gender: str | None = None  # "M", "F", or None (not loaded / blank / invalid)
    raw_gender: str = ""  # original cell value, for display when gender is None
