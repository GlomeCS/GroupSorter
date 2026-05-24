"""GroupSorter tkinter GUI."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from openpyxl import Workbook

from .anomaly import find_anomalies, find_gender_anomalies
from .date_utils import AgeGroup, sub_ranges, suggested_age_groups
from .domain import Person
from .excel_io import (
    column_headers,
    export_results,
    is_password_protected,
    open_workbook,
    read_people,
    sheet_names,
)
from .reporting import (
    format_anomaly_report,
    format_excluded_report,
    format_gender_anomaly_report,
    format_groups_report,
)
from .sorter import run_sort

_GENDER_NONE = "(none — no gender sorting)"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("GroupSorter")
        self.resizable(True, True)
        self.minsize(640, 560)

        # State
        self._workbook: Workbook | None = None
        self._people: list[Person] = []
        self._last_groups: list[list[Person]] = []
        self._last_anomalies: list[Person] = []
        self._last_gender_anomalies: list[Person] = []
        self._last_start: date | None = None
        self._last_end: date | None = None
        self._custom_mode = False

        self._age_groups: list[AgeGroup] = suggested_age_groups()

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # ── File section ──────────────────────────────────────────────
        file_frame = ttk.LabelFrame(self, text="1. Load Excel File")
        file_frame.pack(fill="x", **pad)

        self._file_var = tk.StringVar(value="No file loaded")
        ttk.Label(file_frame, textvariable=self._file_var, anchor="w").pack(
            side="left", fill="x", expand=True, padx=8, pady=6
        )
        ttk.Button(file_frame, text="Browse…", command=self._browse_file).pack(
            side="right", padx=8, pady=6
        )

        # ── Sheet & columns ──────────────────────────────────────────
        sc_frame = ttk.LabelFrame(self, text="2. Select Sheet & Columns")
        sc_frame.pack(fill="x", **pad)

        ttk.Label(sc_frame, text="Sheet:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self._sheet_var = tk.StringVar()
        self._sheet_cb = ttk.Combobox(
            sc_frame, textvariable=self._sheet_var, state="disabled", width=28
        )
        self._sheet_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self._sheet_cb.bind("<<ComboboxSelected>>", self._on_sheet_selected)

        ttk.Label(sc_frame, text="Name column:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._name_col_var = tk.StringVar()
        self._name_col_cb = ttk.Combobox(
            sc_frame, textvariable=self._name_col_var, state="disabled", width=28
        )
        self._name_col_cb.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(sc_frame, text="Date of Birth column:").grid(
            row=2, column=0, sticky="w", padx=8, pady=4
        )
        self._dob_col_var = tk.StringVar()
        self._dob_col_cb = ttk.Combobox(
            sc_frame, textvariable=self._dob_col_var, state="disabled", width=28
        )
        self._dob_col_cb.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(sc_frame, text="Gender column (optional):").grid(
            row=3, column=0, sticky="w", padx=8, pady=4
        )
        self._gender_col_var = tk.StringVar(value=_GENDER_NONE)
        self._gender_col_cb = ttk.Combobox(
            sc_frame, textvariable=self._gender_col_var, state="disabled", width=28
        )
        self._gender_col_cb.grid(row=3, column=1, sticky="w", padx=4, pady=4)
        self._gender_col_cb.bind("<<ComboboxSelected>>", self._on_gender_col_changed)

        ttk.Button(sc_frame, text="Load People", command=self._load_people).grid(
            row=4, column=0, columnspan=2, pady=6
        )

        # ── Age group ────────────────────────────────────────────────
        ag_frame = ttk.LabelFrame(self, text="3. Age Group / Date Range")
        ag_frame.pack(fill="x", **pad)

        self._age_group_var = tk.StringVar()
        ag_labels = [str(g) for g in self._age_groups] + ["Custom…"]
        self._age_group_cb = ttk.Combobox(
            ag_frame, textvariable=self._age_group_var, values=ag_labels,
            state="readonly", width=60
        )
        self._age_group_cb.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=6)
        self._age_group_cb.bind("<<ComboboxSelected>>", self._on_age_group_selected)
        self._age_group_cb.current(0)

        # Custom date entry (hidden until "Custom…" selected)
        self._custom_frame = ttk.Frame(ag_frame)
        ttk.Label(self._custom_frame, text="Start date (YYYY-MM-DD):").grid(row=0, column=0, padx=8)
        self._custom_start_var = tk.StringVar()
        ttk.Entry(self._custom_frame, textvariable=self._custom_start_var, width=14).grid(
            row=0, column=1
        )
        ttk.Label(self._custom_frame, text="End date (YYYY-MM-DD):").grid(row=0, column=2, padx=8)
        self._custom_end_var = tk.StringVar()
        ttk.Entry(self._custom_frame, textvariable=self._custom_end_var, width=14).grid(
            row=0, column=3
        )

        self._split_hint_var = tk.StringVar()
        self._split_hint_lbl = ttk.Label(
            ag_frame, textvariable=self._split_hint_var, foreground="#555"
        )
        self._split_hint_lbl.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=2)
        self._update_split_hint()

        # ── Sort settings ────────────────────────────────────────────
        sort_frame = ttk.LabelFrame(self, text="4. Sort Settings")
        sort_frame.pack(fill="x", **pad)

        ttk.Label(sort_frame, text="Number of groups:").grid(
            row=0, column=0, sticky="w", padx=8, pady=4
        )
        self._num_groups_var = tk.IntVar(value=4)
        self._num_groups_var.trace_add("write", lambda *_: self._invalidate())
        ttk.Spinbox(sort_frame, from_=1, to=100, textvariable=self._num_groups_var, width=6).grid(
            row=0, column=1, sticky="w", padx=4
        )

        ttk.Label(sort_frame, text="Age mode:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._mode_var = tk.StringVar(value="mixed")
        ttk.Radiobutton(
            sort_frame, text="Mixed (each group gets a spread of all age sub-ranges)",
            variable=self._mode_var, value="mixed", command=self._invalidate,
        ).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Radiobutton(
            sort_frame, text="Isolated (each group contains only one age sub-range)",
            variable=self._mode_var, value="isolated", command=self._invalidate,
        ).grid(row=2, column=1, sticky="w", padx=4)

        # Gender mode (hidden until a gender column is selected)
        self._gender_sort_frame = ttk.Frame(sort_frame)
        ttk.Label(self._gender_sort_frame, text="Gender mode:").grid(
            row=0, column=0, sticky="w", padx=8, pady=4
        )
        self._gender_mode_var = tk.StringVar(value="mixed")
        ttk.Radiobutton(
            self._gender_sort_frame,
            text="Mixed (gender spread evenly across groups)",
            variable=self._gender_mode_var,
            value="mixed",
            command=self._invalidate,
        ).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Radiobutton(
            self._gender_sort_frame,
            text="Isolated (one gender per group)",
            variable=self._gender_mode_var,
            value="isolated",
            command=self._invalidate,
        ).grid(row=1, column=1, sticky="w", padx=4)

        # ── Action buttons ───────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        ttk.Button(btn_frame, text="Check Anomalies", command=self._check_anomalies).pack(
            side="left", padx=4, pady=4
        )
        ttk.Button(btn_frame, text="Sort Groups", command=self._sort_groups).pack(
            side="left", padx=4, pady=4
        )
        ttk.Button(btn_frame, text="Export to Excel…", command=self._export).pack(
            side="left", padx=4, pady=4
        )
        ttk.Button(btn_frame, text="Clear Results", command=self._clear_results).pack(
            side="right", padx=4, pady=4
        )

        # ── Results area ─────────────────────────────────────────────
        results_frame = ttk.LabelFrame(self, text="Results")
        results_frame.pack(fill="both", expand=True, **pad)

        self._results_text = tk.Text(
            results_frame, wrap="word", state="disabled",
            font=("Courier", 10), relief="flat", bg="#f8f8f8"
        )
        scrollbar = ttk.Scrollbar(results_frame, command=self._results_text.yview)
        self._results_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._results_text.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if not path:
            return

        password = None
        try:
            protected = is_password_protected(path)
        except OSError as exc:
            messagebox.showerror("Error opening file", str(exc))
            return
        if protected:
            password = simpledialog.askstring(
                "Password required",
                f"'{Path(path).name}' is password-protected.\nEnter the password:",
                show="*",
                parent=self,
            )
            if password is None:
                return  # user cancelled

        try:
            self._workbook = open_workbook(path, password=password)
        except ValueError as exc:
            messagebox.showerror("Error opening file", str(exc))
            return

        self._file_var.set(Path(path).name)
        names = sheet_names(self._workbook)
        self._sheet_cb.configure(values=names, state="readonly")
        self._sheet_var.set(names[0])
        self._on_sheet_selected()
        self._people = []
        self._invalidate()
        self._display("File loaded. Select a sheet and columns, then click 'Load People'.")

    def _on_sheet_selected(self, _event=None) -> None:
        if not self._workbook:
            return
        self._invalidate()
        ws = self._workbook[self._sheet_var.get()]
        headers = column_headers(ws)
        for cb in (self._name_col_cb, self._dob_col_cb):
            cb.configure(values=headers, state="readonly")
        self._name_col_var.set(
            _guess_column(headers, ("name", "full name", "player", "child"))
            or (headers[0] if headers else "")
        )
        self._dob_col_var.set(
            _guess_column(headers, ("dob", "date of birth", "birthday", "birth date"))
            or (headers[1] if len(headers) > 1 else "")
        )
        gender_options = [_GENDER_NONE] + headers
        self._gender_col_cb.configure(values=gender_options, state="readonly")
        detected = _guess_column(headers, ("gender", "sex", "m/f", "male/female"))
        self._gender_col_var.set(detected if detected else _GENDER_NONE)
        self._on_gender_col_changed()

    def _on_gender_col_changed(self, _event=None) -> None:
        if self._gender_col_var.get() == _GENDER_NONE:
            self._gender_sort_frame.grid_forget()
        else:
            self._gender_sort_frame.grid(
                row=3, column=0, columnspan=2, sticky="w", padx=4, pady=2
            )
        self._invalidate()

    def _load_people(self) -> None:
        if not self._workbook:
            messagebox.showwarning("No file", "Please load an Excel file first.")
            return
        name_col = self._name_col_var.get()
        dob_col = self._dob_col_var.get()
        if not name_col or not dob_col:
            messagebox.showwarning(
                "Columns required", "Please select both a name column and a DOB column."
            )
            return
        gender_col_raw = self._gender_col_var.get()
        gender_col = None if gender_col_raw == _GENDER_NONE else gender_col_raw
        try:
            ws = self._workbook[self._sheet_var.get()]
            self._people = read_people(ws, name_col, dob_col, gender_col=gender_col)
        except ValueError as exc:
            messagebox.showerror("Error reading sheet", str(exc))
            return
        self._invalidate()
        gender_note = f" (with gender from '{gender_col}')" if gender_col else ""
        self._display(
            f"Loaded {len(self._people)} people from '{self._sheet_var.get()}'{gender_note}."
        )

    def _on_age_group_selected(self, _event=None) -> None:
        selection = self._age_group_var.get()
        if selection == "Custom…":
            self._custom_mode = True
            self._custom_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        else:
            self._custom_mode = False
            self._custom_frame.grid_forget()
        self._invalidate()
        self._update_split_hint()

    def _update_split_hint(self) -> None:
        try:
            start, end = self._resolve_dates()
            bands = sub_ranges(start, end)
            if len(bands) == 1:
                hint = f"Sub-range: {_fmt_date(bands[0][0])} – {_fmt_date(bands[0][1])}"
            else:
                parts = [
                    f"  Range {i+1}: {_fmt_date(s)} – {_fmt_date(e)}"
                    for i, (s, e) in enumerate(bands)
                ]
                hint = f"Sub-ranges ({len(bands)}):\n" + "\n".join(parts)
        except Exception:
            hint = ""
        self._split_hint_var.set(hint)

    def _resolve_dates(self) -> tuple[date, date]:
        """Return (start_date, end_date) from current selection."""
        if self._custom_mode:
            start = date.fromisoformat(self._custom_start_var.get().strip())
            end = date.fromisoformat(self._custom_end_var.get().strip())
            if start > end:
                raise ValueError("Custom start date must be on or before end date.")
            return start, end
        selection = self._age_group_var.get()
        for group in self._age_groups:
            if str(group) == selection:
                return group.start_date, group.end_date
        raise ValueError("No age group selected.")

    def _check_anomalies(self) -> None:
        if not self._people:
            messagebox.showwarning("No data", "Please load people from an Excel file first.")
            return
        try:
            start, end = self._resolve_dates()
        except ValueError as exc:
            messagebox.showerror("Invalid date range", str(exc))
            return
        self._last_start = start
        self._last_end = end
        self._last_anomalies = find_anomalies(self._people, start, end)
        report = format_anomaly_report(self._last_anomalies, start, end)

        if self._gender_col_var.get() != _GENDER_NONE:
            dob_anomaly_ids = {id(p) for p in self._last_anomalies}
            dob_valid = [p for p in self._people if id(p) not in dob_anomaly_ids]
            self._last_gender_anomalies = find_gender_anomalies(dob_valid)
            report += "\n\n" + format_gender_anomaly_report(self._last_gender_anomalies)
        else:
            self._last_gender_anomalies = []

        self._display(report)

    def _sort_groups(self) -> None:
        if not self._people:
            messagebox.showwarning("No data", "Please load people from an Excel file first.")
            return
        try:
            start, end = self._resolve_dates()
        except ValueError as exc:
            messagebox.showerror("Invalid date range", str(exc))
            return
        try:
            num_groups = int(self._num_groups_var.get())
            if num_groups < 1:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid input", "Number of groups must be a positive integer.")
            return

        self._last_start = start
        self._last_end = end
        age_mode = self._mode_var.get()
        gender_mode: str | None = (
            self._gender_mode_var.get() if self._gender_col_var.get() != _GENDER_NONE else None
        )

        result = run_sort(self._people, start, end, num_groups, age_mode, gender_mode)
        self._last_groups = result.groups
        self._last_anomalies = result.dob_anomalies
        self._last_gender_anomalies = result.gender_anomalies

        if result.fell_back:
            if gender_mode == "isolated":
                messagebox.showwarning(
                    "Isolated mode fallback",
                    "Within one or both gender groups, there are more age sub-ranges than\n"
                    "allocated groups. Isolated age mode will fall back to mixed for those.",
                )
            else:
                messagebox.showwarning(
                    "Isolated mode fallback",
                    "There are more non-empty age sub-ranges than groups.\n"
                    "Isolated mode will fall back to mixed distribution.",
                )

        if gender_mode == "isolated" and result.gender_alloc is not None:
            male_g, female_g = result.gender_alloc
            if male_g == 0 and female_g == 0:
                messagebox.showwarning(
                    "Gender allocation warning",
                    "No participants remain after filtering. No groups will contain any people.",
                )
            elif male_g == 0 or female_g == 0:
                absent = "male" if male_g == 0 else "female"
                messagebox.showwarning(
                    "Gender allocation warning",
                    f"There are not enough {absent} participants for a dedicated group.\n"
                    f"All groups will be allocated to the other gender.",
                )

        self._display(format_groups_report(result.groups, age_mode, result.fell_back, gender_mode))
        excluded = format_excluded_report(result.dob_anomalies, result.gender_anomalies)
        if excluded:
            self._append(excluded)

    def _export(self) -> None:
        if not self._last_groups and not self._last_anomalies and not self._last_gender_anomalies:
            messagebox.showwarning(
                "Nothing to export", "Run 'Check Anomalies' or 'Sort Groups' first."
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save results as…",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_results(
                path,
                self._last_groups,
                self._last_anomalies,
                gender_anomalies=(
                    self._last_gender_anomalies
                    if self._gender_col_var.get() != _GENDER_NONE
                    else None
                ),
            )
            messagebox.showinfo("Exported", f"Results saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _clear_results(self) -> None:
        self._display("")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _invalidate(self) -> None:
        """Clear cached sort/anomaly results when inputs change."""
        self._last_groups = []
        self._last_anomalies = []
        self._last_gender_anomalies = []
        self._last_start = None
        self._last_end = None

    def _display(self, text: str) -> None:
        self._results_text.configure(state="normal")
        self._results_text.delete("1.0", "end")
        self._results_text.insert("end", text)
        self._results_text.configure(state="disabled")

    def _append(self, text: str) -> None:
        self._results_text.configure(state="normal")
        self._results_text.insert("end", text)
        self._results_text.configure(state="disabled")


def _guess_column(headers: list[str], keywords: tuple[str, ...]) -> str | None:
    lower = [h.lower() for h in headers]
    for kw in keywords:
        for i, h in enumerate(lower):
            if kw in h:
                return headers[i]
    return None


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")
