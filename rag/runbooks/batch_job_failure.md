---
title: Batch Job Failure
keywords: [batch, job, SM37, background, BTC, BTCTRNS2, failed, cancelled, scheduled, event, batch scheduler]
sap_note: 1959077
risk: LOW
---

# Batch Job Failure

## Overview

SAP batch jobs (background jobs) run scheduled or event-triggered tasks such
as data loads, report generation, ALE/IDoc processing, and housekeeping. Job
failures are common and usually application-level issues, but Basis is often
the first responder when monitoring detects failed critical jobs.

## Symptoms

- SM37 shows jobs with status CANCELLED or FINISHED with errors
- Job log (SM37 → select job → Job Log) shows error messages
- Business processes that depend on batch output are delayed
- SM21 may show BTC-related messages
- `ABAPGetWPTable` may show BTC processes in STOPPED state (rare, more severe)

## Diagnosis Steps

### 1. Check job status and log

In SM37: display the failed job. Read the job log for:
- ABAP short dump references (→ check ST22)
- Database errors
- Authorization failures
- "No batch work process available" → all BTC WPs busy

### 2. Check batch work process availability

```bash
sapcontrol -nr <NR> -function ABAPGetWPTable
```

Count BTC-type processes. If all are busy (Status = Run), new batch jobs
queue and may time out. Common during month-end or year-end processing.

### 3. Check for system-level causes

- Disk full → batch job cannot write spool output
- Memory exhaustion → batch job terminated by OOM
- Database issue → batch job SQL operations fail

## Remediation

### Reschedule the job

If the failure was transient (temporary disk full, brief DB outage):
1. Fix the underlying issue
2. In SM37 → select job → Repeat Scheduling
3. Or use SM36 to create a new immediate run

### Free up batch work processes

If all BTC WPs are occupied:
- Check SM50 for long-running batch jobs — are any stuck?
- Consider cancelling non-critical running jobs to free WPs
- Profile parameter `rdisp/wp_no_btc` controls the number of batch WPs

### For recurring failures

Document the pattern and escalate to the application team. Common fixes:
- Optimize the ABAP program (see TIME_OUT runbook)
- Stagger job start times to avoid resource contention
- Increase batch WP count if the instance has capacity

## Risk Assessment

**LOW** — investigating and rescheduling batch jobs is routine L1 work.
Cancelling a running batch job may cause data inconsistency if the job was
mid-update — always check with the job owner first.

## Related SAP Notes

- SAP Note 1959077: Background processing troubleshooting
- SAP Note 54480: Background job scheduling basics
