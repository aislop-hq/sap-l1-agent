---
title: ABAP Dump — TIME_OUT
keywords: [TIME_OUT, ABAP, dump, runtime, long-running, SELECT, ST22, short dump, ZREPORT, checkpoint, batch]
sap_note: 1752526
risk: LOW
---

# ABAP Dump — TIME_OUT

## Overview

A TIME_OUT ABAP short dump occurs when a dialog or batch work process exceeds
the maximum allowed runtime. For dialog processes this is controlled by profile
parameter `rdisp/max_wprun_time` (default 600 seconds). For batch/update
processes the timeout is typically much higher or unlimited.

TIME_OUT dumps are application-level issues and almost never require Basis
system-level intervention. They indicate inefficient ABAP code — typically a
large `SELECT` statement without a proper `WHERE` clause, a missing database
index, or a loop without periodic `COMMIT WORK` statements.

This runbook is primarily informational for L1 Basis. The key action is to
document the finding and escalate to the ABAP development team.

## Symptoms

- Short dump visible in transaction ST22 with runtime error `TIME_OUT`
- Work process trace `dev_w<N>` contains entries like:
  ```
  M  ***LOG R15=> ABAP runtime error TIME_OUT occurred
  M  ABAP Program: ZREPORT_HEAVY
  ```
- The work process table (SM50/ABAPGetWPTable) may show the WP with
  `Reason = TIME_OUT` and `Err = X` briefly before the WP is recycled
- Users report "transaction timed out" or "maximum processing time exceeded"
- In SM21: message class `ABAP`, message type `DUMP`

## Diagnosis Steps

### 1. Read the work process trace

```bash
cat /usr/sap/<SID>/work/dev_w<N>
```

Key fields to extract:
- **Program**: The ABAP program that timed out (e.g., `ZREPORT_HEAVY`)
- **Line number**: The source line where execution was when the timeout hit
- **User/Client**: Who triggered it — batch user or interactive?
- **Table**: If a database operation was in progress, which table?

### 2. Check ST22 for the full dump

In transaction ST22, look up the dump for the time window. The full dump
contains:
- The complete ABAP call stack
- Variable values at the time of the crash
- The SQL statement being executed (if applicable)
- Memory consumption of the work process

### 3. Identify the root cause pattern

| Pattern                                    | Likely cause                          |
|--------------------------------------------|---------------------------------------|
| `SELECT * FROM <large_table>`              | Missing WHERE clause                  |
| `SELECT` in a `LOOP`                       | N+1 query pattern, needs JOIN/FOR ALL |
| No `COMMIT WORK` in processing loop        | Transaction too long, needs checkpoint|
| `CALL FUNCTION` with long-running RFC      | Remote system slow or unresponsive    |
| Report runs fine in DEV but fails in PRD   | Data volume difference                |

### 4. Check if it's a recurring pattern

```sql
-- In DBACOCKPIT or via SE16 on table SNAP
SELECT COUNT(*) FROM snap
WHERE seession LIKE 'TIME_OUT%'
  AND datum > sy-datum - 30
GROUP BY aession
```

Recurring TIME_OUTs on the same program indicate a systematic issue that
needs developer attention, not just a one-off retry.

## Remediation

### For L1 Basis: No system-level fix required

TIME_OUT dumps do **not** require:
- Work process restart (the WP recovers automatically)
- Instance restart
- Parameter changes (increasing `rdisp/max_wprun_time` is almost never the right fix)

### Escalation to ABAP development

Create an incident for the development team with:
1. Program name and line number from the dump
2. User and client where it occurred
3. Frequency (one-off vs. recurring)
4. Whether it happens in batch or dialog
5. The SQL statement or operation that was running

### Temporary mitigation (if business-critical)

If the report must run and keeps timing out:
- Schedule it as a **batch job** (SM36) where the timeout is higher
- Ask the Basis team to temporarily increase `rdisp/max_wprun_time` for the
  instance (requires restart — coordinate with change management)

## Risk Assessment

**LOW** — this is an informational finding. No system action is required and
the work process recovers automatically after the dump. The dump itself is
already logged in ST22 for developer analysis.

## Related SAP Notes

- SAP Note 1752526: TIME_OUT in dialog work processes
- SAP Note 44051: rdisp/max_wprun_time parameter documentation
- SAP Note 1087167: Optimizing long-running ABAP reports
