"""Deterministic mock outputs for DEMO_MODE.

Each scenario returns a dict of {command_pattern: mock_output}.
The alert string is matched by keyword to select the right scenario.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Scenario 1 — Hung Work Process  (keywords: WP, work proc)
# ---------------------------------------------------------------------------
HUNG_WP_OUTPUTS: dict[str, str] = {
    "ABAPGetWPTable": (
        "No, Typ, Pid,    Status,  Reason, Start,         Err, Sem, Cpu, Time, Program, Client, User, Action, Table\n"
        "0,  DIA, 12501,  Run,     ,       2026-03-24,    ,    ,    120, 5,    SAPMSSY1, 001, DDIC, ,\n"
        "1,  DIA, 12502,  Run,     ,       2026-03-24,    ,    ,    80,  3,    SAPMSSY1, 001, DDIC, ,\n"
        "2,  DIA, 12503,  STOPPED, SIGSEGV,2026-03-24,    X,   ,    0,   0,    Z_CUSTOM_FM, 001, ZUSER, ,\n"
        "3,  BTC, 12504,  Wait,    ,       2026-03-24,    ,    ,    10,  0,    , , , ,\n"
    ),
    "GetProcessList": (
        "name, description, dispstatus, textstatus, starttime, elapsedtime, pid\n"
        "disp+work, Dispatcher, GREEN, Running, 2026-03-24 06:00:00, 18:00:00, 12500\n"
        "igswd_mt, IGS Watchdog, GREEN, Running, 2026-03-24 06:00:00, 18:00:00, 12510\n"
        "gwrd, Gateway, GREEN, Running, 2026-03-24 06:00:00, 18:00:00, 12520\n"
    ),
    "dev_w2": (
        "***LOG Q0I=> SigISegv, signal 11 received  [dpnpcheck.c   723]\n"
        "***LOG Q04=> SIGSEGV caught in Z_CUSTOM_FM\n"
        "***LOG Q0I=> work process WP02 is being restarted\n"
        "trc file: \"dev_w2\", trc level: 1, component: \"ABAP\"\n"
        "M  ***LOG R19=> SIGSEGV in function module Z_CUSTOM_FM (program SAPLZ_CUSTOM)\n"
        "M  ABAP dump: SYSTEM_DUMP / SIGSEGV\n"
    ),
    "df -h": (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/sda1        50G   30G   20G  60% /\n"
        "/dev/sdb1       100G   45G   55G  45% /usr/sap\n"
    ),
}


# ---------------------------------------------------------------------------
# Scenario 2 — Filesystem Critical  (keywords: filesystem, disk)
# ---------------------------------------------------------------------------
FILESYSTEM_OUTPUTS: dict[str, str] = {
    "df -h": (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/sda1        50G   30G   20G  60% /\n"
        "/dev/sdb1       100G   94G    6G  94% /usr/sap/DEV/work\n"
        "/dev/sdc1       200G   80G  120G  40% /usr/sap/DEV/data\n"
    ),
    "ls -lh": (
        "total 8.2G\n"
        "-rw-r--r-- 1 devadm sapsys 2.1G Feb 10 dev_w0.old\n"
        "-rw-r--r-- 1 devadm sapsys 1.8G Feb 05 dev_w1.old\n"
        "-rw-r--r-- 1 devadm sapsys 1.5G Jan 20 dev_w2.old\n"
        "-rw-r--r-- 1 devadm sapsys 1.2G Jan 15 dev_disp.old\n"
        "-rw-r--r-- 1 devadm sapsys 800M Jan 10 dev_rd.old\n"
        "-rw-r--r-- 1 devadm sapsys 120K Mar 24 dev_w0\n"
        "-rw-r--r-- 1 devadm sapsys  80K Mar 24 dev_w1\n"
    ),
    "ABAPGetWPTable": (
        "No, Typ, Pid,    Status, Reason, Start,         Err, Sem, Cpu, Time, Program, Client, User, Action, Table\n"
        "0,  DIA, 12501,  Run,    ,       2026-03-24,    ,    ,    100, 5,    SAPMSSY1, 001, DDIC, ,\n"
        "1,  DIA, 12502,  Run,    ,       2026-03-24,    ,    ,    80,  3,    SAPMSSY1, 001, DDIC, ,\n"
    ),
    "GetProcessList": (
        "name, description, dispstatus, textstatus, starttime, elapsedtime, pid\n"
        "disp+work, Dispatcher, GREEN, Running, 2026-03-24 06:00:00, 18:00:00, 12500\n"
    ),
}


# ---------------------------------------------------------------------------
# Scenario 3 — ABAP Dump / TIME_OUT  (keywords: dump, abap)
# ---------------------------------------------------------------------------
ABAP_DUMP_OUTPUTS: dict[str, str] = {
    "dev_w0": (
        "trc file: \"dev_w0\", trc level: 1, component: \"ABAP\"\n"
        "M  ***LOG R15=> ABAP runtime error TIME_OUT occurred\n"
        "M  ABAP Program: ZREPORT_HEAVY\n"
        "M  Source: ZREPORT_HEAVY line 1042\n"
        "M  Error: TIME_OUT — program exceeded maximum runtime\n"
        "M  Long running SELECT on table VBAK without proper WHERE clause\n"
        "M  User: ZBATCHUSER  Client: 001\n"
        "M  No checkpoint/commit found in main loop\n"
    ),
    "ABAPGetWPTable": (
        "No, Typ, Pid,    Status, Reason,   Start,         Err, Sem, Cpu, Time, Program, Client, User, Action, Table\n"
        "0,  DIA, 12501,  Run,    TIME_OUT, 2026-03-24,    X,   ,    600, 600,  ZREPORT_HEAVY, 001, ZBATCHUSER, ,\n"
        "1,  DIA, 12502,  Run,    ,         2026-03-24,    ,    ,    80,  3,    SAPMSSY1, 001, DDIC, ,\n"
    ),
    "GetProcessList": (
        "name, description, dispstatus, textstatus, starttime, elapsedtime, pid\n"
        "disp+work, Dispatcher, GREEN, Running, 2026-03-24 06:00:00, 18:00:00, 12500\n"
    ),
    "df -h": (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/sda1        50G   30G   20G  60% /\n"
        "/dev/sdb1       100G   45G   55G  45% /usr/sap\n"
    ),
}


# ---------------------------------------------------------------------------
# Scenario 4 — Instance Down  (keywords: instance, down)
# ---------------------------------------------------------------------------
INSTANCE_DOWN_OUTPUTS: dict[str, str] = {
    "GetSystemInstanceList": (
        "hostname, instanceNr, httpPort, httpsPort, startPriority, features, dispstatus\n"
        "sap-dev-01, 00, 50013, 50014, 1, ABAP|GATEWAY, GRAY\n"
    ),
    "GetProcessList": (
        "name, description, dispstatus, textstatus, starttime, elapsedtime, pid\n"
        "disp+work, Dispatcher, GRAY, Stopped, , , \n"
        "igswd_mt, IGS Watchdog, GRAY, Stopped, , , \n"
        "gwrd, Gateway, GRAY, Stopped, , , \n"
    ),
    "df -h": (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/sda1        50G   30G   20G  60% /\n"
        "/dev/sdb1       100G   45G   55G  45% /usr/sap\n"
    ),
}


# ---------------------------------------------------------------------------
# Keyword → scenario mapping
# ---------------------------------------------------------------------------
_SCENARIOS: list[tuple[list[str], dict[str, str]]] = [
    (["wp", "work proc"], HUNG_WP_OUTPUTS),
    (["filesystem", "disk"], FILESYSTEM_OUTPUTS),
    (["dump", "abap"], ABAP_DUMP_OUTPUTS),
    (["instance", "down"], INSTANCE_DOWN_OUTPUTS),
]


def select_scenario(alert: str) -> dict[str, str]:
    """Return the mock output dict for the first keyword match in *alert*."""
    alert_lower = alert.lower()
    for keywords, outputs in _SCENARIOS:
        for kw in keywords:
            if kw in alert_lower:
                return outputs
    # Fallback — return the hung WP scenario as default
    return HUNG_WP_OUTPUTS


def mock_command(alert: str, command: str) -> str:
    """Look up a mock response for *command* within the scenario selected by *alert*.

    Uses substring matching so that e.g. ``sapcontrol … -function ABAPGetWPTable``
    matches the key ``ABAPGetWPTable``.
    """
    scenario = select_scenario(alert)
    for pattern, output in scenario.items():
        if pattern in command:
            return output
    return f"(mock) no output configured for command: {command}"
