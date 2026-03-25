---
title: Update Process Failure
keywords: [update, UPD, SM13, update process, V1, V2, failed update, update termination, STOPPED]
sap_note: 48400
risk: MEDIUM
action: restart_workprocess
fix_command: "sapcontrol -nr {NR} -function RestartService"
verify_command: "sapcontrol -nr {NR} -function GetProcessList"
---

# Update Process Failure

## Overview

SAP uses asynchronous update processes (V1 for critical, V2 for non-critical
updates) to write data changes to the database. When update processes fail or
stop, document postings appear successful to the user but the database changes
are never committed. This is a data integrity risk that requires prompt
attention.

## Symptoms

- Transaction SM13 shows failed update records (status: ERR)
- Work process table shows UPD/UP2 processes in STOPPED state
- Users report "document saved" but the document is not visible afterwards
- SM21 shows update termination messages
- `ABAPGetWPTable` shows UPD processes with `Err = X`

## Diagnosis Steps

### 1. Check SM13 for failed updates

List failed updates. Note the:
- User and client
- Update function module that failed
- Error message / short dump reference
- Timestamp — are failures ongoing or from a specific time window?

### 2. Check update work process status

```bash
sapcontrol -nr <NR> -function ABAPGetWPTable
```

Look for UPD/UP2 type processes. If Status = STOPPED, the update dispatcher
cannot process new updates.

### 3. Read the update process trace

```bash
cat /usr/sap/<SID>/work/dev_w<N>   # where N is the UPD process number
```

Look for database errors (ORA-xxxx, DBIF_RSQL_SQL_ERROR) or ABAP short dumps.

## Remediation

### Restart stopped update processes

```bash
sapcontrol -nr <NR> -function RestartService
```

### Reprocess failed updates

In SM13: select failed records → choose "Reprocess". This re-executes the
update function module. Only reprocess if the root cause has been fixed.

### If database errors are the cause

- Check database alert log for tablespace or connectivity issues
- Coordinate with DBA team
- Do NOT reprocess updates until the database issue is resolved

## Risk Assessment

**MEDIUM** — failed updates represent incomplete business transactions. While
restarting the update process is low-risk, reprocessing failed updates can
cause duplicate postings if the original update partially succeeded.

## Related SAP Notes

- SAP Note 48400: Update process troubleshooting
- SAP Note 16646: SM13 — update debugging
