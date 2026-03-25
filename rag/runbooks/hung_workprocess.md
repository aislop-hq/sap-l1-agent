---
title: Hung Work Process
keywords: [WP, STOPPED, SIGSEGV, RestartService, work process, crash, signal, SM50, dpnpcheck]
sap_note: 1234567
risk: LOW
---

# Hung Work Process

## Overview

A work process (WP) in an SAP ABAP application server can become unresponsive
or crash due to various reasons including memory corruption, segmentation faults
(SIGSEGV), or deadlocks. When a WP enters STOPPED state, it no longer serves
user requests and reduces the available dialog capacity of the instance.

This runbook covers the diagnosis and remediation of individual work process
failures, which are the most common L1 Basis incident type.

## Symptoms

- Work process shows status **STOPPED** in transaction SM50 or via
  `sapcontrol -nr <NR> -function ABAPGetWPTable`
- The `Reason` column in the WP table shows a signal name such as SIGSEGV,
  SIGBUS, or SIGABRT
- The corresponding trace file `dev_w<N>` contains a crash stack trace with
  entries like `***LOG Q0I=> SigISegv, signal 11 received`
- Users may report intermittent transaction timeouts or "no dialog work
  process available" errors (SM21 message type W, id DIA)
- In extreme cases multiple WPs crash in sequence if the root cause is a
  shared memory corruption — check SM50 for a pattern

## Diagnosis Steps

### 1. Identify the stopped work process

```bash
sapcontrol -nr <NR> -function ABAPGetWPTable
```

Look for rows where `Status = STOPPED` and note the WP number (`No` column).
Also record the `Pid`, `Reason`, and `Program` fields — these feed into the
trace analysis.

### 2. Read the work process trace

```bash
cat /usr/sap/<SID>/work/dev_w<N>
```

Search for the following patterns:
- `***LOG Q0I=>` — signal receipt line, shows the signal number
- `***LOG Q04=>` — the function or module where the crash occurred
- `ABAP dump:` — the short dump category (e.g., SYSTEM_DUMP, MEMORY_CORRUPT)
- `M  ***LOG R19=>` — the ABAP-level crash location (program, include, line)

### 3. Check for known patterns

Common crash signatures and their SAP Notes:

| Crash signature                        | SAP Note | Fix                        |
|----------------------------------------|----------|----------------------------|
| SIGSEGV in dpnpcheck.c                 | 1234567  | Kernel patch               |
| SIGSEGV in abheap.c (heap corruption)  | 2145678  | Increase em/initial_size   |
| SIGBUS in shared memory segment        | 1987654  | Check /dev/shm sizing      |
| Repeated crash in same Z-program       | —        | ABAP code fix required     |

### 4. Check SM21 system log

In transaction SM21, filter for the time window around the crash. Look for:
- Message ID `DIA` — dialog process events
- Message ID `R19` — ABAP runtime errors
- Any preceding `enqueue` or `update` errors that might indicate a cascade

## Remediation

### Restart the individual work process

```bash
sapcontrol -nr <NR> -function RestartService
```

This restarts only the crashed work process without affecting other WPs or
connected users. The dispatcher automatically reassigns the WP number.

**Important:** If the same WP crashes again within minutes, do NOT keep
restarting — escalate to L2 and check the ABAP code or kernel patch level.

### Apply kernel patch (if applicable)

If the crash matches a known kernel bug (see table above), schedule a kernel
update during the next maintenance window. Kernel patches are applied via
SWPM or manual replacement of the `disp+work` executable.

### Disable the offending program (temporary)

If a custom Z-program is consistently crashing WPs, consider:
1. Locking the program in SE38 to prevent execution
2. Notifying the development team
3. Documenting the workaround in the incident ticket

## Risk Assessment

**LOW** — restarting a single work process is a routine Basis operation. It does
not require a system restart and does not impact other users. The restarted WP
is available for new requests within seconds.

## Related SAP Notes

- SAP Note 1234567: SIGSEGV in dpnpcheck.c — kernel crash in network check
- SAP Note 16083: How to analyze work process crash dumps
- SAP Note 1501654: Understanding ABAP work process states
