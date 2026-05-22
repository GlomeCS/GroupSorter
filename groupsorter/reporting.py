"""Text report formatting for groups, anomalies, and gender anomalies."""

from datetime import date

from .domain import Person


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
        gender_str = f"(unrecognised: {p.raw_gender!r})" if p.raw_gender else "(missing)"
        lines.append(f"  {p.name}  —  DOB: {dob_str}  —  Gender: {gender_str}")
    return "\n".join(lines)


def format_groups_report(
    groups: list[list[Person]],
    mode: str,
    fell_back: bool = False,
    gender_mode: str | None = None,
) -> str:
    if mode == "mixed":
        age_label = "Mixed (age ranges distributed)"
    elif fell_back:
        age_label = "Isolated → fell back to Mixed (more sub-ranges than groups)"
    else:
        age_label = "Isolated (one age range per group)"

    lines = [f"Age sort mode: {age_label}"]

    if gender_mode == "mixed":
        lines.append("Gender sort mode: Mixed (gender spread across groups)")
    elif gender_mode == "isolated":
        lines.append("Gender sort mode: Isolated (one gender per group)")

    lines += [f"Groups: {len(groups)}", ""]

    has_gender = any(p.gender is not None for group in groups for p in group)

    for i, group in enumerate(groups, 1):
        lines.append(f"── Group {i} ({len(group)} {'person' if len(group) == 1 else 'people'}) ──")
        if group:
            if has_gender:
                m_count = sum(1 for p in group if p.gender == "M")
                f_count = sum(1 for p in group if p.gender == "F")
                lines.append(f"  [{m_count}M / {f_count}F]")
            for person in group:
                dob_str = person.dob.strftime("%d %b %Y") if person.dob else "unknown DOB"
                gender_str = f" [{person.gender}]" if person.gender else ""
                lines.append(f"  {person.name}  ({dob_str}){gender_str}")
        else:
            lines.append("  (empty)")
        lines.append("")
    return "\n".join(lines)


def format_excluded_report(
    dob_anomalies: list[Person],
    gender_anomalies: list[Person],
) -> str:
    lines: list[str] = []
    if dob_anomalies:
        count = len(dob_anomalies)
        label = "anomaly" if count == 1 else "anomalies"
        lines.append(f"\n── {count} DOB {label} excluded ──")
        for p in dob_anomalies:
            dob_str = p.dob.strftime("%d %b %Y") if p.dob else f"(unreadable: {p.raw_dob})"
            lines.append(f"  {p.name}  —  {dob_str}")
    if gender_anomalies:
        count = len(gender_anomalies)
        label = "anomaly" if count == 1 else "anomalies"
        lines.append(f"\n── {count} gender {label} excluded ──")
        for p in gender_anomalies:
            dob_str = p.dob.strftime("%d %b %Y") if p.dob else "(unknown DOB)"
            gender_str = f"(unrecognised: {p.raw_gender!r})" if p.raw_gender else "(missing)"
            lines.append(f"  {p.name}  —  DOB: {dob_str}  —  Gender: {gender_str}")
    return "\n".join(lines)
