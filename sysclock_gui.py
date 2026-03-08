#!/usr/bin/env python3
"""
sysclock_gui.py  —  System Clock Manager
Modifica l'orario di sistema, sincronizza NTP, gestisce timezone.
Richiede privilegi root/admin per le operazioni di sistema.

Copyright (C) 2026  Alessandro Orlando
License: GNU General Public License v3.0 (GPL-3.0)
         https://www.gnu.org/licenses/gpl-3.0.html

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Dipendenze: solo stdlib Python (tkinter, subprocess, threading, ...)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import datetime
import time
import platform
import os
import sys
import collections

# ─────────────────────────────────────────────────────────────── Palette ──
C = {
    "bg":        "#0b0e13",
    "panel":     "#10141c",
    "panel2":    "#161c28",
    "border":    "#1e2a3a",
    "accent":    "#38bdf8",      # sky blue
    "accent2":   "#f472b6",      # pink
    "accent3":   "#34d399",      # green
    "warn":      "#fb923c",      # orange
    "err":       "#f87171",      # red
    "txt":       "#e2e8f0",
    "txt_dim":   "#7a9aba",
    "txt_med":   "#a8c0d6",
    "black":     "#000000",
}

OS = platform.system()   # "Linux", "Darwin", "Windows"

# ─────────────────────────────────────────────── System-level functions ──

def _is_admin() -> bool:
    """Check if the process has administrator / root privileges."""
    if OS == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def _run(cmd, use_sudo=False, shell=False):
    """Run a shell command, optionally via sudo. Returns (ok, stdout, stderr)."""
    if use_sudo and OS != "Windows" and not _is_admin():
        cmd = ["sudo", "-n"] + cmd   # non-interactive sudo
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=10, shell=shell)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError as e:
        return False, "", str(e)
    except subprocess.TimeoutExpired:
        return False, "", "timeout"


def set_system_time(dt: datetime.datetime) -> tuple[bool, str]:
    """Set the system clock to dt (local time)."""
    if OS == "Linux":
        ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        ok, out, err = _run(["date", "-s", ts], use_sudo=True)
        if not ok:
            ok, out, err = _run(["timedatectl", "set-time", ts], use_sudo=True)
        return ok, err if not ok else "OK"
    elif OS == "Darwin":
        ts = dt.strftime("%m%d%H%M%Y.%S")
        ok, out, err = _run(["date", ts], use_sudo=True)
        return ok, err if not ok else "OK"
    elif OS == "Windows":
        # Use SetSystemTime via ctypes for precise millisecond control
        try:
            import ctypes, ctypes.wintypes
            class SYSTEMTIME(ctypes.Structure):
                _fields_ = [
                    ("wYear",         ctypes.wintypes.WORD),
                    ("wMonth",        ctypes.wintypes.WORD),
                    ("wDayOfWeek",    ctypes.wintypes.WORD),
                    ("wDay",          ctypes.wintypes.WORD),
                    ("wHour",         ctypes.wintypes.WORD),
                    ("wMinute",       ctypes.wintypes.WORD),
                    ("wSecond",       ctypes.wintypes.WORD),
                    ("wMilliseconds", ctypes.wintypes.WORD),
                ]
            st = SYSTEMTIME(
                dt.year, dt.month, 0, dt.day,
                dt.hour, dt.minute, dt.second, dt.microsecond // 1000
            )
            ok = bool(ctypes.windll.kernel32.SetLocalTime(ctypes.byref(st)))
            return ok, "OK" if ok else "SetLocalTime failed (run as Administrator)"
        except Exception as e:
            return False, str(e)
    return False, "Unsupported OS"


def step_system_time(ms: int) -> tuple[bool, str]:
    """Advance (or retard) system clock by ms milliseconds."""
    now = datetime.datetime.now()
    target = now + datetime.timedelta(milliseconds=ms)
    return set_system_time(target)


def get_timezones() -> list[str]:
    """Return list of available timezone names."""
    if OS == "Windows":
        # tzutil /l lists all available Windows timezone names
        ok, out, _ = _run(["tzutil", "/l"])
        if ok and out:
            # Output alternates: display name / timezone ID lines
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            # Timezone IDs are the lines NOT indented (every other line)
            ids = [lines[i] for i in range(1, len(lines), 2)]
            if ids:
                return sorted(ids)
    if OS == "Linux":
        ok, out, _ = _run(["timedatectl", "list-timezones"])
        if ok and out:
            return out.splitlines()
    try:
        import zoneinfo
        return sorted(zoneinfo.available_timezones())
    except ImportError:
        pass
    return ["UTC", "Europe/Rome", "America/New_York", "America/Los_Angeles",
            "Asia/Tokyo", "Asia/Shanghai", "Europe/London", "Europe/Berlin"]


def set_timezone(tz: str) -> tuple[bool, str]:
    if OS == "Windows":
        # tzutil /s "Timezone ID"
        ok, _, err = _run(["tzutil", "/s", tz])
        return ok, err if not ok else "OK"
    elif OS == "Linux":
        ok, _, err = _run(["timedatectl", "set-timezone", tz], use_sudo=True)
        return ok, err if not ok else "OK"
    elif OS == "Darwin":
        ok, _, err = _run(["systemsetup", "-settimezone", tz], use_sudo=True)
        return ok, err if not ok else "OK"
    return False, "Unsupported OS"


def ntp_sync(enable: bool) -> tuple[bool, str]:
    if OS == "Windows":
        if enable:
            # Start Windows Time service and force sync
            _run(["sc", "config", "w32time", "start=auto"])
            _run(["net", "start", "w32time"])
            ok, _, err = _run(["w32tm", "/resync", "/force"])
        else:
            ok, _, err = _run(["net", "stop", "w32time"])
        return ok, err if not ok else "OK"
    elif OS == "Linux":
        val = "true" if enable else "false"
        ok, _, err = _run(["timedatectl", "set-ntp", val], use_sudo=True)
        return ok, err if not ok else "OK"
    elif OS == "Darwin":
        svc = "on" if enable else "off"
        ok, _, err = _run(["systemsetup", "-setusingnetworktime", svc], use_sudo=True)
        return ok, err if not ok else "OK"
    return False, "Unsupported OS"


def get_ntp_status() -> bool:
    if OS == "Windows":
        ok, out, _ = _run(["sc", "query", "w32time"])
        return ok and "RUNNING" in out.upper()
    elif OS == "Linux":
        ok, out, _ = _run(["timedatectl", "show", "--property=NTP", "--value"])
        return out.strip().lower() == "yes"
    elif OS == "Darwin":
        ok, out, _ = _run(["systemsetup", "-getusingnetworktime"])
        return "on" in out.lower()
    return False

# ──────────────────────────────────────────────────────── Sparkline util ──

class RingBuffer:
    def __init__(self, size):
        self._buf = collections.deque(maxlen=size)

    def push(self, v):
        self._buf.append(v)

    def values(self):
        return list(self._buf)


# ─────────────────────────────────────────── Styled widget helpers ──────

def _label(parent, text="", fg=None, font=None, bg=None, **kw):
    return tk.Label(parent, text=text,
                    fg=fg or C["txt"], bg=bg or C["bg"],
                    font=font or ("Courier New", 10), **kw)


def _frame(parent, bg=None, **kw):
    return tk.Frame(parent, bg=bg or C["bg"], **kw)


def _panel(parent, **kw):
    f = tk.Frame(parent, bg=C["panel"],
                 highlightbackground=C["border"], highlightthickness=1, **kw)
    return f


def _btn(parent, text, cmd, color=None, **kw):
    color = color or C["accent"]
    b = tk.Button(parent, text=text, command=cmd,
                  bg=C["panel2"], fg=color,
                  activebackground=color, activeforeground=C["bg"],
                  relief="flat", bd=0, cursor="hand2",
                  font=("Courier New", 10, "bold"),
                  padx=12, pady=6, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=color, fg=C["bg"]))
    b.bind("<Leave>", lambda e: b.config(bg=C["panel2"], fg=color))
    return b


def _divider(parent, color=None):
    tk.Frame(parent, bg=color or C["border"], height=1).pack(fill="x", pady=6)

# ──────────────────────────────────────────────────── Main Application ──

class SysClockApp(tk.Tk):

    STEP_PRESETS = [10, 50, 100, 500, 1000, 5000, 30000, 60000]

    def __init__(self):
        super().__init__()
        self.title("System Clock Manager")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(860, 600)

        self._step_ms   = tk.IntVar(value=1000)
        self._total_ms  = 0
        self._log       = []
        self._ntp_var   = tk.BooleanVar(value=False)
        self._tz_var    = tk.StringVar(value="")
        self._history   = RingBuffer(120)   # seconds of offset history
        self._running   = True

        self._build_ui()
        self._tick()       # live clock updater

    # ─────────────────────────────────────────────── UI construction ───

    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────
        top = _frame(self, bg=C["panel"])
        top.pack(fill="x", padx=0, pady=0)

        tk.Frame(top, bg=C["accent"], width=4).pack(side="left", fill="y")

        _label(top, "SYSCLOCK", fg=C["accent"],
               font=("Courier New", 18, "bold"), bg=C["panel"],
               padx=14, pady=10).pack(side="left")

        subtitle_block = _frame(top, bg=C["panel"])
        subtitle_block.pack(side="left", pady=10)
        _label(subtitle_block, "system time manager", fg=C["txt_dim"],
               font=("Courier New", 9), bg=C["panel"], anchor="w").pack(fill="x")
        _label(subtitle_block, "\u00a9 2026 Alessandro Orlando  \u2022  GNU GPL v3.0",
               fg=C["txt_dim"], font=("Courier New", 7), bg=C["panel"], anchor="w").pack(fill="x")

        self._os_lbl = _label(top, f"● {OS}", fg=C["accent3"],
                              font=("Courier New", 9, "bold"), bg=C["panel"],
                              padx=14)
        self._os_lbl.pack(side="right", pady=14)

        # root / admin check
        is_root = _is_admin()
        priv_color = C["accent3"] if is_root else C["warn"]
        priv_text  = "ADMIN" if (is_root and OS == "Windows") else ("ROOT" if is_root else "NO ROOT")
        _label(top, priv_text, fg=priv_color,
               font=("Courier New", 9, "bold"), bg=C["panel"],
               padx=8).pack(side="right", pady=14)

        # ── main layout: left column + right column ───────────────────────
        body = _frame(self)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        left  = _frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 7))
        right = _frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(7, 0))

        self._build_clock_panel(left)
        self._build_step_panel(left)
        self._build_manual_panel(left)
        self._build_ntp_panel(right)
        self._build_tz_panel(right)
        self._build_chart_panel(right)
        self._build_log_panel(right)

    # ── Clock display ─────────────────────────────────────────────────────

    def _build_clock_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "SYSTEM TIME", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x")

        self._clock_var = tk.StringVar(value="──:──:──")
        tk.Label(inner, textvariable=self._clock_var,
                 fg=C["accent"], bg=C["panel"],
                 font=("Courier New", 42, "bold"),
                 anchor="w").pack(fill="x")

        self._date_var = tk.StringVar(value="────────────")
        tk.Label(inner, textvariable=self._date_var,
                 fg=C["txt_med"], bg=C["panel"],
                 font=("Courier New", 12),
                 anchor="w").pack(fill="x")

        _divider(inner)

        row = _frame(inner, bg=C["panel"])
        row.pack(fill="x")

        self._offset_var = tk.StringVar(value="offset  +0 ms")
        _label(row, textvariable=self._offset_var,
               fg=C["txt_dim"], font=("Courier New", 10), bg=C["panel"],
               anchor="w").pack(side="left")

        self._tz_display = tk.StringVar(value="")
        _label(row, textvariable=self._tz_display,
               fg=C["txt_dim"], font=("Courier New", 10), bg=C["panel"],
               anchor="e").pack(side="right")

    # ── Step controls ──────────────────────────────────────────────────────

    def _build_step_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "STEP CONTROLS", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(0, 8))

        # preset buttons
        preset_row = _frame(inner, bg=C["panel"])
        preset_row.pack(fill="x", pady=(0, 8))

        _label(preset_row, "preset:", fg=C["txt_dim"],
               font=("Courier New", 9), bg=C["panel"]).pack(side="left", padx=(0, 6))

        for ms in self.STEP_PRESETS:
            lbl = f"{ms}ms" if ms < 1000 else f"{ms//1000}s"
            b = tk.Button(preset_row, text=lbl,
                          command=lambda v=ms: self._set_step(v),
                          bg=C["panel2"], fg=C["txt_med"],
                          activebackground=C["accent"], activeforeground=C["bg"],
                          relief="flat", bd=0, cursor="hand2",
                          font=("Courier New", 8), padx=7, pady=3)
            b.pack(side="left", padx=2)
            b.bind("<Enter>", lambda e, b=b: b.config(bg=C["accent"], fg=C["bg"]))
            b.bind("<Leave>", lambda e, b=b: b.config(bg=C["panel2"], fg=C["txt_med"]))

        # custom slider
        slider_row = _frame(inner, bg=C["panel"])
        slider_row.pack(fill="x", pady=(0, 10))

        _label(slider_row, "custom:", fg=C["txt_dim"],
               font=("Courier New", 9), bg=C["panel"]).pack(side="left", padx=(0, 6))

        self._step_slider = tk.Scale(
            slider_row, from_=10, to=60000,
            orient="horizontal", variable=self._step_ms,
            bg=C["panel"], fg=C["txt_med"], troughcolor=C["panel2"],
            highlightthickness=0, showvalue=False,
            sliderlength=14, width=6,
            command=lambda v: self._step_ms.set(int(float(v)))
        )
        self._step_slider.pack(side="left", fill="x", expand=True)

        self._step_lbl = _label(slider_row, fg=C["accent"],
                                font=("Courier New", 11, "bold"), bg=C["panel"],
                                width=8, anchor="e")
        self._step_lbl.pack(side="left")
        self._step_ms.trace_add("write", self._on_step_change)
        self._on_step_change()

        # back / forward buttons
        btn_row = _frame(inner, bg=C["panel"])
        btn_row.pack(fill="x")

        _btn(btn_row, "◀◀  BACK", self._step_back, color=C["accent2"],
             width=14).pack(side="left", padx=(0, 8))
        _btn(btn_row, "FORWARD  ▶▶", self._step_fwd, color=C["accent"],
             width=14).pack(side="left")

        _btn(btn_row, "RESET OFFSET", self._reset_offset, color=C["warn"],
             width=14).pack(side="right")

        # keybinding hint
        _label(inner, "  < , ► back    > . ► fwd    + ► step↑    - ► step↓    Q/Esc ► quit",
               fg=C["txt_dim"], font=("Courier New", 8), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(8, 0))

        # bind keys
        self.bind("<comma>",    lambda e: self._step_back())
        self.bind("<less>",     lambda e: self._step_back())
        self.bind("<period>",   lambda e: self._step_fwd())
        self.bind("<greater>",  lambda e: self._step_fwd())
        self.bind("<plus>",     lambda e: self._inc_step())
        self.bind("<equal>",    lambda e: self._inc_step())
        self.bind("<minus>",    lambda e: self._dec_step())
        self.bind("<underscore>", lambda e: self._dec_step())
        self.bind("q", lambda e: self.destroy())
        self.bind("Q", lambda e: self.destroy())
        self.bind("<Escape>",   lambda e: self.destroy())

    # ── Manual date/time setter ────────────────────────────────────────────

    def _build_manual_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "SET EXACT TIME", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(0, 8))

        row = _frame(inner, bg=C["panel"])
        row.pack(fill="x")

        entry_style = dict(
            bg=C["panel2"], fg=C["txt"], insertbackground=C["accent"],
            relief="flat", bd=0, font=("Courier New", 12),
            width=10, justify="center",
            highlightbackground=C["border"], highlightthickness=1,
        )

        now = datetime.datetime.now()

        _label(row, "Date:", fg=C["txt_dim"], bg=C["panel"],
               font=("Courier New", 9)).pack(side="left")
        self._date_entry = tk.Entry(row, **entry_style)
        self._date_entry.insert(0, now.strftime("%Y-%m-%d"))
        self._date_entry.pack(side="left", padx=(4, 12))

        _label(row, "Time:", fg=C["txt_dim"], bg=C["panel"],
               font=("Courier New", 9)).pack(side="left")
        self._time_entry = tk.Entry(row, **entry_style)
        self._time_entry.insert(0, now.strftime("%H:%M:%S"))
        self._time_entry.pack(side="left", padx=(4, 12))

        _btn(row, "SET", self._set_exact_time, color=C["accent3"]).pack(side="left")
        _btn(row, "NOW", self._fill_now, color=C["txt_dim"]).pack(side="left", padx=(6, 0))

    # ── NTP ───────────────────────────────────────────────────────────────

    def _build_ntp_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "NTP SYNCHRONIZATION", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(0, 8))

        row = _frame(inner, bg=C["panel"])
        row.pack(fill="x")

        self._ntp_status_lbl = _label(row, "●  checking...", fg=C["txt_dim"],
                                      font=("Courier New", 10), bg=C["panel"])
        self._ntp_status_lbl.pack(side="left")

        _btn(row, "ENABLE NTP",  lambda: self._set_ntp(True),
             color=C["accent3"]).pack(side="right", padx=(6, 0))
        _btn(row, "DISABLE NTP", lambda: self._set_ntp(False),
             color=C["err"]).pack(side="right")

        # refresh NTP status in background
        threading.Thread(target=self._refresh_ntp_status, daemon=True).start()

    # ── Timezone ──────────────────────────────────────────────────────────

    def _build_tz_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "TIMEZONE", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(0, 8))

        row = _frame(inner, bg=C["panel"])
        row.pack(fill="x")

        self._tz_combo = ttk.Combobox(row, textvariable=self._tz_var,
                                      font=("Courier New", 10), width=28)
        self._tz_combo.pack(side="left", padx=(0, 8))

        _btn(row, "APPLY", self._apply_tz, color=C["accent"]).pack(side="left")

        # load timezones async
        threading.Thread(target=self._load_tz, daemon=True).start()

        # current tz
        try:
            cur = datetime.datetime.now().astimezone().tzname()
        except Exception:
            cur = "?"
        _label(inner, f"current: {cur}", fg=C["txt_dim"],
               font=("Courier New", 9), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(6, 0))

    # ── Sparkline chart ───────────────────────────────────────────────────

    def _build_chart_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 10))

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="x", padx=16, pady=12)

        _label(inner, "OFFSET HISTORY  (last 2 min)", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(fill="x", pady=(0, 6))

        self._chart = tk.Canvas(inner, bg=C["panel2"], height=80,
                                highlightthickness=0)
        self._chart.pack(fill="x")

        self._chart_labels = _frame(inner, bg=C["panel"])
        self._chart_labels.pack(fill="x", pady=(3, 0))
        self._chart_min_lbl = _label(self._chart_labels, "min: 0ms",
                                     fg=C["txt_dim"], font=("Courier New", 8),
                                     bg=C["panel"], anchor="w")
        self._chart_min_lbl.pack(side="left")
        self._chart_max_lbl = _label(self._chart_labels, "max: 0ms",
                                     fg=C["txt_dim"], font=("Courier New", 8),
                                     bg=C["panel"], anchor="e")
        self._chart_max_lbl.pack(side="right")

    # ── Log ───────────────────────────────────────────────────────────────

    def _build_log_panel(self, parent):
        p = _panel(parent)
        p.pack(fill="both", expand=True)

        inner = _frame(p, bg=C["panel"])
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        hdr = _frame(inner, bg=C["panel"])
        hdr.pack(fill="x", pady=(0, 4))

        _label(hdr, "OPERATIONS LOG", fg=C["txt_dim"],
               font=("Courier New", 8, "bold"), bg=C["panel"],
               anchor="w").pack(side="left")
        _btn(hdr, "CLEAR", self._clear_log, color=C["txt_dim"]).pack(side="right")

        self._log_text = tk.Text(
            inner, bg=C["panel2"], fg=C["txt_med"],
            font=("Courier New", 9), relief="flat", bd=0,
            state="disabled", height=8, wrap="word",
            highlightthickness=0,
            insertbackground=C["accent"],
        )
        self._log_text.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(inner, command=self._log_text.yview)
        self._log_text["yscrollcommand"] = sb.set

        # tags for colored output
        self._log_text.tag_config("ok",   foreground=C["accent3"])
        self._log_text.tag_config("err",  foreground=C["err"])
        self._log_text.tag_config("info", foreground=C["accent"])
        self._log_text.tag_config("ts",   foreground=C["txt_dim"])

    # ──────────────────────────────────────────── Action implementations ──

    def _step_back(self):
        self._do_step(-self._step_ms.get())

    def _step_fwd(self):
        self._do_step(self._step_ms.get())

    def _do_step(self, ms: int):
        def _work():
            ok, msg = step_system_time(ms)
            sign = "+" if ms > 0 else ""
            if ok:
                self._total_ms += ms
                self._history.push(self._total_ms)
                self._log_entry(f"Step {sign}{ms} ms  →  total {self._total_ms:+d} ms", "ok")
            else:
                self._log_entry(f"Step FAILED: {msg}", "err")
            self._update_offset_display()
        threading.Thread(target=_work, daemon=True).start()

    def _set_exact_time(self):
        date_str = self._date_entry.get().strip()
        time_str = self._time_entry.get().strip()
        try:
            dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showerror("Format Error",
                                 "Use YYYY-MM-DD for date and HH:MM:SS for time.")
            return

        def _work():
            ok, msg = set_system_time(dt)
            if ok:
                self._log_entry(f"Time set to {dt.strftime('%Y-%m-%d %H:%M:%S')}", "ok")
            else:
                self._log_entry(f"Set time FAILED: {msg}", "err")
        threading.Thread(target=_work, daemon=True).start()

    def _fill_now(self):
        now = datetime.datetime.now()
        self._date_entry.delete(0, "end")
        self._date_entry.insert(0, now.strftime("%Y-%m-%d"))
        self._time_entry.delete(0, "end")
        self._time_entry.insert(0, now.strftime("%H:%M:%S"))

    def _set_ntp(self, enable: bool):
        def _work():
            ok, msg = ntp_sync(enable)
            state = "enabled" if enable else "disabled"
            if ok:
                self._log_entry(f"NTP {state}", "ok")
                self._refresh_ntp_status()
            else:
                self._log_entry(f"NTP {state} FAILED: {msg}", "err")
        threading.Thread(target=_work, daemon=True).start()

    def _refresh_ntp_status(self):
        active = get_ntp_status()
        color = C["accent3"] if active else C["err"]
        text  = "●  NTP active" if active else "●  NTP inactive"
        self.after(0, lambda: self._ntp_status_lbl.config(text=text, fg=color))

    def _apply_tz(self):
        tz = self._tz_var.get().strip()
        if not tz:
            return
        def _work():
            ok, msg = set_timezone(tz)
            if ok:
                self._log_entry(f"Timezone set to {tz}", "ok")
            else:
                self._log_entry(f"TZ FAILED: {msg}", "err")
        threading.Thread(target=_work, daemon=True).start()

    def _load_tz(self):
        zones = get_timezones()
        self.after(0, lambda: self._tz_combo.config(values=zones))
        try:
            local_tz = datetime.datetime.now().astimezone().tzinfo
            name = str(local_tz)
            if name in zones:
                self.after(0, lambda: self._tz_var.set(name))
        except Exception:
            pass

    def _reset_offset(self):
        self._total_ms = 0
        self._history.push(0)
        self._log_entry("Offset counter reset to 0", "info")
        self._update_offset_display()

    def _inc_step(self):
        v = self._step_ms.get()
        presets = self.STEP_PRESETS
        nxt = next((p for p in presets if p > v), presets[-1])
        self._step_ms.set(nxt)

    def _dec_step(self):
        v = self._step_ms.get()
        presets = self.STEP_PRESETS
        prv = next((p for p in reversed(presets) if p < v), presets[0])
        self._step_ms.set(prv)

    def _set_step(self, v: int):
        self._step_ms.set(v)

    # ──────────────────────────────────────────────── UI update helpers ──

    def _on_step_change(self, *_):
        v = self._step_ms.get()
        if v >= 60000:
            txt = f"{v//60000}m"
        elif v >= 1000:
            txt = f"{v/1000:.1f}s"
        else:
            txt = f"{v}ms"
        self._step_lbl.config(text=txt)

    def _update_offset_display(self):
        sign = "+" if self._total_ms >= 0 else ""
        self._offset_var.set(f"offset  {sign}{self._total_ms} ms")
        self._redraw_chart()

    def _log_entry(self, msg: str, tag: str = "info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        def _insert():
            self._log_text.config(state="normal")
            self._log_text.insert("end", f"[{ts}] ", "ts")
            self._log_text.insert("end", msg + "\n", tag)
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        self.after(0, _insert)

    def _clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _redraw_chart(self):
        c = self._chart
        c.delete("all")
        W = c.winfo_width() or 400
        H = c.winfo_height() or 80

        vals = self._history.values()
        if not vals:
            return

        mn, mx = min(vals), max(vals)
        span = mx - mn if mx != mn else 1

        # grid lines
        for i in range(1, 4):
            y = int(H * i / 4)
            c.create_line(0, y, W, y, fill=C["border"], dash=(2, 4))

        # zero line
        zero_y = H - int((0 - mn) / span * H) if span else H // 2
        c.create_line(0, zero_y, W, zero_y, fill=C["txt_dim"], dash=(4, 4))

        # polyline
        n = len(vals)
        pts = []
        for i, v in enumerate(vals):
            x = int(W * i / max(n - 1, 1))
            y = H - int((v - mn) / span * (H - 4)) - 2
            pts.extend([x, y])

        if len(pts) >= 4:
            c.create_line(*pts, fill=C["accent"], width=2, smooth=True)
            # dot at last point
            lx, ly = pts[-2], pts[-1]
            c.create_oval(lx - 4, ly - 4, lx + 4, ly + 4,
                          fill=C["accent"], outline="")

        self._chart_min_lbl.config(text=f"min: {mn:+d}ms")
        self._chart_max_lbl.config(text=f"max: {mx:+d}ms")

    # ─────────────────────────────────────────────────────── Live tick ──

    def _tick(self):
        if not self._running:
            return
        now = datetime.datetime.now()
        self._clock_var.set(now.strftime("%H:%M:%S"))
        self._date_var.set(now.strftime("%A, %d %B %Y"))
        try:
            tz_name = now.astimezone().tzname()
            self._tz_display.set(tz_name)
        except Exception:
            pass

        self._history.push(self._total_ms)
        self._redraw_chart()

        self.after(1000, self._tick)

    def destroy(self):
        self._running = False
        super().destroy()


# ──────────────────────────────────────────────────────────────── main ──

if __name__ == "__main__":
    # Style ttk combobox to dark theme
    app = SysClockApp()

    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("TCombobox",
                    fieldbackground=C["panel2"],
                    background=C["panel2"],
                    foreground=C["txt"],
                    selectbackground=C["accent"],
                    selectforeground=C["bg"],
                    bordercolor=C["border"],
                    lightcolor=C["panel2"],
                    darkcolor=C["panel2"],
                    arrowcolor=C["accent"])

    style.configure("TScrollbar",
                    background=C["panel2"],
                    troughcolor=C["panel"],
                    bordercolor=C["border"],
                    arrowcolor=C["txt_dim"])

    app._log_entry("System Clock Manager started", "info")
    app._log_entry(f"Running on {OS}  |  Python {sys.version.split()[0]}", "info")
    if not _is_admin():
        app._log_entry("WARNING: not running as administrator — system calls may fail", "err")
        if OS == "Windows":
            app._log_entry("Tip: run Command Prompt as Administrator, then: python sysclock_gui.py", "info")
        else:
            app._log_entry("Tip: run with  sudo python3 sysclock_gui.py", "info")

    app.mainloop()
