---
title: Memory Issues — Extended Memory and Heap
keywords: [memory, PRIV, extended memory, heap, em/initial_size, abap/heap_area_total, STORAGE_PARAMETERS_WRONG_SET, OOM, swap]
sap_note: 146289
risk: MEDIUM
---

# Memory Issues — Extended Memory and Heap

## Overview

SAP ABAP work processes use a tiered memory model: roll memory → extended
memory (EM) → heap (private) memory. When a work process enters PRIV mode
(private memory / heap allocation), it is exclusively bound to one user context
and cannot serve other requests until that context ends. If many WPs enter PRIV
simultaneously, the instance runs out of dialog capacity.

At the OS level, excessive memory usage can trigger the Linux OOM killer, which
terminates SAP processes without warning.

## Symptoms

- SM50 shows multiple work processes in PRIV mode
- Transaction ST02 shows extended memory exhausted or high swap usage
- Users receive STORAGE_PARAMETERS_WRONG_SET short dumps
- OS monitoring shows swap usage >50% or OOM kills in `dmesg`
- Instance performance degrades progressively during the business day

## Diagnosis Steps

### 1. Check work process memory modes

```bash
sapcontrol -nr <NR> -function ABAPGetWPTable
```

Count processes in PRIV mode. If >50% of dialog WPs are in PRIV, the instance
is memory-constrained.

### 2. Check extended memory usage

Transaction ST02 → Extended Memory section:
- `Max Used` vs. `Configured` — if Max Used ≈ Configured, EM is exhausted
- Check `Heap Memory` section similarly

### 3. Check OS memory

```bash
free -h
# Look at: total, used, available, swap used
```

If swap usage is high (>2 GB), the system is under memory pressure.

```bash
dmesg | grep -i "oom\|out of memory" | tail -10
```

### 4. Identify memory-hungry sessions

In SM04 → display all users → sort by memory. Users consuming >500 MB of
extended memory are candidates for investigation.

## Remediation

### Immediate: End PRIV sessions

In SM50: identify long-running PRIV processes. If they are from dialog users
(not batch), they can be ended:
- SM04 → select user → End Session

### Tune memory parameters

Key profile parameters (require restart):

```
em/initial_size_MB = 16384          # Extended memory pool (default often too small)
abap/heap_area_total = 2000000000   # Max heap per WP (2 GB)
abap/heap_area_dia = 500000000      # Max heap for dialog WP
```

### OS-level: Increase available memory

- Add swap space if physical memory cannot be increased
- Check if other non-SAP processes are consuming excessive memory
- Consider migrating to a larger VM instance

## Risk Assessment

**MEDIUM** — ending user sessions causes data loss for unsaved work. Memory
parameter changes require instance restart. However, leaving memory exhaustion
unaddressed leads to instance instability.

## Related SAP Notes

- SAP Note 146289: SAP memory management parameters
- SAP Note 1518419: Understanding PRIV mode work processes
- SAP Note 2085980: Linux OOM killer and SAP systems
