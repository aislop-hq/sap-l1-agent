---
title: Enqueue Lock Issues
keywords: [enqueue, lock, SM12, ENQUEUE_OVERFLOW, lock table, dequeue, blocking, exclusive lock]
sap_note: 1potom1
risk: MEDIUM
action: escalate
fix_command: ""
verify_command: ""
---

# Enqueue Lock Issues

## Overview

The SAP enqueue server manages logical locks for database records. When the
lock table overflows, when orphaned locks accumulate, or when a long-running
process holds exclusive locks, other users are blocked from accessing the
same data. This manifests as "locked by user" errors in transactions.

## Symptoms

- Users see "Entry locked by user XXXXX" in transactions like VA01, ME21N, FB01
- Transaction SM12 shows many old lock entries (hours or days old)
- SM21 system log shows ENQUEUE_OVERFLOW messages
- Batch jobs fail because they cannot obtain required locks
- `sapcontrol -nr <NR> -function GetAlertTree` shows enqueue alerts

## Diagnosis Steps

### 1. Check the lock table

In transaction SM12, display all locks. Look for:
- Locks older than the current business day
- Locks held by users who are no longer logged in (orphaned locks)
- Locks from batch processes that crashed mid-execution

### 2. Check enqueue server health

```bash
sapcontrol -nr <NR> -function GetProcessList
```

Verify the enqueue server process (`enserver`) is GREEN. If it shows YELLOW
or GRAY, the lock table may be corrupted.

### 3. Check lock table size

Profile parameter `enque/table_size` controls the lock table capacity.
Default is often 4096 entries. Check current usage:

```bash
sapcontrol -nr <NR> -function GetAlertTree
```

If usage is >80%, the table may need resizing.

## Remediation

### Delete orphaned locks

In SM12 → select old locks → Delete. This is safe for locks where:
- The user is no longer logged in (check SM04)
- The lock is >24 hours old
- The originating batch job has already failed

### Increase lock table (if overflow)

Adjust profile parameter:
```
enque/table_size = 8192
```
Requires instance restart. Coordinate with change management.

### Kill blocking sessions

If a dialog user is holding critical locks:
1. Identify the user session in SM04
2. Contact the user before terminating their session
3. In SM04: select session → End Session (soft terminate)

## Risk Assessment

**MEDIUM** — deleting lock entries can cause data inconsistency if the holding
transaction is still active. Always verify the lock owner's session status
before deleting locks.

## Related SAP Notes

- SAP Note 1potom1: Enqueue lock table sizing guidelines
- SAP Note 84348: SM12 lock administration
