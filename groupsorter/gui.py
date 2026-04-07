"""GroupSorter tkinter GUI."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .anomaly import find_anomalies, format_anomaly_report
from .date_utils import AgeGroup, sub_ranges, suggested_age_groups
from .excel_io import (
    column_headers,
    export_results,
    is_password_protected,
    load_workbook,
    read_people,
    sheet_names,
)
from .sorter import format_groups_report, sort_groups


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("GroupSorter")
        self.resizable(True, True)
        self.minsize(640, 560)

        # State
        self._workbook = None
        self._people: list = []
        self._last_groups: list = []
        self._last_anomalies: list = []
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
        self._sheet_cb = ttk.Combobox(sc_frame, textvariable=self._sheet_var, state="disabled", width=28)
        self._sheet_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self._sheet_cb.bind("<<ComboboxSelected>>", self._on_sheet_selected)

        ttk.Label(sc_frame, text="Name column:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._name_col_var = tk.StringVar()
        self._name_col_cb = ttk.Combobox(sc_frame, textvariable=self._name_col_var, state="disabled", width=28)
        self._name_col_cb.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(sc_frame, text="Date of Birth column:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self._dob_col_var = tk.StringVar()
        self._dob_col_cb = ttk.Combobox(sc_frame, textvariable=self._dob_col_var, state="disabled", width=28)
        self._dob_col_cb.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Button(sc_frame, text="Load People", command=self._load_people).grid(
            row=3, column=0, columnspan=2, pady=6
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
        ttk.Entry(self._custom_frame, textvariable=self._custom_start_var, width=14).grid(row=0, column=1)
        ttk.Label(self._custom_frame, text="End date (YYYY-MM-DD):").grid(row=0, column=2, padx=8)
        self._custom_end_var = tk.StringVar()
        ttk.Entry(self._custom_frame, textvariable=self._custom_end_var, width=14).grid(row=0, column=3)

        self._split_hint_var = tk.StringVar()
        self._split_hint_lbl = ttk.Label(ag_frame, textvariable=self._split_hint_var, foreground="#555")
        self._split_hint_lbl.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=2)
        self._update_split_hint()

        # ── Sort settings ────────────────────────────────────────────
        sort_frame = ttk.LabelFrame(self, text="4. Sort Settings")
        sort_frame.pack(fill="x", **pad)

        ttk.Label(sort_frame, text="Number of groups:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self._num_groups_var = tk.IntVar(value=4)
        ttk.Spinbox(sort_frame, from_=1, to=100, textvariable=self._num_groups_var, width=6).grid(
            row=0, column=1, sticky="w", padx=4
        )

        ttk.Label(sort_frame, text="Mode:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._mode_var = tk.StringVar(value="mixed")
        ttk.Radiobutton(
            sort_frame, text="Mixed (each group gets a spread of all age sub-ranges)",
            variable=self._mode_var, value="mixed"
        ).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Radiobutton(
            sort_frame, text="Isolated (each group contains only one age sub-range)",
            variable=self._mode_var, value="isolated"
        ).grid(row=2, column=1, sticky="w", padx=4)

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
        if is_password_protected(path):
            password = simpledialog.askstring(
                "Password required",
                f"'{Path(path).name}' is password-protected.\nEnter the password:",
                show="*",
                parent=self,
            )
            if password is None:
                return  # user cancelled

        try:
            self._workbook = load_workbook(path, password=password)
        except ValueError as exc:
            messagebox.showerror("Error opening file", str(exc))
            return

        self._file_var.set(Path(path).name)
        names = sheet_names(self._workbook)
        self._sheet_cb.configure(values=names, state="readonly")
        self._sheet_var.set(names[0])
        self._on_sheet_selected()
        self._people = []
        self._display("File loaded. Select a sheet and columns, then click 'Load People'.")

    def _on_sheet_selected(self, _event=None) -> None:
        if not self._workbook:
            return
        ws = self._workbook[self._sheet_var.get()]
        headers = column_headers(ws)
        for cb in (self._name_col_cb, self._dob_col_cb):
            cb.configure(values=headers, state="readonly")
        # Auto-select likely columns
        self._name_col_var.set(_guess_column(headers, ("name", "full name", "player", "child")) or (headers[0] if headers else ""))
        self._dob_col_var.set(_guess_column(headers, ("dob", "date of birth", "birthday", "birth date")) or (headers[1] if len(headers) > 1 else ""))

    def _load_people(self) -> None:
        if not self._workbook:
            messagebox.showwarning("No file", "Please load an Excel file first.")
            return
        name_col = self._name_col_var.get()
        dob_col = self._dob_col_var.get()
        if not name_col or not dob_col:
            messagebox.showwarning("Columns required", "Please select both a name column and a DOB column.")
            return
        try:
            ws = self._workbook[self._sheet_var.get()]
            self._people = read_people(ws, name_col, dob_col)
        except ValueError as exc:
            messagebox.showerror("Error reading sheet", str(exc))
            return
        self._display(f"Loaded {len(self._people)} people from '{self._sheet_var.get()}'.")

    def _on_age_group_selected(self, _event=None) -> None:
        selection = self._age_group_var.get()
        if selection == "Custom…":
            self._custom_mode = True
            self._custom_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        else:
            self._custom_mode = False
            self._custom_frame.grid_forget()
        self._update_split_hint()

    def _update_split_hint(self) -> None:
        try:
            start, end = self._resolve_dates()
            bands = sub_ranges(start, end)
            if len(bands) == 1:
                hint = f"Sub-range: {_fmt_date(bands[0][0])} – {_fmt_date(bands[0][1])}"
            else:
                parts = [f"  Range {i+1}: {_fmt_date(s)} – {_fmt_date(e)}" for i, (s, e) in enumerate(bands)]
                hint = f"Sub-ranges ({len(bands)}):\n" + "\n".join(parts)
        except Exception:
            hint = ""
        self._split_hint_var.set(hint)

    def _resolve_dates(self) -> tuple[date, date]:
        """Return (start_date, end_date) from current selection."""
        if self._custom_mode:
            start = date.fromisoformat(self._custom_start_var.get().strip())
            end = date.fromisoformat(self._custom_end_var.get().strip())
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
        except Exception as exc:
            messagebox.showerror("Invalid date range", str(exc))
            return
        self._last_start = start
        self._last_end = end
        self._last_anomalies = find_anomalies(self._people, start, end)
        self._display(format_anomaly_report(self._last_anomalies, start, end))

    def _sort_groups(self) -> None:
        if not self._people:
            messagebox.showwarning("No data", "Please load people from an Excel file first.")
            return
        try:
            start, end = self._resolve_dates()
        except Exception as exc:
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
        mode = self._mode_var.get()

        # Exclude anomalies before sorting
        anomalies = find_anomalies(self._people, start, end)
        valid = [p for p in self._people if p not in anomalies]

        self._last_groups = sort_groups(valid, start, end, num_groups, mode)
        self._last_anomalies = anomalies
        self._display(format_groups_report(self._last_groups, mode))
        if anomalies:
            self._append(f"\n── {len(anomalies)} anomal{'y' if len(anomalies)==1 else 'ies'} excluded from sorting ──\n")
            for p in anomalies:
                dob_str = p.dob.strftime("%d %b %Y") if p.dob else f"(unreadable: {p.raw_dob})"
                self._append(f"  {p.name}  —  {dob_str}\n")

    def _export(self) -> None:
        if not self._last_groups and not self._last_anomalies:
            messagebox.showwarning("Nothing to export", "Run 'Check Anomalies' or 'Sort Groups' first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save results as…",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_results(path, self._last_groups, self._last_anomalies)
            messagebox.showinfo("Exported", f"Results saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _clear_results(self) -> None:
        self._display("")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
