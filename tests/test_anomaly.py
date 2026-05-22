"""Tests for anomaly detection."""

from datetime import date

from groupsorter.anomaly import find_anomalies
from groupsorter.domain import Person


def make_person(name: str, dob: date | None) -> Person:
    return Person(name=name, dob=dob, raw_dob=str(dob) if dob else "")


START = date(2011, 7, 1)
END = date(2013, 6, 30)


class TestFindAnomalies:
    def test_no_anomalies(self):
        people = [
            make_person("Alice", date(2012, 1, 15)),
            make_person("Bob", date(2011, 7, 1)),   # on start boundary
            make_person("Carol", date(2013, 6, 30)), # on end boundary
        ]
        assert find_anomalies(people, START, END) == []

    def test_dob_before_range(self):
        p = make_person("OldPerson", date(2010, 6, 30))
        assert find_anomalies([p], START, END) == [p]

    def test_dob_after_range(self):
        p = make_person("YoungPerson", date(2013, 7, 1))
        assert find_anomalies([p], START, END) == [p]

    def test_missing_dob(self):
        p = make_person("NoDOB", None)
        assert find_anomalies([p], START, END) == [p]

    def test_mixed_list(self):
        valid = make_person("Valid", date(2012, 6, 1))
        anomaly = make_person("Anomaly", date(2014, 1, 1))
        no_dob = make_person("NoDOB", None)
        result = find_anomalies([valid, anomaly, no_dob], START, END)
        assert anomaly in result
        assert no_dob in result
        assert valid not in result
